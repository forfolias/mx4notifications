import logging
from enum import IntEnum
from struct import pack, unpack

import hid

LOGITECH_VID = 0x046D
USAGE_PAGE_HIDPP = 0xFF00
BUS_USB = 0x03
BUS_BLUETOOTH = 0x05
PRODUCT_HINTS = ("mx master 4", "mx master")
WEBHID_REPORT_ID = 0x11
WEBHID_REPORT_LENGTH = 19
WEBHID_DEVICE_INDEX = 0x02


class ReportID(IntEnum):
    Short = 0x10  # 7 bytes
    Long = 0x11  # 20 bytes


class FunctionID(IntEnum):
    IRoot = 0x0000
    IFeatureSet = 0x0001
    IFeatureInfo = 0x0002

    Haptic = 0x0B4E


class MXMaster4:
    device: hid.Device | None = None

    def __init__(self, path: str, device_idx: int, bus_type: int | None):
        self.path = path
        self.device_idx = device_idx
        self.is_bluetooth = self._is_bluetooth(bus_type)

    @staticmethod
    def _is_bluetooth(bus_type: int | str | None) -> bool:
        if hasattr(bus_type, "name"):
            try:
                return "bluetooth" in bus_type.name.lower()
            except Exception:
                pass
        if isinstance(bus_type, str):
            return "bluetooth" in bus_type.lower()
        if isinstance(bus_type, int):
            return bus_type == BUS_BLUETOOTH
        return False

    @classmethod
    def find(cls, prefer_bluetooth: bool = False):
        devices = hid.enumerate(LOGITECH_VID)
        candidates = []

        for device in devices:
            product = (device.get("product_string") or "").lower()
            usage_page = device.get("usage_page")
            if usage_page != USAGE_PAGE_HIDPP and not any(
                    hint in product for hint in PRODUCT_HINTS
            ):
                continue

            path = device.get("path")
            if isinstance(path, bytes):
                path = path.decode("utf-8", errors="ignore")
            else:
                path = str(path)

            device_idx = device.get("interface_number")
            if not isinstance(device_idx, int) or not 0 <= device_idx <= 0xFF:
                device_idx = 0x00

            bus_type = device.get("bus_type")
            score = 0
            if usage_page == USAGE_PAGE_HIDPP:
                score += 2
            if any(hint in product for hint in PRODUCT_HINTS):
                score += 1
            if bus_type == BUS_BLUETOOTH:
                score += 2 if prefer_bluetooth else 1
            elif bus_type == BUS_USB:
                score += 2 if not prefer_bluetooth else 1

            candidates.append((score, path, device_idx, device))

        if not candidates:
            return None

        candidates.sort(key=lambda entry: entry[0], reverse=True)
        _, path, device_idx, device = candidates[0]
        logging.debug("Found: %s", device.get("product_string"))
        logging.debug("\tPath: %s", path)
        logging.debug(
            "\tVID:PID: %.04X:%.04X",
            device.get("vendor_id", 0),
            device.get("product_id", 0),
        )
        logging.debug("\tInterface: %s", device.get("interface_number"))
        logging.debug("\tBus: %s", device.get("bus_type"))
        return cls(path, device_idx, device.get("bus_type"))

    def __enter__(self):
        self.device = hid.Device(path=self.path.encode())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.device.close()

    def write(self, data: bytes):
        if not self.device:
            raise Exception("Device not open")
        self.device.write(data)

    def haptic(self, pattern_id: int):
        if self.is_bluetooth:
            return self._webhid_haptic(pattern_id)
        return self.hidpp(FunctionID.Haptic, pattern_id)

    def _webhid_haptic(self, pattern_id: int):
        if not 0 <= pattern_id <= 0xFF:
            raise Exception("Haptic pattern out of range")
        payload = bytearray(WEBHID_REPORT_LENGTH)
        payload[0] = WEBHID_DEVICE_INDEX
        payload[1] = (int(FunctionID.Haptic) >> 8) & 0xFF
        payload[2] = int(FunctionID.Haptic) & 0xFF
        payload[3] = pattern_id
        report = bytes([WEBHID_REPORT_ID]) + payload
        logging.debug(
            "Sending: %02X %s",
            WEBHID_REPORT_ID,
            payload.hex(),
        )
        self.write(report)

    def hidpp(
            self,
            feature_idx: FunctionID,
            *args: int,
    ) -> tuple[int, bytes]:
        if len(args) > 16:
            raise Exception("Too many arguments")

        data = bytes(args)
        if len(data) < 3:
            data += bytes([0]) * (3 - len(data))

        report_id = ReportID.Short if len(data) == 3 else ReportID.Long
        logging.debug(
            f"Sending: {report_id:02X} {self.device_idx:02X} {feature_idx:04X} {data.hex()}"
        )
        packet = pack(b">BBH3s", report_id, self.device_idx, feature_idx, data)
        self.write(packet)
        return self.read()

    def read(self) -> tuple[int, bytes]:
        response: bytes
        r_f_idx: int

        response = self.device.read(20)

        # print(f"Response: {' '.join(f'{b:02X}' for b in response)}")
        (r_report_id, r_device_idx, r_f_idx) = unpack(b">BBH", response[:4])
        if r_device_idx != self.device_idx:
            return self.read()

        if r_report_id == ReportID.Short:
            data = response[4:]
            if len(data) != 7 - 4:
                raise Exception("Wrong short report length")
        elif r_report_id == ReportID.Long:
            data = response[4:]
            if len(data) != 20 - 4:
                raise Exception("Wrong long report length")
        else:
            raise Exception("Unknown report ID")

        return r_f_idx, response[4:]


def demo():
    from time import sleep

    logging.basicConfig(level=logging.DEBUG)

    mx_master_4 = MXMaster4.find()

    if not mx_master_4:
        logging.error("MX Master 4 not found!")
        exit(1)

    with mx_master_4 as dev:
        for i in range(15):
            logging.info("Haptic %d", i)
            dev.haptic(i)
            sleep(3)


if __name__ == "__main__":
    demo()
