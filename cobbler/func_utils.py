"""
Misc func functions for cobbler

Copyright 2006-2008, Red Hat, Inc
Scott Henson <shenson@redhat.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA
"""

try:
    import func.overlord.client as func
    from func.CommonErrors import Func_Client_Exception
    HAZFUNC=True
except ImportError:
    HAZFUNC=False
except IOError:
    # cant import Func because we're not root, for instance, we're likely
    # running from Apache and we've pulled this in from importing utils
    HAZFUNC=False


