"""
Core controller: wires webcam capture, MediaPipe hand tracking, motion
filtering, and gesture-to-keypress mapping together.
"""

import logging
import time

import cv2
import mediapipe as mp
import pyautogui

from .config import GestureConfig
from .filters import MotionEstimator
from .state_machine import GestureStateMachine

logger = logging.getLogger(__name__)

# Index fingertip landmark ID in MediaPipe's 21-point hand model.
INDEX_FINGERTIP_ID = 8


class HandGestureController:
    """
    Tracks the index fingertip and converts swipe gestures into
    keyboard presses for browser-game control.
    """

    def __init__(self, config: GestureConfig | None = None):
        self.config = config or GestureConfig()

        self._mp_hands = mp.solutions.hands
        self._hands = self._mp_hands.Hands(
            max_num_hands=self.config.max_num_hands,
            min_detection_confidence=self.config.min_detection_confidence,
            min_tracking_confidence=self.config.min_tracking_confidence,
        )
        self._draw = mp.solutions.drawing_utils

        self._motion = MotionEstimator(
            alpha=self.config.smoothing_alpha,
            history_length=self.config.history_length,
        )
        self._debounce = GestureStateMachine(cooldown_s=self.config.action_cooldown_s)

        self._cap = None
        self._last_action_label = ""
        self._last_action_time = 0.0

    # -- lifecycle -----------------------------------------------------

    def open_camera(self) -> None:
        self._cap = cv2.VideoCapture(self.config.camera_index)
        if not self._cap.isOpened():
            raise RuntimeError(
                f"Could not open camera at index {self.config.camera_index}. "
                "Check that it's connected and not in use by another app."
            )
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.frame_width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.frame_height)
        logger.info("Camera opened (index=%d)", self.config.camera_index)

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
        cv2.destroyAllWindows()
        logger.info("Camera released, windows closed")

    # -- per-frame processing ------------------------------------------

    def _classify_swipe(self, dx: float, dy: float) -> str | None:
        cfg = self.config
        abs_dx, abs_dy = abs(dx), abs(dy)

        if abs_dx > cfg.swipe_threshold_px and abs_dx > cfg.axis_dominance_ratio * abs_dy:
            return "right" if dx > 0 else "left"

        if abs_dy > cfg.swipe_threshold_px and abs_dy > cfg.axis_dominance_ratio * abs_dx:
            return "down" if dy > 0 else "up"

        return None

    def _trigger(self, direction: str) -> None:
        key = self.config.key_map[direction]
        pyautogui.press(key)
        self._last_action_label = f"Gesture: {direction.capitalize()}"
        self._last_action_time = time.time()
        logger.info("Action fired: %s -> key '%s'", direction, key)

    def process_frame(self, frame):
        """
        Run detection + filtering + debounced action-firing on a single
        BGR frame. Returns the annotated frame (for display) so this
        method stays usable in tests without a live window.
        """
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self._hands.process(rgb)
        h, w, _ = frame.shape

        swipe_direction = None

        if result.multi_hand_landmarks:
            hand_landmarks = result.multi_hand_landmarks[0]
            self._draw.draw_landmarks(frame, hand_landmarks, self._mp_hands.HAND_CONNECTIONS)

            landmark = hand_landmarks.landmark[INDEX_FINGERTIP_ID]
            # x is flipped to match the mirrored camera view used for display.
            x = w - int(landmark.x * w)
            y = int(landmark.y * h)

            self._motion.update((x, y))

            if self._motion.is_ready():
                dx, dy = self._motion.velocity()
                swipe_direction = self._classify_swipe(dx, dy)
        else:
            # No hand in frame: don't let stale history trigger a false swipe.
            self._motion.reset()

        if self._debounce.try_fire(swipe_direction is not None):
            self._trigger(swipe_direction)

        self._draw_overlay(frame)
        return frame

    def _draw_overlay(self, frame) -> None:
        cv2.putText(frame, "Press q to quit", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        if self._last_action_label:
            cv2.putText(frame, self._last_action_label, (10, 65),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
            if time.time() - self._last_action_time > self.config.idle_reset_s:
                self._last_action_label = ""

    # -- main loop -------------------------------------------------------

    def run(self) -> None:
        self.open_camera()
        logger.info("Starting main loop. Swipe to trigger keys, 'q' to quit.")
        try:
            while True:
                success, frame = self._cap.read()
                if not success:
                    logger.warning("Frame grab failed, retrying")
                    continue

                frame = cv2.flip(frame, 1)
                frame = self.process_frame(frame)
                cv2.imshow("Hand Gesture Game Controller", frame)

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
        finally:
            self.close()
