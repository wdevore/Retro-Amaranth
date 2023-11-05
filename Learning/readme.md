
# Programming bitstream icesugar
Just drag

OR

```$ cp /media/RAMDisk/build /media/iposthuman/iCELink```

OR

## Udev rule (icesugar)
Add a udev rule so you can run *icesprog*. Note: you may need to remove the ACTION and SUBSYSTEM and then reboot.
```
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="1d50", ATTRS{idProduct}=="602b", MODE="0660", GROUP="plugdev", TAG+="uaccess"
```
Then trigger the system:
```
$ sudo udevadm control --reload-rules
$ sudo udevadm trigger
```

Then:

```$ icesprog top.bin```

# PYTHONPATH
I appended a module to PYTHONPATH as:

```PYTHONPATH =:/media/iposthuman/Nihongo/Hardware/amaranth-boards```

## VSCode .env file
Create an *.env* in the same location as the *???.code-workspace* file. In it you can add paths to the **PYTHONPATH** variable, for example:
```
PYTHONPATH="/media/iposthuman/Nihongo/Hardware/amaranth-boards:/media/iposthuman/Nihongo/Hardware/Retro-Amaranth/Learning/simulations/bl0x"
```

# Errors
## soft_unicode error

```
...
File "/home/iposthuman/.local/lib/python3.10/site-packages/jinja2/defaults.py", line 3, in <module>
    from .filters import FILTERS as DEFAULT_FILTERS  # noqa: F401
  File "/home/iposthuman/.local/lib/python3.10/site-packages/jinja2/filters.py", line 13, in <module>
    from markupsafe import soft_unicode
ImportError: cannot import name 'soft_unicode' from 'markupsafe' (/home/iposthuman/.local/lib/python3.10/site-packages/markupsafe/__init__.py)
```

```$ pip show jinja2```

```$ pip show markupsafe```

The proper way would be to upgrade *jinja2* to the newest version, however, Amaranth depends on the older version so instead downgrade *markupsafe* from *2.1.3* to *2.0.1*: 
```$ pip install --upgrade markupsafe==2.0.1```

# icesugar dmesg idVendor=1d50, idProduct=602b
```log
[25511.412105] usb 1-11.1.4.2: new full-speed USB device number 20 using xhci_hcd
[25511.562939] usb 1-11.1.4.2: New USB device found, idVendor=1d50, idProduct=602b, bcdDevice= 1.00
[25511.562954] usb 1-11.1.4.2: New USB device strings: Mfr=1, Product=2, SerialNumber=3
[25511.562960] usb 1-11.1.4.2: Product: DAPLink CMSIS-DAP
[25511.562964] usb 1-11.1.4.2: Manufacturer: MuseLab
[25511.562967] usb 1-11.1.4.2: SerialNumber: 07000001004300545000000e4e4e5451a5a5a5a597969908
[25511.582307] usb-storage 1-11.1.4.2:1.0: USB Mass Storage device detected
[25511.582927] scsi host11: usb-storage 1-11.1.4.2:1.0
[25511.583728] cdc_acm 1-11.1.4.2:1.1: ttyACM1: USB ACM device
[25511.585597] hid-generic 0003:1D50:602B.000D: hiddev4,hidraw8: USB HID v1.00 Device [MuseLab DAPLink CMSIS-DAP] on usb-0000:00:14.0-11.1.4.2/input3
[25512.605215] scsi 11:0:0:0: Direct-Access     MBED     VFS              0.1  PQ: 0 ANSI: 2
[25512.605789] sd 11:0:0:0: Attached scsi generic sg4 type 0
[25512.606393] sd 11:0:0:0: [sdd] 131200 512-byte logical blocks: (67.2 MB/64.1 MiB)
[25512.606645] sd 11:0:0:0: [sdd] Write Protect is off
[25512.606650] sd 11:0:0:0: [sdd] Mode Sense: 03 00 00 00
[25512.606863] sd 11:0:0:0: [sdd] No Caching mode page found
[25512.606865] sd 11:0:0:0: [sdd] Assuming drive cache: write through
[25512.616973]  sdd:
[25512.617126] sd 11:0:0:0: [sdd] Attached SCSI removable disk
```