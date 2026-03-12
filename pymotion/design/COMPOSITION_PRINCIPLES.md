# PyMotion Composition Principles

Canonical reference for visual quality in PyMotion examples and components.
Every frame produced by PyMotion should follow these principles.

---

## Principle 1 — One Thing at a Time

Every frame has exactly one primary element.
Everything else is either absent, or subordinate and visually quiet.

- A title frame has a title. Not a title, a subtitle, a logo, a background animation, and a progress indicator.
- A data frame has one chart. Not a chart, three counters, two labels, and a background gradient.
- A speaking-head frame has the speaker. One lower third. One watermark at very low opacity. That is all.

**Test:** Cover everything except the primary element with your hand. The remaining frame should be self-explanatory. Then uncover everything else. The secondary elements should not make the frame feel busier — they should feel like supporting cast.

If a frame needs five elements to communicate its idea, the idea is not clear enough. Clarify the idea first. Then one or two elements will be sufficient.

---

## Principle 2 — Hierarchy Through Size, Not Decoration

Visual hierarchy is achieved by making important things large and less important things small. It is not achieved by adding more colors, borders, backgrounds, or effects.

- A primary label is 56-96px. A secondary label is 14-18px. The size difference alone creates hierarchy.
- A chart's axis labels should be half the size of the chart title. Their smallness communicates subordination.
- A lower third's name should be noticeably larger than the title. Not just bold — larger. 24px vs 13px, not 18px vs 16px.

**Test:** Remove all color from the frame (greyscale). Does hierarchy still read clearly? If you need color to tell what is important, the size relationships are wrong.

---

## Principle 3 — Whitespace Is Not Empty Space

Whitespace is the visual air between elements that lets each one breathe and assert its presence.

- Content should not come closer than 80px to any frame edge (safe zone). Most content should be further.
- Between two consecutive text elements, the gap should be at least 0.75x the size of the larger element's line height.
- A full-screen chart should have 120px above for the title, 60px below for labels.
- Optical center (approximately 45% from top) looks more balanced than mathematical center.

**Test:** Double all internal padding and gaps. Does it look better? If yes, you started with too little space. Keep increasing until sparse, then pull back 20%.

---

## Principle 4 — Motion Has a Job

Every animated element earns its animation by doing one of:
  A. Directing attention to new information.
  B. Communicating a relationship.
  C. Providing temporal context.
  D. Establishing emotional tone.

If an element is animated but its animation does none of these, remove the animation. Static is better than purposeless motion.

**Test:** Imagine the same frame as a static image. Does the animation add information the static version lacks? If no, remove it.

---

## Principle 5 — Restraint in Color

A frame uses at most three roles of color:
  1. Background (one color family)
  2. Content (text, lines, structural elements — near-white on dark)
  3. Accent (one color signaling importance — used sparingly)

Chart palettes are the only legitimate exception.

**Test:** Can you describe the frame's color story in one sentence? "Dark field, white content, indigo accent." If not, there are too many colors.

---

## Principle 6 — Typography Does the Work

In motion graphics, type is the primary visual element.

- Titles: display_lg (56px) is the floor. display_xl (72px) or display_2xl (96px) is usually better.
- Body text: body_lg (16px) at 1080p is the floor. Slide-style body should be heading (24px).
- Maximum line length: 65-75 characters.
- Never center-align paragraphs or multi-line body text.
- Letter-spacing on large display text should be negative (tighter). At 96px, tracking=-2px.
- All-caps text always uses positive letter-spacing (+0.08em minimum).

---

## Principle 7 — Scene Structure

Every scene follows this structure:

**ENTRY (0-20% of scene duration)**
Primary element enters. Nothing else moves. Animation: opacity + y-drift, ease_out_quart, NORMAL duration.

**HOLD (20-80% of scene duration)**
Primary element is static or progresses in one dimension only. Secondary elements may have entered. The viewer reads the content.

**EXIT (80-100% of scene duration)**
Fade primary element out over FAST duration, or let the transition handle exit.

**Corollary:** Do not overlap entry animations of multiple elements. Stagger them. Exception: elements that belong together may overlap by 50% if subtle.
