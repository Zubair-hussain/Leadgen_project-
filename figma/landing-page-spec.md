# Landing Page Spec

## Source

Primary implementation: `leadgen.html`

## Hero

Headline:

```text
Start [meeting / booking / closing / winning / signing] buyers.
```

Animation:

- Rotating word pill.
- 2.6 second interval.
- Smooth slide up/out for the leaving word.
- Smooth slide in/settle for the entering word.
- Pill color changes with the active word.
- Dot pulses continuously.
- Reduced-motion mode stops long-running rotation.

## Motion Inventory

| Element | Motion |
| --- | --- |
| Hero word pill | Slide swap + width morph + color shift |
| Live dot | Expanding pulse |
| Scroll hint | Vertical drop |
| Cards | Rise/fade entrance |
| Overlay | Fade in |
| Modal | Rise in |
| Generated lead markers | Fade in |
| Error dot | Red pulse |

## Figma Notes

Represent the animation with component variants:

- `WordPill / meeting`
- `WordPill / booking`
- `WordPill / closing`
- `WordPill / winning`
- `WordPill / signing`

Prototype transition:

- Smart Animate.
- Duration: 520ms.
- Delay between states: 2600ms.
- Easing approximation: `cubic-bezier(.62,.04,.2,1)`.
