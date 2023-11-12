import socket
import time
import colorsys
import glob
import random
import typing
import atexit


def times255(
    self, rgb: typing.Tuple[float, float, float]
) -> typing.Tuple[int, int, int]:
    """
    Multiply RGB set by 255
    """
    return int(rgb[0] * 0xFF), int(rgb[1] * 0xFF), int(rgb[2] * 0xFF)


def custom_frame(row, start, data):
    result = b"\x0f\x03\x00\x00"
    result += bytes((row, start, start + len(data) - 1))
    for rgb in data:
        result += bytes(rgb)
    return result


def times255(rgb):
    return int(rgb[0] * 0xFF), int(rgb[1] * 0xFF), int(rgb[2] * 0xFF)


class RazerCtl:
    def __init__(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(glob.glob("/var/run/razer-analog-*")[0])

    def send(self, data):
        self.sock.sendall(bytes((len(data),)) + data)

        if not data:
            return

        pktlen = self.sock.recv(1)
        received_data = self.sock.recv(pktlen[0])[7 : 7 + len(data)]

        print("received_data, data", received_data, data)

        return received_data


def main():
    razerctl = RazerCtl()

    # wave
    # razerctl.send("\x0f\x02\x01\x05\x04\x01\x20")

    # spectrum cycle
    # razerctl.send("\x0f\x02\x01\x05\x03")

    # custom
    if False:
        razerctl.send(b"\x0f\x02\x00\x00\x08")

    # custom frame
    if False:
        t = time.localtime()
        y = (t.tm_hour * 60 + t.tm_min) / (24 * 60)
        razerctl.send(
            custom_frame(0, 0, (times255(colorsys.hls_to_rgb(y, 0.5, 1)),) * 15)
        )
        razerctl.send(
            custom_frame(1, 0, (times255(colorsys.hls_to_rgb(y, 0.5, 1)),) * 15)
        )
        razerctl.send(
            custom_frame(2, 0, (times255(colorsys.hls_to_rgb(y, 0.5, 1)),) * 15)
        )
        razerctl.send(
            custom_frame(3, 0, (times255(colorsys.hls_to_rgb(y, 0.5, 1)),) * 15)
        )
        razerctl.send(
            custom_frame(4, 0, (times255(colorsys.hls_to_rgb(y, 0.5, 1)),) * 15)
        )
    if False:
        razerctl.send(custom_frame(0, 0, ((0xFF, 0xFF, 0xFF),) * 1))
        razerctl.send(custom_frame(0, 1, ((0, 0, 0),) * 14))

        razerctl.send(custom_frame(1, 0, ((0, 0, 0),) * 2))
        razerctl.send(custom_frame(1, 2, ((0xFF, 0xFF, 0xFF),) * 1))
        razerctl.send(custom_frame(1, 3, ((0, 0, 0),) * 12))

        razerctl.send(custom_frame(2, 0, ((0, 0, 0),) * 1))
        razerctl.send(custom_frame(2, 1, ((0xFF, 0xFF, 0xFF),) * 3))
        razerctl.send(custom_frame(2, 4, ((0, 0, 0),) * 2))
        razerctl.send(custom_frame(2, 6, ((0xFF, 0xFF, 0xFF),) * 4))

        razerctl.send(custom_frame(3, 0, ((0, 0, 0),) * 3))
        razerctl.send(custom_frame(3, 3, ((0xFF, 0xFF, 0xFF),) * 1))
        razerctl.send(custom_frame(3, 4, ((0, 0, 0),) * 12))

        razerctl.send(custom_frame(4, 0, ((0, 0, 0),) * 15))

    if False:
        # brightness
        razerctl.send(b"\x0f\x04\x00\x00\xFF")

    if False:
        # Get layout / ping
        razerctl.send(b"\x00\x86\x00\x00")

    if False:
        # Device mode
        razerctl.send(b"\x00\x04\x03\x00")

    if False:
        razerctl.send(b"\x05\x8A\x00")
        razerctl.send(b"\x05\x03\x1d")
        razerctl.send(b"\x06\x80\x00\x00")
        # memory stats
        # razerctl.send(b"\x06\x8e\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")

        # razerctl.send(b"\x05\x80\x00")
        # razerctl.send(b"\x00\x87\x00")
        # razerctl.send(b"\x05\x88\x00\x00\x00\x00\xfa\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
        # razerctl.send(b"\x05\x81\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
        # razerctl.send(b"\x0f\x82\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
        # razerctl.send(b"\x02\x12\x01\x11\x00\x00\x00\x02\x02\x00\x17\x00\x00\x00")
        # razerctl.send(b"\x02\x12\x05\x11\x00\x00\x00\x02\x02\x00\x05\x00\x00\x00")
        # razerctl.send(b"\x02\x12\x01\x11\x00\x00\x00\x02\x02\x00\x14\x00\x00\x00")
        pass
    if True:
        # left meta = fn
        razerctl.send(b"\x02\x12\x01\x7f\x00\x00\x00\x0c\x01\x01\x00\x00\x00\x00")
        razerctl.send(b"\x02\x12\x01\x7f\x01\x00\x00\x0c\x01\x01\x00\x00\x00\x00")

        razerctl.send(b"\x02\x12\x02\x7f\x00\x00\x00\x0c\x01\x01\x00\x00\x00\x00")
        razerctl.send(b"\x02\x12\x02\x7f\x01\x00\x00\x0c\x01\x01\x00\x00\x00\x00")
    if False:
        # Read presets
        razerctl.send(
            b"\x05\x88\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        )
        razerctl.send(
            b"\x05\x88\x02\x00\x40\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        )
        razerctl.send(
            b"\x05\x88\x02\x00\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        )
        razerctl.send(
            b"\x05\x88\x02\x00\xc0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        )

    while False:
        for row in range(5):
            randoms = []
            for i in range(15):
                randoms.append(
                    times255(colorsys.hls_to_rgb(random.uniform(0, 1), 0.5, 1))
                )
            razerctl.send(custom_frame(row, 0, randoms))
        time.sleep(0.1)

    def shutdown() -> None:
        razerctl.send(b"")

    atexit.register(shutdown)
    # sock.sendall(b"\x0f\x02\x01\x05\x03")
