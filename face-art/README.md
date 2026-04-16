# Face Art

A single-page web app that turns your face movements into generative art.

**Live demo:** https://experiments.andrewmcdonough.com/faceart/

## How it works

The app uses your webcam and [MediaPipe FaceLandmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker) to track 478 facial landmarks and 52 blend-shape scores in real time. Each gesture triggers a different visual effect on the full-screen art canvas.

## Gestures & effects

| Gesture | Effect |
|---|---|
| **Blink** (both eyes) | Radial colour explosion bursts from your face |
| **Wink** (left eye) | Hearts float upward |
| **Wink** (right eye) | Stars scatter and sparkle |
| **Smile** | A rainbow arc appears above your face |
| **Frown** | A dark rain cloud drifts across the screen |
| **Nod** | A cluster of bubbles rises and pops |
| **Head shake** | A colour swirl spirals outward |

The background slowly cycles through a dark hue shift, and a motion-trail effect means earlier art lingers and fades over time.

## Running locally

Just open `index.html` in a modern browser — no build step, no server required. Camera permission is required.

```bash
open faceart/index.html
# or serve it:
npx serve .
```

> **Note:** Some browsers (Safari on older macOS) may block `getUserMedia` for `file://` URLs. If that happens, serve it over localhost with `npx serve .` or `python3 -m http.server`.

## Technical details

- **No dependencies to install** — all libraries loaded from CDN at runtime
- **MediaPipe Tasks Vision** — face landmark detection + blend shapes
- **HTML5 Canvas 2D API** — all art rendered via canvas
- Blend-shape thresholds are smoothed with an exponential moving average (α=0.35) to reduce jitter
- Each gesture has a cooldown to prevent rapid re-triggering
- Head nod/shake are detected by tracking nose-tip landmark displacement over a 700 ms window
