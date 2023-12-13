# Instructions for developer

## Introduction

This project is a hack for me to use the Razer Huntsman Mini Analog controlling a mouse cursor (as a virtual
mouse). It's not very polished but I hope it's usefull for someone.

This document describes how to setup a development environment so you can hack on this project (I accept
pull requests!)

## Steps to setup your development environment

### Step 1: Clone the repository

```bash
git clone git@github.com:meeuw/razer-analog.git
```

### Step 2: Install

* Install Poetry (if you haven't already):

  https://python-poetry.org/docs/#installation

* Install Python 3 (anything above Python 3.7 should work)

  https://www.python.org/downloads/

* Install the project

  ```bash
  cd razer-analog
  poetry install
  ```

### Step 3: Find the udev path to your keyboard

The udev path might vary between reboots or when you change USB ports.

Run the following command to list your udev device tree:

```bash
udevadm info -t
```

For me this opens in `less` and I can search using `/`.

* Search for `Razer_Huntsman_Mini_Analog`
* Check for `T: usb_device`
* Note down the value which is mentioned after `P:`

### Step 4: Start daemon

* Find where the daemon is installed

  ```bash
  poetry run which razer-analog
  ```

  This should return something like:

  ```
  /home/user/.cache/pypoetry/virtualenvs/razer-analog-i6Yo9m09-py3.12/bin/razer-analog
  ```

* Become root (or some user that has access to /dev/hidraw*)

  Run the above command as root and supply the udev path from Step 3:

  ```
  /home/user/.cache/pypoetry/virtualenvs/razer-analog-i6Yo9m09-py3.12/bin/razer-analog /sys/devices/pci0000:00/0000:00:14.0/usb3/3-1
  ```

## Development

If everything is right the daemon is running and you should be able to use the analog features of the
keyboard. If you make any changes in the Python code you should stop the daemon (using Ctrl-C) and restart
using the command in step 4

## Adding a new device

I don't own any other keyboard than the Razer Huntsman Mini so I don't have experience with other devices.
Though I can tell what must be changed for another device

* The HuntsmanMiniAnalog class has a method `open` with the hardcoded vendor id (0x1532) and product
  id (0x0282). For another device these should be updated.
* Also in this member there's a dump of the HID descriptor of the control interface, this might be different
  for other devices. The HID descriptors of connected USB devices can be shown in Linux using the `usbhid-dump`
  command.
* For other keyboards the razer report id's are probably different. These are configured in
  `razer_huntsman_mini_analog.json`. I'd recommend to add some print command to print the output of
  `buf` in `HuntsmanMiniAnalog.read()`.
