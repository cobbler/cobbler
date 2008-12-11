#!/usr/bin/python

import os
import sys
import string
import time
import re
import md5
import base64
import xmlrpclib

class WatchedFile:
    def __init__(self, fn, alias):
        self.fn = fn
        self.alias = alias
        self.reset()

    def reset(self):
        self.where = 0
        self.last_size = 0
        self.lfrag=''
        self.re_list={}
        self.seen_line={}

    def exists(self):
        return os.access(self.fn, os.F_OK)

    def lookfor(self,pattern):
        self.re_list[pattern] = re.compile(pattern,re.MULTILINE)
        self.seen_line[pattern] = 0

    def seen(self,pattern):
        if self.seen_line.has_key(pattern):
            return self.seen_line[pattern]
        else:
            return 0

    def changed(self):
        if not self.exists():
            return 0
        size = os.stat(self.fn)[6]
        if size > self.last_size:
            self.last_size = size
            return 1
        else:
            return 0

    def uploadWrapper(self, blocksize = 262144):
        """upload a file in chunks using the uploadFile call"""
        retries = 3
        fo = file(self.fn, "r")
        totalsize = os.path.getsize(self.fn)
        ofs = 0
        md5sum = md5.new()
        while True:
            lap = time.time()
            contents = fo.read(blocksize)
            md5sum.update(contents)
            size = len(contents)
            data = base64.encodestring(contents)
            if size == 0:
                offset = -1
                digest = md5sum.hexdigest()
                sz = ofs
            else:
                offset = ofs
                digest = md5.new(contents).hexdigest()
                sz = size
            del contents
            tries = 0
            while tries <= retries:
                debug("upload_log_data('%s', '%s', %s, %s, %s, ...)\n" % (name, self.alias, sz, digest, offset))
                if session.upload_log_data(name, self.alias, sz, digest, offset, data):
                    break
                else:
                    tries = tries + 1
            if size == 0:
                break
            ofs += size
        fo.close()

    def update(self):
        if not self.exists():
            return
        if not self.changed():
            return
        try:
            self.uploadWrapper()
        except:
            raise

class MountWatcher:

    def __init__(self,mp):
        self.mountpoint = mp
        self.zero()

    def zero(self):
        self.line=''
        self.time = time.time()

    def update(self):
        fd = open('/proc/mounts')
        found = 0
        while 1:
            line = fd.readline()
            if not line:
                break
            parts = string.split(line)
            mp = parts[1]
            if mp == self.mountpoint:
                found = 1
                if line != self.line:
                    self.line = line
                    self.time = time.time()
        if not found:
            self.zero()
        fd.close()

    def stable(self):
        self.update()
        if self.line and (time.time() - self.time > 60):
            return 1
        else:
            return 0

def anamon_loop():
    alog = WatchedFile("/tmp/anaconda.log", "anaconda.log")
    alog.lookfor("step installpackages$")

    slog = WatchedFile("/tmp/syslog", "sys.log")
    llog = WatchedFile("/tmp/lvmout", "lvmout.log")
    kcfg = WatchedFile("/tmp/ks.cfg", "ks.cfg")
    scrlog = WatchedFile("/tmp/ks-script.log", "ks-script.log")
    dump = WatchedFile("/tmp/anacdump.txt", "anacdump.txt")
    mod = WatchedFile("/tmp/modprobe.conf", "modprobe.conf")
    ilog = WatchedFile("/mnt/sysimage/root/install.log", "install.log")
    ilog2 = WatchedFile("/mnt/sysimage/tmp/install.log", "tmp+install.log")
    ulog = WatchedFile("/mnt/sysimage/root/upgrade.log", "upgrade.log")
    ulog2 = WatchedFile("/mnt/sysimage/tmp/upgrade.log", "tmp+upgrade.log")
    sysimage = MountWatcher("/mnt/sysimage")
    watchlist = [alog, slog, dump, scrlog, mod, llog, kcfg]
    waitlist = [ilog, ilog2, ulog, ulog2]

    while 1:
        time.sleep(5)

        for watch in waitlist:
            if alog.seen("step installpackages$") or (sysimage.stable() and watch.exists()):
                print "Adding %s to watch list" % watch.alias
                watchlist.append(watch)
                waitlist.remove(watch)

        for wf in watchlist:
            wf.update()

# process args
name = ""
daemon = 1
debug = lambda x,**y: None

n = 0
while n < len(sys.argv):
    arg = sys.argv[n]
    if arg == '--name':
        n = n+1
        name = sys.argv[n]
    elif arg == '--debug':
        debug = lambda x,**y: sys.stderr.write(x % y)
    elif arg == '--fg':
        daemon = 0
    n = n+1

session = xmlrpclib.Server("http://dell-t5400.test.redhat.com:80/cobbler_api")

if daemon:
    if not os.fork():
        anamon_loop()
        sys._exit(1)
    sys.exit(0)
else:
    anamon_loop()

