#!/usr/bin/env python3
"""patch_fhid.py [path/to/f_hid.c]

Samsung's hidg_alloc() ends with a "HACK, replace content" block that overwrites
the values set through configfs (subclass, protocol, report_length, report_desc)
with a hardcoded 7-byte dummy descriptor (hid_data). That is why a gadget HID
function always reports subclass 0 / protocol 0 / maxpacket 4 / empty descriptor.

This patch skips the hack whenever configfs already provided a report_desc, so
Samsung's default only applies when nothing was configured. Idempotent.
"""
import re
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "drivers/usb/gadget/function/f_hid.c"
src = open(path).read()

if "t225_skip_hack" in src:
    print("f_hid.c already patched")
    sys.exit(0)

marker = "/* HACK, replace content, duplicate code from above */"
m = src.find(marker)
if m < 0:
    sys.exit("ERROR: HACK marker not found - f_hid.c differs from expected")
line_start = src.rfind("\n", 0, m) + 1

# the single-tab 'mutex_unlock' that ends the locked region after the hack block
end = re.compile(r"\n\tmutex_unlock\(&opts->lock\);").search(src, m)
if not end:
    sys.exit("ERROR: end of hack block not found")

# edit the later position first so the earlier index stays valid
src = src[:end.start()] + "\nt225_skip_hack:" + src[end.start():]
skip = (
    "\t/* T225: keep Samsung default only if configfs left report_desc unset */\n"
    "\tif (opts->report_desc)\n"
    "\t\tgoto t225_skip_hack;\n\n"
)
src = src[:line_start] + skip + src[line_start:]

open(path, "w").write(src)
print("patched", path)
