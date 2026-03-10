# PyMotion Development State

## Current Phase
Phase: v1.0.1 — Patch Release (COMPLETE)
Started: 2026-03-10

## Publishing & Distribution

| Channel | Value |
|---------|-------|
| **PyPI package** | `pymotion-studio` |
| **Install** | `pip install pymotion-studio` |
| **Import** | `from pymotion import ...` |
| **GitHub** | github.com/Ohswedd/pymotion |
| **License** | PyMotion Source Available License 1.0 |

## How to Release a New Version

1. Bump version in `pyproject.toml`
2. Add release notes to `CHANGELOG.md`
3. Commit and push to `main`
4. Tag and push:
   ```bash
   git tag v1.x.x
   git push origin v1.x.x
   ```
5. Create a GitHub Release from the tag (or let `release.yml` do it automatically)
6. `publish.yml` fires on the release event and uploads to PyPI via trusted publisher — no tokens needed
7. `docker.yml` fires on the same event and pushes to Docker Hub (if secrets are configured)

### Docker Hub Setup (one-time)

1. Create an access token at https://hub.docker.com/settings/security
2. Add two repository secrets at github.com/Ohswedd/pymotion/settings/secrets/actions:
   - `DOCKERHUB_USERNAME` — your Docker Hub username
   - `DOCKERHUB_TOKEN` — the access token from step 1
3. Done — every future GitHub release will auto-push the Docker image

### CI/CD Pipelines

| Workflow | Trigger | What It Does |
|----------|---------|--------------|
| `ci.yml` | push/PR to `main` | Lint (ruff + mypy --strict), Test (Python 3.11 + 3.12, 80% coverage gate), Security audit (pip-audit) |
| `release.yml` | tag push `v*` | Extracts CHANGELOG section, creates GitHub Release with notes |
| `publish.yml` | GitHub release published | Builds sdist + wheel, publishes to PyPI via OIDC trusted publisher |
| `docker.yml` | GitHub release published | Builds Docker image, pushes `<version>` + `latest` tags to Docker Hub |

## v1.0.1 Patch — Bug Fixes & Quality (COMPLETE)

### Critical Bug Fixes
- [x] Compositor `_alpha_cache` memory aliasing — text layers randomly skipped due to numpy pointer reuse
- [x] Animated text flickering — reveal-mask architecture for Typewriter/WordByWord/LetterByLetter
- [x] CountUp/CountDown frame-stepping — quintic ease-out + step_frames=3 for smooth counters
- [x] FreeType renderer — replaced block-char fallback with proper glyph rendering

### Encoding Quality
- [x] H.264 presets: CRF 18→10, preset faster→medium
- [x] Added x264-params: no-dct-decimate, no-fast-pskip (eliminates text shimmer)
- [x] Added Lanczos chroma scaling for RGB→YUV420p conversion
- [x] H.265 presets: CRF 22→16, preset faster→medium
- [x] Instagram/TikTok presets: added -tune animation

### Examples
- [x] 5 production-ready examples rewritten (real estate, tech review, fitness, restaurant, education)
- [x] Stock assets + download_assets.py script
- [x] All examples render without flickering

### Quality Gates
- [x] 1116 tests pass
- [x] 85% coverage
- [x] ruff clean, mypy --strict clean
- [x] pip-audit clean (Pillow bumped for CVE-2026-25990)

### Infrastructure & Release
- [x] GitHub repo: public (github.com/Ohswedd/pymotion)
- [x] CI pipeline: lint + test (3.11/3.12) + security audit — all green
- [x] GitHub Actions: ci.yml, publish.yml (PyPI trusted publisher), release.yml (auto-release from tags)
- [x] git tags: v1.0.0, v1.0.1
- [x] GitHub Releases: v1.0.0, v1.0.1 with CHANGELOG notes
- [x] PyPI: pymotion-studio v1.0.1 published
- [x] LICENSE: PyMotion Source Available License 1.0 (use freely, no redistribution)
- [x] README: badges, install, quickstart, examples, architecture, performance, license summary
- [x] Linux font fallback: DejaVuSans/LiberationSans resolved for CI
- [x] mypy --strict: clean across all 60 source files (including CI environment)
- [x] Docker Hub: docker.yml workflow added — auto-pushes on GitHub release (requires DOCKERHUB_USERNAME + DOCKERHUB_TOKEN secrets)

## Completed Phases

### Phase v1.0 — Stable Release (COMPLETE, 2026-03-09)
- Complete PRD §8.2 public API
- 1116 tests, 85% coverage
- All quality gates passed

### Phase RC 0.9 — Polish & Production Readiness (COMPLETE)
- All 22 checklist items complete
- 1079 tests pass, 85% coverage

### Phase 0.4 — Full Feature Completeness (COMPLETE)
- All 24 checklist items complete
- 976 tests pass, 85% coverage

### Phase 0.3 — 3D, Particles, Advanced Audio (COMPLETE)
- All 9 checklist items complete
- 558 tests pass, 82% coverage

### Phase 0.2 — Text, Video, Audio Base (COMPLETE)
- All 20 checklist items complete
- 275 tests pass, 69% coverage

### Phase 0.1 — Core 2D Rendering Pipeline (COMPLETE)
- All infrastructure, core modules, and tests complete
- 132 tests pass, 68% coverage
