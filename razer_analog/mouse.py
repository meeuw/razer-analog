"""
Razer Ananlog virtual mouse
"""
import asyncio
import collections
import atexit
import time
import colorsys
import socket
import signal
import sys
import typing
import os.path

import evdev  # type: ignore
import pyudev  # type: ignore


class Mouse:
    """
    Virtual Mouse
    """

    def __init__(self, state: typing.Dict[int, collections.defaultdict[int, int]]):
        self.ui_mouse = evdev.UInput(
            evdev.util.find_ecodes_by_regex(
                r"(REL_X|REL_Y|REL_WHEEL|REL_WHEEL_HI_RES|"
                r"BTN_RIGHT|BTN_MIDDLE|BTN_LEFT|KEY_CAPSLOCK)$"
            )
        )
        self.enabled: bool = False
        self.state: typing.Dict[int, collections.defaultdict[int, int]] = state

    def enable(self) -> None:
        """
        Enable mouse
        """
        self.enabled = True

    def disable(self) -> None:
        """
        Disable mouse
        """
        self.enabled = False

    def handle(self, from_event: int, to_event: int, direction: int) -> None:
        """
        Handle event
        """
        value = self.state[evdev.ecodes.ecodes["EV_ABS"]][from_event]

        if value:
            value = 0.000000000749 * pow(value, 4.5) + 1
            self.ui_mouse.write(
                evdev.ecodes.ecodes["EV_REL"], to_event, int(value) * direction
            )

    def write(self, typ: int, code: int, value: int) -> None:
        """
        Write event
        """
        self.ui_mouse.write(typ, code, value)

    async def run(self) -> None:
        """
        Main loop
        """
        while True:
            if self.enabled:
                await asyncio.sleep(0.05)
                self.handle(evdev.ecodes.ABS_HAT0X, evdev.ecodes.REL_X, -1)
                self.handle(evdev.ecodes.ABS_HAT0Y, evdev.ecodes.REL_Y, 1)
                self.handle(evdev.ecodes.ABS_HAT1X, evdev.ecodes.REL_Y, -1)
                self.handle(evdev.ecodes.ABS_HAT1Y, evdev.ecodes.REL_X, 1)
                value = self.state[evdev.ecodes.EV_ABS][evdev.ecodes.ABS_HAT2Y]
                if value:
                    self.ui_mouse.write(
                        evdev.ecodes.EV_REL,
                        evdev.ecodes.REL_WHEEL_HI_RES,
                        int(value) * -1,
                    )
                    self.ui_mouse.write(evdev.ecodes.EV_REL, evdev.ecodes.REL_WHEEL, -1)
                value = self.state[evdev.ecodes.EV_ABS][evdev.ecodes.ABS_HAT2X]
                if value:
                    self.ui_mouse.write(
                        evdev.ecodes.EV_REL,
                        evdev.ecodes.REL_WHEEL_HI_RES,
                        int(value) * 1,
                    )
                    self.ui_mouse.write(evdev.ecodes.EV_REL, evdev.ecodes.REL_WHEEL, 1)

                self.ui_mouse.syn()
            else:
                await asyncio.sleep(0.1)


