# Charts & Data Visualization

PyMotion includes animated chart clips for rendering data visualizations
directly inside video compositions. All charts render via Cairo, animate
with ease-out curves, and accept multiple data formats.

## Bar chart

`BarChartClip` renders bars that grow from the baseline over
`animate_duration` frames.

```python
from pymotion import BarChartClip, Composition, Track

comp = Composition(1920, 1080, fps=30, duration=90)

chart = BarChartClip(
    data={"Q1": 120, "Q2": 200, "Q3": 180, "Q4": 250},
    animate_duration=30,
    theme="corporate",
    title="Quarterly Revenue",
    show_values=True,
)
chart.set_duration(90)

track = Track(name="chart")
track.add(chart)
comp.add_track(track)
comp.render("bar_chart.mp4", preset="h264_1080p")
```

## Line chart

`LineChartClip` draws a line progressively from left to right.

```python
from pymotion import LineChartClip

chart = LineChartClip(
    data=[10, 25, 15, 30, 22, 35, 28],
    labels=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    animate_duration=30,
    theme="neon",
    show_dots=True,
    show_fill=True,
)
chart.set_duration(90)
```

## Pie chart

`PieChartClip` sweeps slices in clockwise. Set `inner_radius` for a
donut variant.

```python
from pymotion import PieChartClip

chart = PieChartClip(
    data={"Desktop": 55, "Mobile": 35, "Tablet": 10},
    animate_duration=30,
    theme="gradient",
    inner_radius=0.4,  # donut chart
)
chart.set_duration(90)
```

## Area chart

`AreaChartClip` is a filled variant of the line chart with configurable
fill opacity.

```python
from pymotion import AreaChartClip

chart = AreaChartClip(
    data=[5, 15, 10, 25, 20, 30],
    animate_duration=20,
    fill_opacity=0.5,
)
chart.set_duration(90)
```

## Radar chart

`RadarChartClip` draws a spider/radar chart that grows outward.

```python
from pymotion import RadarChartClip

chart = RadarChartClip(
    data=[85, 70, 90, 60, 75],
    axes=["Speed", "Power", "Range", "Defense", "HP"],
    animate_duration=25,
    theme="minimal",
)
chart.set_duration(90)
```

## Scatter plot

`ScatterPlotClip` reveals points progressively.

```python
from pymotion import ScatterPlotClip

chart = ScatterPlotClip(
    x=[1, 2, 3, 4, 5, 6, 7],
    y=[2.1, 4.0, 3.5, 5.2, 4.8, 6.1, 5.5],
    animate_duration=30,
    point_size=6.0,
)
chart.set_duration(90)
```

## Number counter

`NumberCounter` animates a number from `start_value` to `end_value`
with a customizable format function.

```python
from pymotion import NumberCounter

counter = NumberCounter(
    start_value=0,
    end_value=1_000_000,
    count_duration=60,
    format_fn=lambda v: f"${v:,.0f}",
    size=96.0,
)
counter.set_duration(90)
```

## Progress bar

`ProgressBar` renders a horizontal bar. Pass a callable for animated
values.

```python
from pymotion import ProgressBar
from pymotion.utils.color import Color

bar = ProgressBar(
    value=lambda f: f / 90.0,  # 0% → 100% over 90 frames
    bar_width=600,
    bar_height=40,
    fill_color=Color.parse("#10B981"),
    radius=20,
)
bar.set_duration(90)
```

---

## Themes

All chart clips support four built-in themes:

| Theme | Style |
|-------|-------|
| `"corporate"` | Blue palette, white background, gridlines |
| `"minimal"` | Grayscale, no gridlines, clean look |
| `"neon"` | Bright colors on dark background |
| `"gradient"` | Purple palette, light background |

Pass `theme="neon"` to any chart constructor.

## Data formats

Every chart accepts `data` in three formats:

```python
# List of numbers
data=[10, 20, 30]

# Dict of label → value
data={"A": 10, "B": 20, "C": 30}

# Per-frame callable (live data binding)
data=lambda frame: [frame * 0.5, frame * 1.0, frame * 1.5]
```

When using a dict, the keys become bar/slice labels automatically.
When using a callable, the function receives the current frame number
and must return a list of floats (or a dict).
