import sys
import os
import razer_analog.hidraw
import pyudev
import struct


def crc(buf: bytes) -> int:
    """
    Calculate Razer CRC
    """
    result = 0
    for i in range(2, 86):
        result ^= buf[i]
    return result


def razer_command(hidraw, data: bytes) -> None:
    """
    Send a razer command
    """
    send_report = struct.pack(
        ">BBHBB",
        0x00,  # status
        0xFF,  # transaction_id
        0x00,  # remaining_packets
        0x00,  # protocol_type
        len(data) - 2,  # size
    )
    send_report += data
    send_report += b"\x00" * (82 - len(data))
    send_report += bytes([crc(send_report)])
    send_report += b"\x00"

    hidraw.sendFeatureReport(send_report)
    received_report = hidraw.getFeatureReport(0, 90)

    if received_report[1] == 0x02:  # SUCCESS
        if received_report[2:] != send_report[1:]:
            print("mismatched received_report != send_report")
            print(received_report)
            print(send_report)
    else:
        print("failed to send_report")
        print(send_report)


def main():
    context = pyudev.Context()
    parent = pyudev.Devices.from_path(context, sys.argv[1])
    for udev in context.list_devices(parent=parent, subsystem="hidraw"):
        device_handle = open(udev.device_node, "rb")
        os.set_blocking(device_handle.fileno(), False)
        hidraw = razer_analog.hidraw.HIDRaw(device_handle)
        i = hidraw.getInfo()
        if i.vendor == 0x1532 and i.product == 0x0282:
            desc = hidraw.getRawReportDescriptor()
            print(desc)
            if list(desc) == [
                5,
                12,
                9,
                1,
                161,
                1,
                6,
                0,
                255,
                9,
                2,
                21,
                0,
                37,
                1,
                117,
                8,
                149,
                90,
                177,
                1,
                192,
            ]:
                print("found")
                break
        device_handle.close()
    razer_command(hidraw, bytes((3, 0x00)))
