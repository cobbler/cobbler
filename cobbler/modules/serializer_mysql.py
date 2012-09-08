"""
Serializer code for cobbler.
Experimental:  mysql version
 
Copyright 2006-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>
James Cammarata <jimi@sngx.net>
 
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
 
import distutils.sysconfig
import os
import sys
import traceback
import exceptions
import simplejson
 
plib = distutils.sysconfig.get_python_lib()
mod_path="%s/cobbler" % plib
sys.path.insert(0, mod_path)
 
from utils import _
import utils
from cexceptions import *
import os
import ConfigParser
 
mysql_loaded = False
 
try:
    import MySQLdb
    mysql_loaded = True
except:
    # FIXME: log message
    pass
 
mysqlconn = None
 
def __connect():
    # TODO: detect connection error
    global mysqlconn
    try:
        needs_connection = False
        if not mysqlconn:
            needs_connection = True
        elif not mysqlconn.open:
            needs_connection = True
        if needs_connection:
            mysqlconn = MySQLdb.connect(host="localhost",user="cobbler",passwd="testing123",db="cobbler")
        return mysqlconn.open
    except:
        # FIXME: log error
        return False
 
def register():
    """
    The mandatory cobbler module registration hook.
    """
    # FIXME: only run this if enabled.
    if not mysql_loaded:
        return ""
    __connect()
    return "serializer"
 
def what():
    """
    Module identification function
    """
    return "serializer/mysql"
 
# Note that for all SQL inserts/deletes, we're using parameterized calls to
# execute queries (DO NOT USE "string %s" % foo!!!).
#
# This is the safe and correct way to do things (no Bobby Tables), though
# MySQLdb doesn't like it when you do that with the table name, so we still
# do that the old way. This should not be a concern, since the collection
# types are not exposed to the user and are internal only.
 
def serialize_item(obj, item):
    if not __connect():
        raise "Failed to connect"
    c = mysqlconn.cursor()
    data = simplejson.dumps(item.to_datastruct())
    res = c.execute("INSERT INTO %s (name,data) VALUES(%%s,%%s) ON DUPLICATE KEY UPDATE data=%%s" % obj.collection_type(),(item.name,data,data))
    mysqlconn.commit()
    if res:
        return True
    else:
        return False
 
def serialize_delete(obj, item):
    if not __connect():
        raise "Failed to connect"
    c = mysqlconn.cursor()
    res = c.execute("DELETE FROM %s WHERE name = %%s" % obj.collection_type(),item.name)
    mysqlconn.commit()
    if res:
        return True
    else:
        return False
 
def deserialize_item_raw(collection_type, item_name):
    if not __connect():
        raise "Failed to connect"
    c = mysqlconn.cursor()
    c.execute("SELECT data FROM %s WHERE name=%%s" % collection_type,item_name)
    data = c.fetchone()
    if data:
        data = simplejson.loads(data[0])
    return data
 
def serialize(obj):
    """
    Save an object to the database.
    """
    # TODO: error detection
    ctype = obj.collection_type()
    for x in obj:
        serialize_item(obj,x)
    return True
 
def deserialize_raw(collection_type):
    if not __connect():
        raise "Failed to connect"
    c = mysqlconn.cursor()
    c.execute("SELECT data FROM %s" % collection_type)
    data = c.fetchall()
    rdata = []
    for row in data:
        rdata.append(simplejson.loads(row[0]))
    return rdata
 
def deserialize(obj,topological=True):
    """
    Populate an existing object with the contents of datastruct.
    Object must "implement" Serializable.
    """
    datastruct = deserialize_raw(obj.collection_type())
    if topological and type(datastruct) == list:
       datastruct.sort(__depth_cmp)
    obj.from_datastruct(datastruct)
    return True
 
def __depth_cmp(item1, item2):
    d1 = item1.get("depth",1)
    d2 = item2.get("depth",1)
    return cmp(d1,d2)
 
if __name__ == "__main__":
    print deserialize_item_raw("distro","D1")
 
 