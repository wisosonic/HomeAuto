"""Print events from all sensors. Run on the Pi:  python demos/watch_all.py [pir sound ...]"""

import logging
import sys
import time
from datetime import datetime

from homeauto.pinmap import DEFAULT_PINS
from homeauto.sensors import create_sensors


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    wanted = sys.argv[1:] or list(DEFAULT_PINS)
    sensors = create_sensors({n: DEFAULT_PINS[n] for n in wanted})

    def show(ev):
        t = datetime.fromtimestamp(ev.timestamp).strftime("%H:%M:%S")
        print(f"{t}  {ev.sensor:<12} {ev.kind:<10} {'ACTIVE' if ev.active else 'idle'}")

    for s in sensors.values():
        s.add_listener(show)
    print("Watching:", ", ".join(f"{n}(GPIO{s.pin})" for n, s in sensors.items()), "- Ctrl+C to stop")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for s in sensors.values():
            s.close()


if __name__ == "__main__":
    main()
