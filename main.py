#!/usr/bin/env python3
"""Entry point for the Meeting Focus Tracker."""

from __future__ import annotations

import logging
import sys

from config import Config
from tracker import MeetingFocusTracker


def main() -> None:
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Validate required config
    missing = Config.validate()
    if missing:
        print(f"Missing required config: {', '.join(missing)}")
        print("Set them in .env or as environment variables.")
        sys.exit(1)

    # Get calendar description
    description = Config.CALENDAR_DESCRIPTION
    if not description.strip():
        print("No CALENDAR_DESCRIPTION found in .env.")
        print("Paste the calendar event description below (empty line to finish):")
        lines: list[str] = []
        try:
            while True:
                line = input()
                if line == "":
                    break
                lines.append(line)
        except EOFError:
            pass
        description = "\n".join(lines)

    if not description.strip():
        print("No calendar description provided. Exiting.")
        sys.exit(1)

    # Run tracker
    tracker = MeetingFocusTracker()
    tracker.run(description)


if __name__ == "__main__":
    main()
