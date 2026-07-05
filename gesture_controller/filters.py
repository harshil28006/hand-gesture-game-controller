"""
Motion filtering for fingertip tracking.

Raw MediaPipe landmark coordinates are noisy frame-to-frame (sub-pixel
jitter from the detector, hand tremor, lighting flicker). Differencing
two noisy positions directly gives a noisy velocity estimate, which is
what caused false-positive swipes in the original raw-delta approach.

We fix this with two layers, mirroring how you'd clean up a noisy sensor
signal before feeding it to a controller:

1. An Exponential Moving Average (EMA) low-pass filter on position,
   which suppresses high-frequency jitter while still tracking real
   motion with low lag.
2. A short sliding window over the *filtered* positions to estimate
   velocity (dx, dy) as an average slope rather than a single-step
   difference, which further rejects one-frame outliers.
"""

from collections import deque


class ExponentialMovingAverage:
    """Simple 2D EMA filter: y[n] = alpha * x[n] + (1 - alpha) * y[n-1]."""

    def __init__(self, alpha: float):
        if not 0.0 < alpha <= 1.0:
            raise ValueError("alpha must be in (0, 1]")
        self.alpha = alpha
        self._value = None

    def update(self, point: tuple[float, float]) -> tuple[float, float]:
        if self._value is None:
            self._value = point
        else:
            px, py = self._value
            x, y = point
            self._value = (
                self.alpha * x + (1 - self.alpha) * px,
                self.alpha * y + (1 - self.alpha) * py,
            )
        return self._value

    def reset(self):
        self._value = None


class MotionEstimator:
    """
    Wraps an EMA position filter with a sliding-window velocity estimate.

    Call `update(point)` every frame with the raw (x, y) fingertip
    position. Once enough samples are buffered, `velocity()` returns the
    average (dx, dy) per frame over the window, computed on the smoothed
    trajectory.
    """

    def __init__(self, alpha: float, history_length: int):
        self._ema = ExponentialMovingAverage(alpha)
        self._history: deque[tuple[float, float]] = deque(maxlen=history_length)

    def update(self, point: tuple[float, float]) -> None:
        smoothed = self._ema.update(point)
        self._history.append(smoothed)

    def is_ready(self) -> bool:
        return len(self._history) == self._history.maxlen

    def velocity(self) -> tuple[float, float]:
        """Average per-frame (dx, dy) across the buffered window."""
        if len(self._history) < 2:
            return 0.0, 0.0
        n = len(self._history) - 1
        dx = sum(self._history[i + 1][0] - self._history[i][0] for i in range(n)) / n
        dy = sum(self._history[i + 1][1] - self._history[i][1] for i in range(n)) / n
        return dx, dy

    def reset(self):
        self._ema.reset()
        self._history.clear()
