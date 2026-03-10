# Composition

The root objects for video generation. A `Composition` owns the resolution,
frame rate, duration, and all tracks. `Track` holds clips in z-order.

## Composition

::: pymotion.composition.Composition

## Track

::: pymotion.composition.Track

## CompositionClip

Nest a Composition as a clip inside another Composition (pre-comps).

::: pymotion.composition.CompositionClip

## AdjustmentLayer

Apply effects to all layers below in the same composition.

::: pymotion.composition.AdjustmentLayer
