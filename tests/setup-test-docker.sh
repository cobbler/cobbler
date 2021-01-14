#!/bin/bash
# set SECRET_KEY for django tests
sed -i s/SECRET_KEY.*/'SECRET_KEY\ =\ "qwertyuiopasdfghl;"'/ cobbler/web/settings.py
