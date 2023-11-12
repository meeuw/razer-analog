"""
Layout for keyboard
"""
import typing
import json
import pkg_resources  # type: ignore
import evdev  # type: ignore

absinfo = evdev.device.AbsInfo(value=0, min=0, max=255, fuzz=0, flat=0, resolution=1)
layout_analog = {
    36: (evdev.ecodes.ecodes["ABS_HAT0X"], absinfo),
    37: (evdev.ecodes.ecodes["ABS_HAT0Y"], absinfo),
    38: (evdev.ecodes.ecodes["ABS_HAT1X"], absinfo),
    39: (evdev.ecodes.ecodes["ABS_HAT1Y"], absinfo),
    18: (evdev.ecodes.ecodes["ABS_HAT2X"], absinfo),
    47: (evdev.ecodes.ecodes["ABS_HAT2Y"], absinfo),
}


def load_layout() -> typing.Dict[str, typing.Dict[int, int]]:
    """
    Load layout from json file
    """
    with open(
        pkg_resources.resource_filename(
            "razer_analog", "razer_huntsman_mini_analog.json"
        ),
        encoding="utf-8",
    ) as razer_huntsman_mini_analog_file:
        result: typing.Dict[str, typing.Dict[int, int]] = {
            "plain": {},
            "fn": {},
            "fn_fn": {},
        }
        for layout_key, layout_value in json.load(
            razer_huntsman_mini_analog_file
        ).items():
            for razer_key, evdev_key in layout_value.items():
                result[layout_key][int(razer_key)] = evdev.ecodes.ecodes[
                    "KEY_" + evdev_key
                ]
    return result


layout = load_layout()


def get_layout(fn_pressed: bool, meta_pressed: bool) -> typing.Dict[int, int]:
    """
    Get layout from pressed keys
    """
    if fn_pressed and meta_pressed:
        return layout["fn_fn"]
    if fn_pressed or meta_pressed:
        return layout["fn"]
    return layout["plain"]