class Chroma:
    """
    Chroma lighting
    """

    def __init__(self, razer_analog_pid: int):
        sock_file = f"/var/run/razer-analog-{razer_analog_pid}"
        for _ in range(10):
            if os.path.exists(sock_file):
                break
            time.sleep(0.1)

        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(sock_file)
        self.sock.settimeout(1)
        # custom
        self.do_time_of_day = True
        self.brightness = 0xFF
        self.time_of_day()

    def custom_frame(
        self, row: int, start: int, data: typing.Tuple[typing.Tuple[int, int, int], ...]
    ) -> bytes:
        """
        Enable custom frame mode (so we can manually enable LEDs)
        """
        result = b"\x0f\x03\x00\x00"
        result += bytes((row, start, start + len(data) - 1))
        for rgb in data:
            result += bytes(rgb)
        return result

    def send(self, data: bytes) -> None:
        """
        Send data using simple protocol (len + data)
        """
        try:
            self.sock.sendall(bytes((len(data),)) + data)
        except BrokenPipeError as exception:
            print("failed to send", exception)

        if not data:
            return

        pktlen = self.sock.recv(1)

        received_data = self.sock.recv(pktlen[0])[7 : 7 + len(data)]
        if received_data != data:
            print("received_data != data", received_data, data)

    def times255(
        self, rgb: typing.Tuple[float, float, float]
    ) -> typing.Tuple[int, int, int]:
        """
        Multiply RGB set by 255
        """
        return int(rgb[0] * 0xFF), int(rgb[1] * 0xFF), int(rgb[2] * 0xFF)

    def mouse(self) -> None:
        """
        Enable custom frame for mouse mode
        """
        self.do_time_of_day = False
        self.send(self.custom_frame(0, 0, ((0xFF, 0xFF, 0xFF),) * 1))
        self.send(self.custom_frame(0, 1, ((0, 0, 0),) * 14))

        self.send(self.custom_frame(1, 0, ((0, 0, 0),) * 2))
        self.send(self.custom_frame(1, 2, ((0xFF, 0xFF, 0xFF),) * 1))
        self.send(self.custom_frame(1, 3, ((0, 0, 0),) * 12))

        self.send(self.custom_frame(2, 0, ((0xFF, 0xFF, 0xFF),) * 4))
        self.send(self.custom_frame(2, 4, ((0, 0, 0),) * 2))
        self.send(self.custom_frame(2, 6, ((0xFF, 0xFF, 0xFF),) * 4))
        self.send(self.custom_frame(2, 10, ((0, 0, 0),) * 5))

        self.send(self.custom_frame(3, 0, ((0, 0, 0),) * 3))
        self.send(self.custom_frame(3, 3, ((0xFF, 0xFF, 0xFF),) * 1))
        self.send(self.custom_frame(3, 4, ((0, 0, 0),) * 11))

        self.send(self.custom_frame(4, 0, ((0, 0, 0),) * 15))

    def time_of_day(self) -> None:
        """
        Enable custom frame for time of day mode
        """
        self.do_time_of_day = True
        self.send(b"\x0f\x02\x00\x05\x08")
        localtime = time.localtime()
        hue = (localtime.tm_hour * 60 + localtime.tm_min) / (24 * 60)
        for row in range(5):
            self.send(
                self.custom_frame(
                    row, 0, (self.times255(colorsys.hls_to_rgb(hue, 0.5, 1)),) * 15
                )
            )

    def highlight_fn(self) -> None:
        """
        Highlight buttons that can be used with fn
        """
        self.send(self.custom_frame(0, 0, ((0xFF, 0xFF, 0xFF),) * 15))

        self.send(self.custom_frame(1, 0, ((0xFF, 0xFF, 0xFF),) * 13))
        self.send(self.custom_frame(1, 13, ((0x00, 0x00, 0x00),) * 2))

        self.send(self.custom_frame(2, 0, ((0x00, 0x00, 0x00),) * 5))
        self.send(self.custom_frame(2, 5, ((0xFF, 0xFF, 0xFF),) * 7))
        self.send(self.custom_frame(2, 12, ((0x00, 0x00, 0x00),) * 3))

        self.send(self.custom_frame(3, 0, ((0x00, 0x00, 0x00),) * 9))
        self.send(self.custom_frame(3, 9, ((0xFF, 0xFF, 0xFF),) * 3))
        self.send(self.custom_frame(3, 12, ((0x00, 0x00, 0x00),) * 3))

        self.send(self.custom_frame(4, 0, ((0x00, 0x00, 0x00),) * 15))

    def highlight_shift(self) -> None:
        """
        Highlight buttons that can be used with shift
        """
        self.send(self.custom_frame(0, 0, ((0x00, 0x00, 0x00),) * 1))
        self.send(self.custom_frame(0, 1, ((0xFF, 0xFF, 0xFF),) * 13))
        self.send(self.custom_frame(0, 14, ((0x00, 0x00, 0x00),) * 1))

        self.send(self.custom_frame(1, 0, ((0xFF, 0xFF, 0xFF),) * 15))

        self.send(self.custom_frame(2, 0, ((0x00, 0x00, 0x00),) * 1))
        self.send(self.custom_frame(2, 1, ((0xFF, 0xFF, 0xFF),) * 14))

        self.send(self.custom_frame(3, 0, ((0x00, 0x00, 0x00),) * 1))
        self.send(self.custom_frame(3, 1, ((0xFF, 0xFF, 0xFF),) * 11))
        self.send(self.custom_frame(3, 12, ((0x00, 0x00, 0x00),) * 3))

        self.send(self.custom_frame(4, 0, ((0x00, 0x00, 0x00),) * 15))

    def highlight_shift_fn(self) -> None:
        """
        Highlight buttons that can be used with shift-fn
        """
        self.send(self.custom_frame(0, 0, ((0xFF, 0xFF, 0xFF),) * 15))

        self.send(self.custom_frame(1, 0, ((0x00, 0x00, 0x00),) * 8))
        self.send(self.custom_frame(1, 8, ((0xFF, 0xFF, 0xFF),) * 5))
        self.send(self.custom_frame(1, 13, ((0x00, 0x00, 0x00),) * 2))

        self.send(self.custom_frame(2, 0, ((0x00, 0x00, 0x00),) * 7))
        self.send(self.custom_frame(2, 7, ((0xFF, 0xFF, 0xFF),) * 5))
        self.send(self.custom_frame(2, 12, ((0x00, 0x00, 0x00),) * 3))

        self.send(self.custom_frame(3, 0, ((0x00, 0x00, 0x00),) * 11))
        self.send(self.custom_frame(3, 11, ((0xFF, 0xFF, 0xFF),) * 1))
        self.send(self.custom_frame(3, 12, ((0x00, 0x00, 0x00),) * 3))

        self.send(self.custom_frame(4, 0, ((0x00, 0x00, 0x00),) * 15))

    def adjust_brightness(self, offset: int) -> None:
        """
        Adjust brightness of LEDs
        """
        self.brightness += offset
        self.brightness = min(max(self.brightness, 0), 0xFF)
        self.send(b"\x0f\x04\x00\x00" + bytes((self.brightness,)))

    async def run(self) -> None:
        """
        Main loop
        """
        while 1:
            await asyncio.sleep(60)
            if self.do_time_of_day:
                self.time_of_day()


