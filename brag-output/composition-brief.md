# Hyperframes Composition Brief: LeadGen

## Objective
Create a short, polished launch-style brag video for **LeadGen** — a premium,
restrained product film.

## Output
- Composition directory: `brag-output/composition/`
- Rendered video: `brag-output/brag.mp4`
- Format: landscape — 1920x1080
- Duration: 20 seconds (4 scenes: 4 + 5 + 7 + 4)

## Source Material
- Project root: repository root; primary source `leadgen.html`
- Primary files read: `leadgen.html` (hero, sections, demo console), README
- Product name: LeadGen
- Tagline / strongest claim: "Stop chasing strangers. Start winning buyers." /
  "Three answers in, a working list out."
- Key UI / visual moment to recreate: the crimson→brass gradient hero with the
  rotating word, and the monospace **run console** resolving to "47 qualified
  leads" with scored lead rows.
- Copy that must appear verbatim:
  - "Stop chasing strangers."
  - "Start winning buyers."
  - "SerpAPI: 128 results"
  - "128 > 100 · engaging Apify + Google SerpAPI"
  - "47 qualified leads"
  - "Three answers in, a working list out."
  - "LeadGen" / "by Zubair Hussain"

## Creative Direction
- Tone preset: polished
- Creative direction: quiet premium product film
- Interpretation: 4 scenes, long holds, soft crossfades; slow deliberate motion;
  light serif display type with generous spacing; the numbers carry the drama.
- Angle: Let the product's own line do the work — the centerpiece is the real demo
  engine running (SerpAPI 128 → threshold → Apify + Google SerpAPI → 47 scored
  leads). Specific numbers, real copy, restraint.
- Hook: black screen; the crimson→brass **LeadGen** wordmark resolves at scale with
  a soft gold glow and one quiet line: "Find the people already looking for you."
- Outro / punchline: "Three answers in, a working list out." → LeadGen wordmark,
  "by Zubair Hussain", hairline "Next.js · Django", fade to black.
- Avoid:
  - Generic SaaS language
  - Abstract filler visuals
  - Unrelated visual redesign

## Visual Identity
- Background: #050505 (base #000000)
- Text: #f3ece6 (muted #c9bcb1)
- Accent: brass/gold #c9a84c → #e0b35c over crimson #c8141e / #ef4444
  (brand gradient `linear-gradient(110deg,#c8141e,#ef4444 46%,#c9a84c)`)
- Display font: Cormorant Garamond (serif); fall back to Georgia serif if the
  webfont is unavailable offline.
- Body font: DM Sans (fallback system sans); Mono: JetBrains Mono (fallback
  ui-monospace) for the console.
- Visual references: dark field with a faint red-dot globe texture; gradient
  wordmark; monospace console with gold ✓.

## Storyboard
Use the storyboard in `brag-output/brag-plan.md` as the creative contract.

Scene summary:
1. Wordmark hook — 4s — LeadGen gradient wordmark + "Find the people already looking for you."
2. The line — 5s — "Stop chasing strangers." → "Start winning buyers." (winning → brass)
3. The engine (centerpiece) — 7s — console types SerpAPI 128 → threshold → Apify + Google SerpAPI → ✓ 47 qualified leads; two scored lead rows arrive.
4. Outro — 4s — "Three answers in, a working list out." → LeadGen wordmark / by Zubair Hussain / Next.js · Django → black.

## Audio
- Audio role: warm, restrained cinematic bed with sparse, motion-matched accents.
- Audio arc: low bed fades in under the hero, holds with sparse key ticks and card
  sounds through the engine run, fades to near-silence for the final tagline.
- Music: Hyperframes selects a soft cinematic/corporate bed from bundled assets.
- Music treatment: start low ~0s; gentle swell around the console reveal (~9–14s);
  ease down at the outro (~16s) so the tagline lands clean.
- Music cue guidance: detect at composition time (`hyperframes beats` on the chosen
  track). Target a soft swell near the console reveal (~9–14s) and a settle near the
  outro (~16s). Console lines snap to every-other-beat so each holds long enough to
  read.
- Audio-reactive treatment: subtle — let the hero glow / console presence breathe
  gently with the bed; no waveform or equalizer visuals.
- Audio-coupled moments:
  - Scene 3 console lines — typed reveal with subtle key ticks
  - Scene 3 "✓ 47 qualified leads" — one dry low accent
  - Scene 3 lead rows — soft card sound as each arrives
  - Scene 4 wordmark — one final soft low accent, then fade
- SFX selection guidance: sparse and polished; low high-frequency-risk files for the
  repeated key ticks; a single restrained accent for the payoff and the logo.
- SFX analysis guidance: use the skill's `assets/sfx/sfx-analysis.md` if present.
- Exact SFX choice: Hyperframes chooses filenames, timestamps, density, volume.
- Audio files: copy the chosen music and SFX into `brag-output/composition/assets/`.

## Hyperframes Instructions
Build with native Hyperframes conventions (`hyperframes-core` timing/`data-*`,
`hyperframes-animation`, `hyperframes-creative`, `hyperframes-keyframes`,
`hyperframes-cli`). This is a /brag run — do not enter the generic intent interview.

Requirements:
- Show at least one real UI/copy element (the hero line + the run console are both real).
- Keep all text readable (respect the reading-time floor: short labels ~0.8s,
  sentences ~0.3s/word). Fast-in, then hold.
- Keep total duration 15–25s (target 20s).
- Include the music/SFX layer; treat cue metadata as optional hints.
- Beat-lock 1–2 major moments (wordmark settle, ✓ payoff) within ±0.15s; snap the
  console lines / lead rows to the beat grid (±0.10s) but never faster than readable.
- Subtle audio-reactive glow only; document if extraction is unavailable.
- Use local assets; run `hyperframes check` (the single gate) before render.
