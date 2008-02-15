#!/usr/bin/python

"""
Copyright 2007, Red Hat, Inc

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

from server.xmlrpcclient import ServerProxy

if __name__ == "__main__":
    sp = ServerProxy("httpu:///var/lib/cobbler/sock")
    print sp.login("<system>","")




