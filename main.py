"""
Entry point for the Hand Gesture Game Controller.

Run:
    python main.py
"""

import logging

from gesture_controller.config import GestureConfig
from gesture_controller.controller import HandGestureController


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    config = GestureConfig()  # tweak thresholds/cooldowns in config.py
    controller = HandGestureController(config)

    try:
        controller.run()
    except RuntimeError as e:
        logging.error(str(e))
    except KeyboardInterrupt:
        logging.info("Interrupted by user, shutting down")
        controller.close()


if __name__ == "__main__":
    main()
