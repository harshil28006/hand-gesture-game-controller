"""
Configuration for the gesture controller.

Keeping every tunable value in one dataclass makes it easy to calibrate
the system for a different camera, lighting condition, or game without
touching the detection/control logic.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class GestureConfig:
    # --- Camera ---
    camera_index: int = 0
    frame_width: int = 640
    frame_height: int = 480

    # --- MediaPipe hand detection ---
    max_num_hands: int = 1
    min_detection_confidence: float = 0.7
    min_tracking_confidence: float = 0.7

    # --- Motion smoothing (see filters.MotionFilter) ---
    smoothing_alpha: float = 0.4       # EMA weight given to the newest sample
    history_length: int = 5            # frames used to estimate velocity

    # --- Swipe classification ---
    swipe_threshold_px: float = 18.0   # min smoothed displacement to count as a swipe
    axis_dominance_ratio: float = 1.2  # how much larger |dx| must be than |dy| (or vice versa)

    # --- Debounce state machine (see state_machine.GestureStateMachine) ---
    action_cooldown_s: float = 0.6     # min time between two accepted actions
    idle_reset_s: float = 1.5          # time with no motion before status text clears

    # --- Key bindings ---
    key_map: dict = None

    def __post_init__(self):
        if self.key_map is None:
            object.__setattr__(
                self,
                "key_map",
                {
                    "right": "right",
                    "left": "left",
                    "up": "up",
                    "down": "down",
                },
            )
