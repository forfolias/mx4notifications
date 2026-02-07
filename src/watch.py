import logging
import os
import subprocess

from mx_master_4 import MXMaster4


def monitor_notifications(device):
    """Monitor D-Bus for notifications using dbus-monitor"""
    cmd = [
        "dbus-monitor",
        "--session",
        "interface='org.freedesktop.Notifications',member='Notify'",
    ]

    logging.info("Starting dbus-monitor...")
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1
    )

    try:
        for line in process.stdout:
            line = line.strip()
            if line:
                logging.debug("D-Bus: %s", line)
                # When we see a Notify method call, trigger haptic
                if "member=Notify" in line or "method call" in line.lower():
                    try:
                        device.haptic(0)
                        logging.info("✓ Haptic feedback triggered!")
                    except Exception as e:
                        logging.error("Failed to trigger haptic: %s", e)
    except KeyboardInterrupt:
        process.terminate()
        raise


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

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
        logging.info("Listening for notifications... Press Ctrl+C to stop.")
        logging.info("Test with: notify-send 'Test' 'Message'")
        logging.info("")

        try:
            monitor_notifications(dev)
        except KeyboardInterrupt:
            logging.info("\nStopping...")


if __name__ == "__main__":
    main()