async def keyboard(
    razer_analog_keyboard: evdev.InputDevice,
    state: typing.Dict[int, collections.defaultdict[int, int]],
    mouse: Mouse,
    chroma: Chroma,
) -> None:
    """
    Watch keyboard events
    """
    shift_pressed = False
    fn_pressed = False
    try:
        async for event in razer_analog_keyboard.async_read_loop():
            state[event.type][event.code] = event.value

            if mouse.enabled:
                if (
                    event.type == evdev.ecodes.ecodes["EV_KEY"]
                    and event.code == evdev.ecodes.ecodes["KEY_CAPSLOCK"]
                ):
                    mouse.write(
                        evdev.ecodes.ecodes["EV_KEY"],
                        evdev.ecodes.ecodes["KEY_CAPSLOCK"],
                        event.value,
                    )
                if (
                    event.type == evdev.ecodes.ecodes["EV_KEY"]
                    and event.code == evdev.ecodes.ecodes["KEY_A"]
                ):
                    mouse.write(
                        evdev.ecodes.ecodes["EV_KEY"],
                        evdev.ecodes.ecodes["BTN_LEFT"],
                        event.value,
                    )
                if (
                    event.type == evdev.ecodes.ecodes["EV_KEY"]
                    and event.code == evdev.ecodes.ecodes["KEY_S"]
                ):
                    mouse.write(
                        evdev.ecodes.ecodes["EV_KEY"],
                        evdev.ecodes.ecodes["BTN_MIDDLE"],
                        event.value,
                    )
                if (
                    event.type == evdev.ecodes.ecodes["EV_KEY"]
                    and event.code == evdev.ecodes.ecodes["KEY_D"]
                ):
                    mouse.write(
                        evdev.ecodes.ecodes["EV_KEY"],
                        evdev.ecodes.ecodes["BTN_RIGHT"],
                        event.value,
                    )
                if (
                    event.type == evdev.ecodes.ecodes["EV_KEY"]
                    and event.code == evdev.ecodes.ecodes["KEY_ESC"]
                ):
                    mouse.disable()
                    chroma.time_of_day()
                    razer_analog_keyboard.ungrab()
            else:
                if (
                    event.type == evdev.ecodes.ecodes["EV_KEY"]
                    and event.code == evdev.ecodes.ecodes["KEY_KEYBOARD"]
                    and event.value
                ):
                    chroma.mouse()
                    while razer_analog_keyboard.active_keys():
                        await asyncio.sleep(0.1)
                    # fingers crossed no keys are pressed..
                    razer_analog_keyboard.grab()

                    mouse.enable()
                elif (
                    event.type == evdev.ecodes.ecodes["EV_KEY"]
                    and event.code == evdev.ecodes.ecodes["KEY_FN"]
                ):
                    if event.value:
                        fn_pressed = True
                        if shift_pressed:
                            chroma.highlight_shift_fn()
                        else:
                            chroma.highlight_fn()
                    else:
                        fn_pressed = False
                        chroma.time_of_day()

                elif event.type == evdev.ecodes.ecodes["EV_KEY"] and event.code in (
                    evdev.ecodes.ecodes["KEY_LEFTSHIFT"],
                    evdev.ecodes.ecodes["KEY_RIGHTSHIFT"],
                ):
                    if event.value:
                        if fn_pressed:
                            chroma.highlight_shift_fn()
                        else:
                            chroma.highlight_shift()

                        shift_pressed = True
                    else:
                        chroma.time_of_day()
                        shift_pressed = False
                elif (
                    event.type == evdev.ecodes.ecodes["EV_KEY"]
                    and event.code == evdev.ecodes.ecodes["KEY_KBDILLUMDOWN"]
                ):
                    chroma.adjust_brightness(-0x0F)
                elif (
                    event.type == evdev.ecodes.ecodes["EV_KEY"]
                    and event.code == evdev.ecodes.ecodes["KEY_KBDILLUMUP"]
                ):
                    chroma.adjust_brightness(0x0F)

    except OSError as exception:
        print(exception, "exiting")
        sys.exit()


def main() -> None:
    """
    Main loop
    """
    context = pyudev.Context()
    # run: udevadm info -t
    # search for "razer-analog-keyboard-"
    # Use the child of this device (event*) (P:):
    # /sys/devices/virtual/input/input39/event23
    udev = pyudev.Devices.from_path(context, sys.argv[1])
    razer_analog_keyboard = evdev.InputDevice(udev.device_node)

    razer_analog_pid = razer_analog_keyboard.name.split("-")[-1]
    print(razer_analog_keyboard)

    state: typing.Dict[int, collections.defaultdict[int, int]] = {
        evdev.ecodes.ecodes["EV_SYN"]: collections.defaultdict(int),
        evdev.ecodes.ecodes["EV_ABS"]: collections.defaultdict(int),
        evdev.ecodes.ecodes["EV_KEY"]: collections.defaultdict(int),
    }
    mouse = Mouse(state)
    chroma = Chroma(razer_analog_pid)

    tasks = asyncio.gather(
        mouse.run(), keyboard(razer_analog_keyboard, state, mouse, chroma), chroma.run()
    )

    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGTERM, tasks.cancel)

    def shutdown() -> None:
        chroma.send(b"")

    atexit.register(shutdown)
    loop.run_until_complete(tasks)
