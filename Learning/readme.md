
# Programming bitstream icesugar
Just drag

OR

```$ cp /media/RAMDisk/build /media/iposthuman/iCELink```

OR

## Udev rule (icesugar)
Add a udev rule so you can run *icesprog*.
```
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="1d50", ATTRS{idProduct}=="602b", MODE="0660", GROUP="plugdev", TAG+="uaccess"
```

Then:

```$ icesprog top.bin```

# PYTHONPATH
I appended a module to PYTHONPATH as:

```PYTHONPATH =:/media/iposthuman/Nihongo/Hardware/amaranth-boards```


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