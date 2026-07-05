# Hand Gesture Game Controller

Control browser-based games using hand swipes captured through your webcam — no keyboard needed.

## Overview

This project tracks your index fingertip in real time using MediaPipe, filters the motion to separate deliberate swipes from hand jitter, and maps left/right/up/down swipes to keyboard presses via PyAutoGUI.

The core interaction is simple, but getting swipe detection to feel reliable (no double-fires, no jitter-triggered false positives) took some actual signal-processing and state-machine design, which is where most of the engineering in this repo lives.

## Design Notes

**Motion filtering (`gesture_controller/filters.py`)**
Raw fingertip coordinates from MediaPipe are noisy frame-to-frame. Rather than differencing two raw positions (which amplifies that noise into a jumpy velocity signal), positions first pass through an Exponential Moving Average low-pass filter, and velocity is then estimated as the average slope over a short sliding window of the *filtered* trajectory. This is the same idea as filtering a noisy sensor reading before feeding it into a controller, applied here to fingertip tracking.

**Debounced triggering (`gesture_controller/state_machine.py`)**
A plain cooldown timer ("don't fire again for N seconds") tends to double-fire on the tail end of a single swipe, because the hand is often still moving when the timer expires. This is modeled explicitly as a two-state machine (`IDLE` / `FIRED`) that only returns to `IDLE` once the cooldown has elapsed **and** the hand has settled below the swipe threshold — so one physical swipe reliably produces exactly one key press.

**Config-driven tuning (`gesture_controller/config.py`)**
Every threshold (swipe distance, cooldown, smoothing weight, camera resolution) lives in one `GestureConfig` dataclass, so calibrating for a different camera, lighting setup, or game doesn't require touching detection logic.

## System Design

1. Capture webcam frames (OpenCV)
2. Detect hand landmarks (MediaPipe) and extract the index fingertip position
3. Smooth the position (EMA) and estimate velocity over a short window
4. Classify the velocity as a left/right/up/down swipe against a threshold
5. Pass the swipe through the debounce state machine
6. Fire the mapped key press (PyAutoGUI) on an accepted trigger

## Tech Stack

* Python
* OpenCV
* MediaPipe
* PyAutoGUI

## Controls

* Swipe your hand **left / right / up / down** to trigger the matching key
* Press `q` to quit

## Setup and Installation

```bash
git clone <your-repository-url>
cd hand_gesture_game_controller
pip install -r requirements.txt
python main.py
```

## Tuning

All tunables are in `gesture_controller/config.py`:

| Parameter | Effect |
|---|---|
| `smoothing_alpha` | Lower = smoother but laggier tracking |
| `swipe_threshold_px` | Higher = requires a more deliberate swipe |
| `axis_dominance_ratio` | Higher = stricter about horizontal-vs-vertical intent |
| `action_cooldown_s` | Minimum time between two accepted actions |

## Notes

* Keep the game window in focus for key presses to register
* Good, even lighting improves hand-tracking accuracy
* Only one hand is tracked at a time by default (`max_num_hands` in config)

## Future Work

* Additional gesture types (fist, open palm, pinch) for more game actions
* On-screen calibration UI instead of editing config directly
* Unit tests for `MotionEstimator` and `GestureStateMachine` using recorded landmark sequences

## Attribution

This project started from and was inspired by [Tushar Singh Pawaiya's `hand_gesture_game_controller`](https://github.com/), which combined gesture and voice input. This version is a from-scratch rewrite focused solely on the gesture pipeline, restructured into a modular, class-based design with explicit motion filtering and debounce logic in place of the original's raw-delta/cooldown-timer approach.

## Author

Harshil Chauhan
