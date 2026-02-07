import argparse
import base64
import io
import logging
import os
import subprocess
import threading
from functools import partial

os.environ.setdefault("PYSTRAY_BACKEND", "appindicator")

import pystray
from PIL import Image

from mx_master_4 import MXMaster4


TRAY_ICON = """
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
"""


class NotificationTrayApp:
    def __init__(self, device: MXMaster4, vibration_id: int):
        self.device = device
        self.vibration_id = vibration_id
        self.listening = False
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._dbus_process: subprocess.Popen | None = None
        self.icon = None
        self._setup_tray()
        self._start_listening()

    def _setup_tray(self):
        vibration_menu = pystray.Menu(
            *[
                pystray.MenuItem(
                    f"Vibration {i}",
                    partial(self.set_vibration, pattern_id=i),
                    checked=lambda item, i=i: self.vibration_id == i,
                )
                for i in range(1, 16)
            ]
        )
        menu = (
            pystray.MenuItem("Select vibration", vibration_menu),
            pystray.MenuItem("Exit", self.exit_app),
        )
        self.icon = pystray.Icon("mx4notifications", self.set_icon(), "MX4 haptic notification", menu)

    def set_icon(self):
        return Image.open(io.BytesIO(base64.b64decode(TRAY_ICON)))

    def set_vibration(self, _icon, _item, pattern_id: int):
        self.vibration_id = pattern_id

    def _start_listening(self):
        if self.listening:
            return
        self.listening = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitor_notifications, daemon=True)
        self._thread.start()

    def stop_listening(self, _icon=None, _item=None):
        if not self.listening:
            return
        self.listening = False
        self._stop_event.set()
        if self._dbus_process and self._dbus_process.poll() is None:
            self._dbus_process.terminate()
        if self._thread:
            self._thread.join(timeout=1)
        self._thread = None

    def exit_app(self, _icon, _item):
        self.stop_listening()
        if self.icon:
            self.icon.stop()

    def _monitor_notifications(self):
        """Monitor D-Bus for notifications using dbus-monitor"""
        cmd = [
            "dbus-monitor",
            "--session",
            "interface='org.freedesktop.Notifications',member='Notify'",
        ]

        logging.info("Starting dbus-monitor...")
        self._dbus_process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1
        )

        try:
            for line in self._dbus_process.stdout:
                if self._stop_event.is_set():
                    break
                line = line.strip()
                if line:
                    logging.debug("D-Bus: %s", line)
                    # When we see a Notify method call, trigger haptic
                    if "member=Notify" in line or "method call" in line.lower():
                        try:
                            self.device.haptic(self.vibration_id)
                            logging.info("✓ Haptic feedback triggered!")
                        except Exception as e:
                            logging.error("Failed to trigger haptic: %s", e)
        finally:
            if self._dbus_process and self._dbus_process.poll() is None:
                self._dbus_process.terminate()
            self._dbus_process = None

    def run(self):
        self.icon.run()


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="MX Master 4 notifications listener.")
    parser.add_argument(
        "--vibration",
        type=int,
        default=1,
        help="Haptic pattern id to use (1-15). Default is 1.",
    )
    args = parser.parse_args()
    if not 1 <= args.vibration <= 15:
        raise SystemExit("Vibration must be between 1 and 15.")

    preference = (os.getenv("MX4_CONNECTION") or "auto").lower()
    if preference == "bluetooth":
        device = MXMaster4.find(prefer_bluetooth=True)
    elif preference == "usb":
        device = MXMaster4.find(prefer_bluetooth=False)
    else:
        device = MXMaster4.find(prefer_bluetooth=False)

    if not device:
        logging.error("MX Master 4 not found!")
        exit(1)

    with device as dev:
        logging.info("MX Master 4 connected!")
        logging.info("Test with: notify-send 'Test' 'Message'")
        logging.info("")
        app = NotificationTrayApp(dev, vibration_id=args.vibration)
        app.run()


if __name__ == "__main__":
    main()
