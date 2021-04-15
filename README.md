# midex-pid-changer
Temporary solution for changing the PID of a MIDEX MIDI/USB converters.


## About
This is my work-around solution for using [@sgorpi midex8 Linux driver][driver] with one of mine device which is different.
This is probably an older version that does not have firmware stored in the internal EEPROM, but receives it from the driver from the host.


## Requirements and installation

* Python 3.6 or later
* packages from ***requirements.txt*** as root (`sudo python3 -m pip install -r requirements.txt`)
* root privileges

## Usage

For normal use with the generated firmware file, run `sudo main.py -f fw.json` and connect the MIDEX device. The program should detect the newly connected device and if it really is a MIDEX it will recognize it and check its PID. If it is not the latest version (0x1001) it will try to update it.
Then [@sgorpi midex8 Linux driver][driver] should recognize it.


For other options choose `-h/--help` switch.

## Original midex driver modifications

For proper functionality it is necessary to modify original code of [midex.c] as follows:

```cpp

#define SB_MIDEX_VID 0x0a4e
#define SB_MIDEX8_PID 0x1001

/*******************************************************************
 * Type definitions
 *******************************************************************/

static struct usb_device_id id_table[] = {
	{ USB_DEVICE(SB_MIDEX_VID, SB_MIDEX8_PID) },
	{ },
};

```


[//]: # (links)

[driver]: <https://github.com/sgorpi/midex8>
[midex.c]: <https://github.com/sgorpi/midex8/blob/master/src/kernel/sound/usb/midex/midex.c>
