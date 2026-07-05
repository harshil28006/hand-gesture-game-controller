"""
Debounce logic for gesture-to-action triggering.

A raw "if enough time has passed, fire again" cooldown timer (the
approach in most quick gesture-control scripts) tends to double-fire on
the trailing edge of a single swipe, because the hand is still moving
when the cooldown expires. Modeling this explicitly as a small state
machine makes the intended behavior clear and easy to tune:

    IDLE --swipe detected--> FIRED --cooldown elapsed--> IDLE

While in FIRED, no new action is accepted regardless of new motion,
until both the cooldown has elapsed AND the hand has returned below the
swipe threshold (settled). This "settle" requirement is what prevents
the double-fire, since a single continuous swipe motion no longer re-
triggers immediately once the cooldown timer alone runs out.
"""

import time
from enum import Enum, auto


class GestureState(Enum):
    IDLE = auto()
    FIRED = auto()


class GestureStateMachine:
    def __init__(self, cooldown_s: float):
        self.cooldown_s = cooldown_s
        self.state = GestureState.IDLE
        self._fired_at = 0.0

    def try_fire(self, swipe_detected: bool) -> bool:
        """
        Call once per frame with whether a swipe condition is currently
        met. Returns True exactly on frames where an action should be
        triggered.
        """
        now = time.time()

        if self.state == GestureState.IDLE:
            if swipe_detected:
                self.state = GestureState.FIRED
                self._fired_at = now
                return True
            return False

        # state == FIRED
        cooldown_elapsed = (now - self._fired_at) >= self.cooldown_s
        settled = not swipe_detected
        if cooldown_elapsed and settled:
            self.state = GestureState.IDLE
        return False
