"""
Razer Analog driver
"""
import asyncio
import os
import struct
import atexit
import signal
import sys
import typing
import io
import time

import evdev  # type: ignore
import pyudev  # type: ignore

import razer_analog.layout
import razer_analog.hidraw


class HuntsmanMiniAnalog:
    """
    Huntsman Mini Analog class
    """

    def __init__(
        self, pressed_queue: asyncio.Queue[typing.Dict[int, int]], parent: str
    ):
        self.report_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self.pressed_queue: asyncio.Queue[typing.Dict[int, int]] = pressed_queue
        self.devices: typing.List[io.BufferedReader] = []
        self.context = pyudev.Context()
        self.parent = pyudev.Devices.from_path(self.context, parent)

        self.open()

        self.monitor = pyudev.Monitor.from_netlink(self.context)
        self.monitor.filter_by(subsystem="hidraw")
        self.monitor.start()

    def open(self) -> None:
        """
        Open device
        """
        self.devices = []
        loop = asyncio.get_event_loop()
        for udev in self.context.list_devices(parent=self.parent, subsystem="hidraw"):
            # pylint: disable=consider-using-with
            device_handle = open(udev.device_node, "rb")
            os.set_blocking(device_handle.fileno(), False)
            hidraw = razer_analog.hidraw.HIDRaw(device_handle)
            i = hidraw.getInfo()
            if i.vendor == 0x1532 and i.product == 0x0282:
                self.devices.append(device_handle)
                loop.add_reader(device_handle.fileno(), self.read, device_handle)
                desc = hidraw.getRawReportDescriptor()
                # I'd like to parse these using python-hid-parser but that needs to be
                # fixed in: https://github.com/usb-tools/python-hid-parser/pull/17
                # fmt: off
                if list(desc) == [5, 12, 9, 1, 161, 1, 6, 0, 255, 9, 2, 21, 0, 37, 1,
                    117, 8, 149, 90, 177, 1, 192,
                ]:
                    # put control interface first
                    self.devices[0], self.devices[-1] = self.devices[-1], self.devices[0]
                elif list(desc) == [ 5, 1, 9, 6, 161, 1, 133, 1, 5, 7, 5, 7, 25, 224, 41,
                    231, 21, 0, 37, 1, 117, 1, 149, 8, 129, 2, 25, 0, 41, 160, 21,
                    0, 37, 1, 117, 1, 149, 160, 129, 2, 117, 8, 149, 2, 129, 1, 5,
                    8, 25, 1, 41, 3, 21, 0, 37, 1, 117, 1, 149, 3, 145, 2, 149, 5,
                    145, 1, 192, 5, 12, 9, 1, 161, 1, 133, 2, 25, 0, 42, 60, 2, 21,
                    0, 38, 60, 2, 149, 1, 117, 16, 129, 0, 117, 8, 149, 21, 129, 1,
                    192, 5, 1, 9, 128, 161, 1, 133, 3, 25, 129, 41, 131, 21, 0, 37,
                    1, 117, 1, 149, 3, 129, 2, 149, 5, 129, 1, 117, 8, 149, 22, 129,
                    1, 192, 5, 1, 9, 0, 161, 1, 133, 4, 9, 3, 21, 0, 38, 255, 0, 53,
                    0, 70, 255, 0, 117, 8, 149, 23, 129, 0, 192, 5, 1, 9, 0, 161, 1,
                    133, 5, 9, 3, 21, 0, 38, 255, 0, 53, 0, 70, 255, 0, 117, 8, 149,
                    23, 129, 0, 192, 5, 1, 9, 0, 161, 1, 133, 7, 9, 3, 21, 0, 38,
                    255, 0, 53, 0, 70, 255, 0, 117, 8, 149, 23, 129, 0, 192,
                ]:
                    pass
                # fmt: on
            else:
                device_handle.close()

    def close(self) -> None:
        """
        close device
        """
        loop = asyncio.get_event_loop()
        for device in self.devices:
            loop.remove_reader(device.fileno())
            device.close()
        self.devices = []

    def read(self, device_handle: io.BufferedReader) -> None:
        """
        read from device
        """
        try:
            buf = device_handle.read(2048)
        except OSError:
            print("failed to read, exiting")
            self.close()
            sys.exit()
        while buf:
            if buf[0] == 0x04:
                pass  #  For some reason presses of Fn are reported here
            elif buf[0] == 0x07:
                self.report_queue.put_nowait(buf[1:23])
            else:
                print([buf])
            buf = buf[24:]

    @staticmethod
    def crc(buf: bytes) -> int:
        """
        Calculate Razer CRC
        """
        result = 0
        for i in range(2, 86):
            result ^= buf[i]
        return result

    def razer_command(self, data: bytes) -> bytes:
        """
        Send a razer command
        """
        if not self.devices:
            print("cannot send command, no devices attached")
            return b""

        hidraw = razer_analog.hidraw.HIDRaw(self.devices[0])
        send_report = struct.pack(
            ">BBHBB",
            0x00,  # status
            0x1F,  # transaction_id
            0x00,  # remaining_packets
            0x00,  # protocol_type
            len(data) - 2,  # size
        )
        send_report += data
        send_report += b"\x00" * (82 - len(data))
        send_report += bytes([self.crc(send_report)])
        send_report += b"\x00"
        hidraw.sendFeatureReport(send_report)
        received_report = hidraw.getFeatureReport(0, 90)

        if received_report[1] != 0x02:  # SUCCESS
            print(
                f"Failed razer_command ({received_report[1]}). received_report, send_report"
            )
            print(received_report)
            print(send_report)

        return received_report

    def set_device_mode(self, mode: int) -> None:
        """
        Set device mode
        """
        data = b"\x00\x04" + bytes((mode, 0x00))
        received_report = self.razer_command(data)[7:11]
        if received_report != data:
            print("set_device_mode mismatch", data, received_report)

    async def run(self) -> None:
        """
        Main loop
        """
        previous_pressed_keys: typing.Set[int] = set([])
        while True:
            report = await self.report_queue.get()
            pressed = {}
            for i in range(0, len(report), 2):
                if report[i] == 0 and report[i + 1] == 0:
                    break
                key, value = report[i : i + 2]
                pressed[key] = value
            # add key_up = 0 when pressed key "disappear" to simplify
            # handling of events.
            for key_up in previous_pressed_keys - set(pressed.keys()):
                pressed[key_up] = 0
            await self.pressed_queue.put(pressed)
            previous_pressed_keys = set(pressed.keys())

    async def client_connected(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """
        Call back when a client connects to the control socket
        """
        while True:
            pktlen = await reader.read(1)
            if pktlen == b"\x00":
                return
            try:
                data = await reader.readexactly(pktlen[0])
            except asyncio.IncompleteReadError:
                break
            if len(data) > 2:
                received_report = self.razer_command(data)
                if received_report:
                    writer.write(bytes((len(received_report),)) + received_report)
                    try:
                        await writer.drain()
                    except ConnectionResetError:
                        print("disconnect")
                        return
                else:
                    print("empty reply")
            else:
                print("received insufficient data")

    async def unix_server(self) -> None:
        """
        Start control socket
        """
        server = await asyncio.start_unix_server(
            self.client_connected, path=f"/var/run/razer-analog-{os.getpid()}"
        )
        async with server:
            await server.serve_forever()


async def user_input_write(
    user_input: evdev.UInput,
    user_input_queue: asyncio.Queue[typing.Tuple[int, int, int]],
) -> None:
    """
    Write user_input_queue to UInput device
    """
    while True:
        etype, code, value = await user_input_queue.get()
        user_input.write(etype, code, value)
        user_input.syn()


def released_modifier_keys(
    leftmeta_released: bool,
    leftmeta_in_repeat: bool,
    fn_released: bool,
    fn_in_repeat: bool,
) -> bool:
    """
    Modifier keys are released and previously pressed
    """
    return (
        (leftmeta_released and leftmeta_in_repeat)
        or (fn_released and leftmeta_in_repeat)
        or (fn_released and leftmeta_released and fn_in_repeat)
    )


def key_triggered(triggered: typing.Dict[int, bool], key: int, value: int) -> bool:
    """
    Check if key should trigger
    """
    if value < 96:
        triggered[key] = False
        return False
    if value > 128:
        triggered[key] = True
        return True
    return triggered.get(key, False)


def razer_key_pressed(
    pressed_keys: typing.Dict[int, int],
    triggered: typing.Dict[int, bool],
    razer_key: str,
) -> bool:
    """
    Check if key is pressed
    """
    razer_keys = {
        "FN": 59,
        "LEFTMETA": 127,
    }
    key = razer_keys[razer_key]
    value = pressed_keys.get(key, 0)
    return key_triggered(triggered, key, value)


async def virtual_keyboard(
    pressed_queue: asyncio.Queue[typing.Dict[int, int]],
    user_input_queue: asyncio.Queue[typing.Tuple[int, int, int]],
) -> None:
    """
    Handle Fn layout, left meta as Fn, FnFn as left meta and keyboard repeat
    """
    repeat: typing.Dict[int, float] = {}
    triggered: typing.Dict[int, bool] = {}
    while True:
        try:
            pressed_keys: typing.Dict[int, int] = pressed_queue.get_nowait()
        except asyncio.QueueEmpty:
            await asyncio.sleep(0.03)
            for pressed_key, repeat_until in repeat.items():
                if time.monotonic() > repeat_until:
                    await user_input_queue.put(
                        (evdev.ecodes.ecodes["EV_KEY"], pressed_key, 2)
                    )
            continue

        layout = razer_analog.layout.get_layout(
            razer_key_pressed(pressed_keys, triggered, "FN"),
            razer_key_pressed(pressed_keys, triggered, "LEFTMETA"),
        )

        if released_modifier_keys(
            leftmeta_released=not razer_key_pressed(
                pressed_keys, triggered, "LEFTMETA"
            ),
            leftmeta_in_repeat=evdev.ecodes.ecodes["KEY_LEFTMETA"] in repeat,
            fn_released=not razer_key_pressed(pressed_keys, triggered, "FN"),
            fn_in_repeat=evdev.ecodes.ecodes["KEY_FN"] in repeat,
        ):
            for code in repeat:
                await user_input_queue.put((evdev.ecodes.ecodes["EV_KEY"], code, 0))
            repeat = {}

        for pressed_key, value in pressed_keys.items():
            if pressed_key in razer_analog.layout.layout_analog:
                await user_input_queue.put(
                    (
                        evdev.ecodes.ecodes["EV_ABS"],
                        razer_analog.layout.layout_analog[pressed_key][0],
                        value,
                    )
                )

            if not pressed_key in layout:
                # ignore pressed_keys not in layout (ie. released keys)
                continue

            code = layout[pressed_key]

            if key_triggered(triggered, pressed_key, value):
                if not code in repeat:
                    repeat[code] = time.monotonic() + 0.2
                    await user_input_queue.put((evdev.ecodes.ecodes["EV_KEY"], code, 1))
            elif code != evdev.ecodes.ecodes["KEY_FN"] and code in repeat:
                # Handle untrigger of key
                # Fn key release is handled above
                del repeat[code]
                await user_input_queue.put((evdev.ecodes.ecodes["EV_KEY"], code, 0))


def main() -> None:
    """
    Setup queues and await:
     - unix_service (for control messages)
     - receive pressed keys
     - handle virtual keyboard
     - write to user input queue
    """
    loop = asyncio.get_event_loop()

    pressed_queue: asyncio.Queue[typing.Dict[int, int]] = asyncio.Queue()
    user_input_queue: asyncio.Queue[typing.Tuple[int, int, int]] = asyncio.Queue()

    user_input_keyb = evdev.UInput(
        {
            evdev.ecodes.ecodes["EV_KEY"]: list(
                razer_analog.layout.layout["plain"].values()
            )
            + list(razer_analog.layout.layout["fn"].values())
            + list(razer_analog.layout.layout["fn_fn"].values()),
            evdev.ecodes.ecodes["EV_ABS"]: list(
                razer_analog.layout.layout_analog.values()
            ),
        },
        name=f"razer-analog-keyboard-{os.getpid()}",
    )

    # Run: udevadm info -t
    # Search for: Razer_Huntsman_Mini_Analog
    # Check for "T: usb_device", use (P:):
    # /sys/devices/pci0000:00/0000:00:14.0/usb3/3-1
    parent = sys.argv[1]
    razer_huntsman_mini = HuntsmanMiniAnalog(pressed_queue, parent)

    def shutdown() -> None:
        razer_huntsman_mini.set_device_mode(0)
        razer_huntsman_mini.close()
        os.unlink(f"/var/run/razer-analog-{os.getpid()}")

    atexit.register(shutdown)

    razer_huntsman_mini.set_device_mode(3)

    tasks = asyncio.gather(
        razer_huntsman_mini.unix_server(),
        razer_huntsman_mini.run(),
        virtual_keyboard(pressed_queue, user_input_queue),
        user_input_write(user_input_keyb, user_input_queue),
    )

    loop.add_signal_handler(signal.SIGTERM, tasks.cancel)
    loop.run_until_complete(tasks)
