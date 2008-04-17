"""
pyyaml legacy
Copyright (c) 2001 Steve Howell and Friends; All Rights Reserved
(see open source license information in docs/ directory)
"""

import re
import string
from timestamp import timestamp, matchTime

DATETIME_REGEX   = re.compile("^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
FLOAT_REGEX      = re.compile("^[-+]?[0-9][0-9,]*\.[0-9]*$")
SCIENTIFIC_REGEX = re.compile("^[-+]?[0-9]+(\.[0-9]*)?[eE][-+][0-9]+$")
OCTAL_REGEX      = re.compile("^[-+]?([0][0-7,]*)$")
HEX_REGEX        = re.compile("^[-+]?0x[0-9a-fA-F,]+$")
INT_REGEX        = re.compile("^[-+]?(0|[1-9][0-9,]*)$")

def convertImplicit(val):
    if val == '~':
        return None
    if val == '+':
        return 1
    if val == '-':
        return 0
    if val[0] == "'" and val[-1] == "'":
        val = val[1:-1]
        return string.replace(val, "''", "\'")
    if val[0] == '"' and val[-1] == '"':
        if re.search(r"\u", val):
            val = "u" + val
        unescapedStr = eval (val)
        return unescapedStr
    if matchTime.match(val):
        return timestamp(val)
    if INT_REGEX.match(val):
        return int(cleanseNumber(val))
    if OCTAL_REGEX.match(val):
        return int(val, 8)
    if HEX_REGEX.match(val):
        return int(val, 16)
    if FLOAT_REGEX.match(val):
        return float(cleanseNumber(val))
    if SCIENTIFIC_REGEX.match(val):
        return float(cleanseNumber(val))
    return val

def cleanseNumber(str):
    if str[0] == '+':
        str = str[1:]
    str = string.replace(str,',','')
    return str

