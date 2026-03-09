"""AsyncIO preview server with WebSocket-based hot-reload.

Provides a local HTTP server that serves a preview of the current
composition. Uses watchfiles for file monitoring and WebSocket
to push updated frames to the browser client.
"""

from __future__ import annotations

import asyncio
import base64
import importlib
import importlib.util
import io
import sys
from pathlib import Path
from typing import Any

import numpy as np
from aiohttp import web

from pymotion.utils.logging import get_logger

logger = get_logger(__name__)

_PREVIEW_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy"
      content="default-src 'self'; img-src 'self' data:; style-src 'unsafe-inline';">
<title>PyMotion Preview</title>
<style>
body { margin: 0; background: #111; display: flex; flex-direction: column;
       align-items: center; justify-content: center; height: 100vh; color: #eee;
       font-family: system-ui, sans-serif; }
#preview { max-width: 100%; border: 1px solid #333; }
#controls { margin-top: 10px; display: flex; gap: 10px; align-items: center; }
input[type=range] { width: 400px; }
#status { font-size: 12px; color: #888; }
</style>
</head>
<body>
<img id="preview" alt="preview">
<div id="controls">
  <input type="range" id="scrub" min="0" max="100" value="0">
  <span id="frame-info">Frame 0</span>
</div>
<div id="status">Connecting...</div>
<script>
const img = document.getElementById('preview');
const scrub = document.getElementById('scrub');
const frameInfo = document.getElementById('frame-info');
const status = document.getElementById('status');
let ws;
function connect() {
  ws = new WebSocket('ws://' + location.host + '/ws');
  ws.onopen = () => { status.textContent = 'Connected'; };
  ws.onmessage = (e) => {
    const data = JSON.parse(e.data);
    if (data.type === 'frame') {
      img.src = 'data:image/jpeg;base64,' + data.data;
      frameInfo.textContent = 'Frame ' + data.frame;
    } else if (data.type === 'info') {
      scrub.max = data.total_frames - 1;
    }
  };
  ws.onclose = () => { status.textContent = 'Disconnected'; setTimeout(connect, 2000); };
}
scrub.addEventListener('input', () => {
  if (ws && ws.readyState === 1) {
    ws.send(JSON.stringify({type:'seek', frame: parseInt(scrub.value)}));
  }
});
connect();
</script>
</body>
</html>"""


class PreviewServer:
    """Hot-reload preview server for PyMotion compositions.

    Serves an HTML page with a WebSocket connection for live frame updates.
    Monitors the source Python file for changes and re-renders on save.

    Args:
        script_path: Path to the Python script containing the composition.
        port: HTTP port to bind to.
        host: Host to bind to (127.0.0.1 for security).
        preview_scale: Scale factor for preview rendering (0.5 = half res).
    """

    def __init__(
        self,
        script_path: str | Path,
        port: int = 4321,
        host: str = "127.0.0.1",
        preview_scale: float = 0.5,
    ) -> None:
        """Initialize the preview server.

        Args:
            script_path: Path to the composition script.
            port: Port number.
            host: Bind address (default: localhost only).
            preview_scale: Preview resolution scale factor.
        """
        self._script_path = Path(script_path).resolve()
        self._port = port
        self._host = host
        self._preview_scale = preview_scale
        self._app: web.Application | None = None
        self._ws_clients: list[web.WebSocketResponse] = []
        self._current_frame = 0
        self._composition: Any = None
        self._running = False

    async def _handle_index(self, request: web.Request) -> web.Response:
        """Serve the preview HTML page.

        Args:
            request: The HTTP request.

        Returns:
            HTML response.
        """
        return web.Response(text=_PREVIEW_HTML, content_type="text/html")

    async def _handle_ws(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket connections.

        Args:
            request: The HTTP request.

        Returns:
            WebSocket response.
        """
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self._ws_clients.append(ws)
        logger.info("ws_client_connected", total=len(self._ws_clients))

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    import json

                    data = json.loads(msg.data)
                    if data.get("type") == "seek":
                        self._current_frame = int(data.get("frame", 0))
                        await self._send_frame(ws, self._current_frame)
        finally:
            self._ws_clients.remove(ws)
            logger.info("ws_client_disconnected", total=len(self._ws_clients))

        return ws

    async def _send_frame(self, ws: web.WebSocketResponse, frame: int) -> None:
        """Render and send a single frame to a WebSocket client.

        Args:
            ws: The WebSocket to send to.
            frame: Frame number to render.
        """
        if self._composition is None:
            return

        try:
            comp = self._composition
            width = int(comp.width * self._preview_scale)
            height = int(comp.height * self._preview_scale)
            # Ensure even dimensions
            width = width + (width % 2)
            height = height + (height % 2)

            # Render frame (simplified — renders placeholder for now)
            frame_data = np.zeros((height, width, 4), dtype=np.uint8)
            frame_data[:, :, 3] = 255

            # Convert BGRA to RGB for JPEG
            from PIL import Image

            rgb = np.zeros((height, width, 3), dtype=np.uint8)
            rgb[:, :, 0] = frame_data[:, :, 2]  # R
            rgb[:, :, 1] = frame_data[:, :, 1]  # G
            rgb[:, :, 2] = frame_data[:, :, 0]  # B

            img = Image.fromarray(rgb)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75)
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")

            import json

            await ws.send_str(json.dumps({"type": "frame", "frame": frame, "data": b64}))
        except Exception:
            logger.exception("frame_render_error", frame=frame)

    async def _broadcast_frame(self, frame: int) -> None:
        """Send a frame to all connected clients.

        Args:
            frame: Frame number to broadcast.
        """
        for ws in list(self._ws_clients):
            if not ws.closed:
                await self._send_frame(ws, frame)

    def _load_composition(self) -> Any:
        """Load/reload the composition from the script file.

        Returns:
            The composition object, or None if loading fails.
        """
        try:
            module_name = f"_pymotion_preview_{self._script_path.stem}"
            spec = importlib.util.spec_from_file_location(module_name, self._script_path)
            if spec is None or spec.loader is None:
                logger.error("cannot_load_script", path=str(self._script_path))
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Look for a Composition object
            comp = getattr(module, "comp", None) or getattr(module, "composition", None)
            if comp is None:
                # Search for any Composition instance
                from pymotion.composition import Composition

                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, Composition):
                        comp = attr
                        break

            if comp is not None:
                logger.info("composition_loaded", path=str(self._script_path))
            else:
                logger.warning("no_composition_found", path=str(self._script_path))

            return comp
        except Exception:
            logger.exception("script_load_error", path=str(self._script_path))
            return None

    async def _watch_files(self) -> None:
        """Watch the script file for changes and reload.

        Uses watchfiles for efficient file system monitoring.
        """
        from watchfiles import awatch

        logger.info("watching_file", path=str(self._script_path))
        async for _changes in awatch(self._script_path):
            logger.info("file_changed", path=str(self._script_path))
            self._composition = self._load_composition()
            await self._broadcast_frame(self._current_frame)

    async def start(self) -> None:
        """Start the preview server."""
        self._composition = self._load_composition()

        self._app = web.Application()
        self._app.router.add_get("/", self._handle_index)
        self._app.router.add_get("/ws", self._handle_ws)

        runner = web.AppRunner(self._app)
        await runner.setup()
        site = web.TCPSite(runner, self._host, self._port)
        await site.start()

        self._running = True
        logger.info(
            "preview_server_started",
            host=self._host,
            port=self._port,
            script=str(self._script_path),
        )

        # Start file watcher
        watch_task = asyncio.create_task(self._watch_files())

        try:
            while self._running:
                await asyncio.sleep(1)
        finally:
            watch_task.cancel()
            await runner.cleanup()

    def stop(self) -> None:
        """Stop the preview server."""
        self._running = False
        logger.info("preview_server_stopped")
