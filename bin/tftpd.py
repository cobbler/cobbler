#!/usr/bin/python3
"""
SYNOPSIS
    tftpd.py [-h,--help] [-v,--verbose] [-d,--debug] [--version]
             [--port=<port>(69)]

DESCRIPTION
A python, Cobbler integrated TFTP server.  It is suitable to call via
xinetd, or as a stand-alone daemon.  If called via xinetd, it will run,
handling requests, until it has been idle for at least 30 seconds, and
will then exit.

This server queries Cobbler for information about hosts that make requests,
and will instantiate template files from the materialized hosts'
'fetchable_files' attribute.

EXIT STATUS

AUTHOR
    Douglas Kilpatrick <kilpatds@oppositelock.org>

LICENSE
    This script is in the public domain, free from copyrights or restrictions

VERSION
    0.5

TODO
    Requirement: retransmit
    Requirement: Ignore stale retrainsmits
    Security:    only return files that are o+r
    Security:    support hosts.allow/deny
    Security:    Make absolute path support optional, and default off
    Feature:     support blksize2 (blksize, limited to powers of 2)
    Feature:     support utimeout (timeout, in ms)

"""


from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import range
from builtins import object
VERSION = 0.5

import sys
import os
import stat
import errno
import time
import optparse
import re
import socket
import pwd
import traceback
import logging
import logging.handlers
import xmlrpc.client

from collections import deque
from fnmatch import fnmatch
from cobbler.utils import local_get_cobbler_api_url
from cobbler import settings

import tornado.ioloop as ioloop
import cobbler.templar
import Cheetah      # need exception types

from struct import pack, unpack
from subprocess import Popen, PIPE, STDOUT

# Data/Defines
TFTP_OPCODE_RRQ = 1
TFTP_OPCODE_DATA = 3
TFTP_OPCODE_ACK = 4
TFTP_OPCODE_ERROR = 5
TFTP_OPCODE_OACK = 6

COBBLER_HANDLE = xmlrpc.client.Server(local_get_cobbler_api_url())

OPTIONS = {
    "port": "69",
    "timeout": 10,
    "min_timeout": 1,
    "max_timeout": 255,
    "blksize": 512,         # that's the default, required
    "max_blksize": 1428,    # MTU - overhead
    "min_blksize": 512,     # the default is small enough already
    "retries": 4,
    "verbose": False,
    "debug": False,
    "idle": 0,              # how long to stick around: 0: unlimited
    "idle_timer": None,
    "cache": True,          # 'cache-time' = 300
    "cache-time": 5 * 300,
    "neg-cache-time": 10,
    "active": 0,
    "prefix": settings.Settings.tftpboot_location,
    "logger": "stream",
    "file_cmd": "/usr/bin/file",
    "user": "nobody",
    # the well known socket.  needs to be global for timeout
    # Using the options hash as a hackaround for python's
    # "create a new object at local scope by default" design.
    "sock": None
}

ERRORS = [
    'Not defined, see error message (if any)',  # 0
    'File not found',                           # 1
    'Access violation',                         # 2
    'Disk full or allocation exceeded',         # 3
    'Illegal TFTP operation',                   # 4
    'Unknown transfer ID',                      # 5
    'File already exists',                      # 6
    'No such user',                             # 7
    'Option negotiation'                        # 8
]

REQUESTS = None


class RenderedFile(object):
    """
    A class to manage rendered files, without changing the logic
    of the rest of the TFTP server.  It replaces the file object
    via duck typing, and feeds out sections of the saved string
    as required
    """

    def __init__(self, data=""):
        """
        Provide the string to be served out as an argument to the
        constructor.  The data object needs to support slices.
        """
        self.data = data
        self.offset = 0

    def seek(self, bytes):
        """
        Only the two-argument version of seek (SEEK_SET) is currently
        supported
        """
        self.offset = bytes

    def read(self, size):
        """Returns <size> bytes relative to the current offset."""
        end = self.offset + size
        return self.data[self.offset:end]

    def fileno(self):
        return 0


class Packet(object):
    """
    Represents a packet received (or sent?) from a tftp client.
    Is a base class that is intended to be overridden.
    The main use cases are "I got a packet, parse it", but
    I'm also keeping the "how to write a packet of type X"
    in the same class to keep the relevant code snippets close
    to each other.

    Any strings that control behavior (mode, rfc2347 options) are
    case-INsensitive.  Filename is allowed to be case sensitive
    """
    def __init__(self, data, local_sock, remote_addr):
        self.data = data
        self.local_sock = local_sock
        self.remote_addr = remote_addr
        self.opcode, = unpack("!H", data[0:2])

    def marshall(self):
        raise NotImplementedError("%s: Write marshall method" % repr(self))

    def is_error(self):
        return False


class RRQPacket(Packet):
    """
    The RRQ Packet.  We only receive those, so this object only
    supports the receive use case.

              2 bytes   string   byte   String   byte
              ---------------------------------------
       DATA  | 01    |   name |   \0   | mode   | \0 |
              ---------------------------------------
              string          string
              ----------------------------
     rfc2347 | name |   \0   | value | \0 | [*]
              ----------------------------
    """
    def __init__(self, data, local_sock, remote_addr):
        Packet.__init__(self, data, local_sock, remote_addr)

        # opcode already extracted, and unpack is awkward for this
        # so pulling out strings by hand
        (f, mode, rfc2347str) = data[2:].split('\0', 2)

        logging.debug("RRQ for file %s(%s) from %s" % (f, mode, remote_addr))
        # Ug.  Can't come up with a simplier way of doing this
        if rfc2347str:
            # the "-1" is to trim off the trailing \0
            self.req_options = deque(rfc2347str[:-1].split('\0'))
            logging.debug("client %s requested options: %s" % (
                str(remote_addr), str(rfc2347str.replace('\0', ','))))
        else:
            self.req_options = deque()

        self.filename = f
        self.mode = mode

    def get_request(self, templar):
        return Request(self.filename, self.remote_addr, templar)


class DATAPacket(Packet):
    """
    The DATA packet.  We only send these, so this object only
    supports the send use case.

              2 bytes    2 bytes       n bytes
             -----------------------------------
       DATA  | 03    |   Block #  |    Data    |
             -----------------------------------
    """
    def __init__(self, data, blk_num):
        self.data = data
        self.blk_num = blk_num

    def marshall(self):
        return pack("!HH %ds" % (len(self.data)), TFTP_OPCODE_DATA, self.blk_num & 0xFFFF, str(self.data))


class ACKPacket(Packet):
    """
    The ACK packet.  We only receive these.

                2 bytes    2 bytes
               ----------------------
         ACK   | 04    |   Block #  |
               ----------------------
    """

    def __init__(self, data, local_sock, remote_addr):
        Packet.__init__(self, data, local_sock, remote_addr)
        block_number, = unpack("!H", data[2:4])
        logging.log(9, "ACK for packet %d from %s" % (block_number, remote_addr))
        self.block_number = block_number

    def marshall(self):
        raise NotImplementedError("We don't send these, we read them")


class ERRORPacket(Packet):
    """The error packet.  We could send or receive these.
       But we really only handle sending them.
               2 bytes  2 bytes        string    1 byte
              ------------------------------------------
        ERROR | 05    |  ErrorCode |   ErrMsg   |   0  |
              ------------------------------------------
    """
    def __init__(self, data, local_sock, remote_addr):
        Packet.__init__(self, data, local_sock, remote_addr)
        self.error_code, = unpack("!h", data[2:4])
        self.error_str = data[4:-1]
        logging.debug("ERROR %d: %s from %s" % (self.error_code, self.error_str, remote_addr))

# FIXME: disabled as per pyflakes, not really sure about this one..
#    def __init__(self, error_code, error_str):
#        self.error_code = error_code
#        self.error_str  = error_str

    def is_error(self):
        return True

    def marshall(self):
        return pack("!HH %dsB" % (len(self.error_str)),
                    TFTP_OPCODE_ERROR, self.error_code, self.error_str, 0)


class OACKPacket(Packet):
    """
    The Option Acknowledge (rfc2347) packet.  We only send these.
    We make an effort to retain name case and order, to aid clients
    that depend on either.

               2 bytes   string   1 byte  string  1 byte
             ----------|--------------------------------
        OACK | 06     || name    |    0  | value |  0  | [*]
             ----------|--------------------------------
    """
    def __init__(self, rfc2347):
        self.opcode = TFTP_OPCODE_OACK
        self.options = rfc2347

    def marshall(self):
        optstr = "\0".join([str(x) for x in self.options])

        return pack("!H %ds c" % (len(optstr)), self.opcode, optstr, '\0')


class XMLRPCSystem(object):
    """
    Use XMLRPC to look up system attributes.  This is the recommended
    method.

    The cache is controlled by the "cache" option and the "cache-time"
    option
    """
    cache = {}

    def __init__(self, ip_address=None, mac_address=None):
        name = None
        resolve = True

        # Try the cache.
        if ip_address in XMLRPCSystem.cache:
            cache_ent = XMLRPCSystem.cache[ip_address]
            now = time.time()
            cache_time = float(OPTIONS["cache-time"])
            neg_cache_time = float(OPTIONS["neg-cache-time"])

            if cache_ent["time"] + cache_time > now:
                name = cache_ent["name"]

                if name is not None:
                    logging.debug("Using cache name for system %s,%s" % (cache_ent["name"], ip_address))
                    resolve = False
                elif (name is None and mac_address is None and cache_ent["time"] + neg_cache_time > now):
                    age = (cache_ent["time"] + neg_cache_time) - now
                    logging.debug("Using neg-cache for system %s:%f" % (ip_address, age))
                    resolve = False
                else:
                    age = (cache_ent["time"] + neg_cache_time) - now
                    logging.debug("ignoring cache for %s:%d" % (ip_address, age))

                # Don't bother trying to find it.. until the neg-cache-time
                # expires anyway
            else:
                del XMLRPCSystem.cache[ip_address]

        # Not in the cache, try to find it.
        if resolve:
            query = {}
            if mac_address is not None:
                query["mac_address"] = mac_address.replace("-", ":").upper()
            elif ip_address is not None:
                query["ip_address"] = ip_address

            try:
                logging.debug("Searching for system %s" % repr(query))
                systems = COBBLER_HANDLE.find_system(query)
                if len(systems) > 1:
                    raise RuntimeError("Args mapped to multiple systems")
                elif len(systems) == 0:
                    raise RuntimeError("%s,%s not found in Cobbler" % (ip_address, mac_address))
                name = systems[0]

            except RuntimeError as e:
                logging.info(str(e))
                name = None
            except:
                (etype, eval,) = sys.exc_info()[:2]
                logging.warn("Exception retrieving rendered system: %s (%s):%s" %
                             (name, eval, traceback.format_exc()))
                name = None

        if name is not None:
            logging.debug("Materializing system %s" % name)
            try:
                self.system = COBBLER_HANDLE.get_system_as_rendered(name)
                self.attrs = self.system
                self.name = self.attrs["name"]
            except:
                (etype, eval,) = sys.exc_info()[:2]
                logging.warn("Exception Materializing system %s (%s):%s" %
                             (name, eval, traceback.format_exc()))
                if ip_address in XMLRPCSystem.cache:
                    del XMLRPCSystem.cache[ip_address]
                self.system = None
                self.attrs = dict()
                self.name = str(ip_address)
        else:
            self.system = None
            self.attrs = dict()
            self.name = str(ip_address)

        # fill the cache, negative entries too
        if OPTIONS["cache"] and resolve:
            logging.debug("Putting %s,%s into cache" % (name, ip_address))
            XMLRPCSystem.cache[ip_address] = {
                "name": name,
                "time": time.time(),
            }


class Request(object):
    """
    Handles the "business logic" of the TFTP server.  One instance
    is spawned per client request (RRQ packet received on well-known port)
    and it is responsible for keeping track of where the file transfer
    is...
    """
    def __init__(self, rrq_packet, local_sock, templar):
        # Trim leading /s, since that's kinda implicit
        self.filename = rrq_packet.filename.lstrip('/')  # assumed
        self.type = "chroot"
        self.remote_addr = rrq_packet.remote_addr
        self.req_options = rrq_packet.req_options
        self.options = dict()
        self.offset = 0
        self.local_sock = local_sock
        self.state = TFTP_OPCODE_RRQ
        self.expand = False
        self.templar = templar

        # Sanitize input more
        # Strip out \s
        self.filename = self.filename.replace('\\', '')
        # Look for elements starting with ".", and blow up.
        try:
            if len(self.filename) == 0:
                raise RuntimeError("Empty Path: ")
            for elm in self.filename.split("/"):
                if elm[0] == ".":
                    raise RuntimeError("Path includes '.': ")
        except RuntimeError as e:
            logging.warn(str(e) + rrq_packet.filename)
            self.error_code = 2
            self.error_str = "Invalid file name"
            self.state = TFTP_OPCODE_ERROR
            self.filename = None

        OPTIONS["active"] += 1
        self.system = XMLRPCSystem(self.remote_addr[0])

    def _remap_strip_ip(self, filename):
        # remove per-host IP or Mac prefixes, so that earlier pxelinux requests
        # can be templated.  We are already doing per-host stuff, so we don't
        # need the IP addresses/mac addresses tacked on
        # /<filename>/UUID (503a463c-537a-858b-af2a-519686f53c58)
        # /<filename>/MAC (01-00-50-56-8b-33-88)
        # /<filename>/IP (C000025B)
        trimmed = filename
        if self.system.system is None:
            # If the file name has a mac address, strip that, use it to
            # look up the system, and recurse.
            m = re.compile("01((-[0-9a-f]{2}){6})$").search(filename)
            if m:
                # Found a mac address.  try and look up a system
                self.system = XMLRPCSystem(self.system.name, m.group(1)[1:])
                if self.system.system is not None:
                    logging.info("Looked up host late: '%s'" % self.system.name)
                    return self._remap_strip_ip(filename)

            # We can still trim off an ip address... system.name is the
            # incoming ip
            suffix = "/%08X" % unpack('!L', socket.inet_aton(self.system.name))[0]
            if suffix and trimmed[len(trimmed) - len(suffix):] == suffix:
                trimmed = trimmed.replace(suffix, "")
                logging.debug('_remap_strip_ip: converted %s to %s' % (filename, trimmed))
                return trimmed
        else:
            # looking over all keys, because I have to search for keys I want
            for (k, v) in list(self.system.system.items()):
                suffix = False
                # if I find a mac_address key or ip_address key, then see if
                # that matches the file I'm looking at
                if k.find("mac_address") >= 0 and v != '':
                    # the "01" is the ARP type of the interface.  01 is
                    # ethernet.  This won't work for token ring, for example
                    suffix = "/01-" + v.replace(":", "-").lower()
                elif k.find("ip_address") >= 0 and v != '':
                    # IPv4 hardcoded here.
                    suffix = "/%08X" % unpack('!L', socket.inet_aton(v))[0]

                if suffix and trimmed[len(trimmed) - len(suffix):] == suffix:
                    trimmed = trimmed.replace(suffix, "")
                    logging.debug('_remap_strip_ip: converted %s to %s' % (filename, trimmed))
                    return trimmed
        return filename

    def _remap_via_profiles(self, filename):
        pattern = re.compile("images/([^/]*)/(.*)")
        m = pattern.match(filename)
        if m:
            logging.debug("client requesting distro?")
            p = COBBLER_HANDLE.get_distro_as_rendered(m.group(1))
            if p:
                logging.debug("%s matched distro %s" % (filename, p["name"]))
                if m.group(2) == os.path.basename(p["kernel"]):
                    return p["kernel"], "template"
                elif m.group(2) == os.path.basename(p["initrd"]):
                    return p["initrd"], "template"
                logging.debug("but unknown file requested.")
            else:
                logging.debug("Couldn't load profile %s" % m.group(1))
        return filename, "chroot"

    def _remap_name_via_fetchable(self, filename):
        fetchable_files = self.system.attrs["fetchable_files"].strip()
        if not fetchable_files:
            return filename, None

        # We support two types of matches in fetchable_files
        # * Direct match ("/foo=/bar")
        # * Globs on directories ("/foo/*=/bar")
        #   A glob is realliy just a directory remap
        glob_pattern = re.compile("(/)?[*]$")

        # Look for the file in the fetchable_files hash
        # XXX: Template name
        for (k, v) in [x.split("=") for x in fetchable_files.split(" ")]:
            k = k.lstrip('/')  # Allow some slop w/ starting /s
            # Full Path: "/foo=/bar"
            result = None

            if k == filename:
                logging.debug('_remap_name: %s => %s' % (k, v))
                result = v
            # Glob Path: "/foo/*=/bar/"
            else:
                match = glob_pattern.search(k)
                if match and fnmatch("/" + filename, "/" + k):
                    logging.debug('_remap_name (glob): %s => %s' % (k, v))
                    # Erase the trailing '/?[*]' in key
                    # Replace the matching leading portion in filename
                    # with the value
                    # Expand the result
                    if match.group(1):
                        lead_dir = glob_pattern.sub(match.group(1), k)
                    else:
                        lead_dir = glob_pattern.sub("", k)
                    result = filename.replace(lead_dir, v, 1)

            # Render the target, to expand things like "$kernel"
            if result is not None:
                try:
                    return self.templar.render(
                        result, self.system.attrs, None).strip(), "template"
                except Cheetah.Parser.ParseError as e:
                    logging.warn('Unable to expand name: %s(%s): %s' % (filename, result, e))

        return filename, None

    def _remap_name_via_boot_files(self, filename):

        boot_files = self.system.attrs["boot_files"].strip()
        if not boot_files:
            logging.debug('_remap_name: no boot_files for %s/%s' % (self.system, filename))
            return filename, None

        filename = filename.lstrip('/')  # assumed

        # Override "img_path", as that's the only variable used by
        # the VMWare boot_files support, and they use a slightly different
        # definition: one that's relative to tftpboot
        attrs = self.system.attrs.copy()
        attrs["img_path"] = os.path.join("images", attrs["distro_name"])

        # Look for the file in the boot_files hash
        for (k, v) in [x.split("=") for x in boot_files.split(" ")]:
            k = k.lstrip('/')  # Allow some slop w/ starting /s

            # Render the key, to expand things like "$img_path"
            try:
                expanded_k = self.templar.render(k, attrs, None)
            except Cheetah.Parser.ParseError as e:
                logging.warn('Unable to expand name: %s(%s): %s' % (filename, k, e))
                continue

            if expanded_k == filename:
                # Render the target, to expand things like "$kernel"
                logging.debug('_remap_name: %s => %s' % (expanded_k, v))

                try:
                    return self.templar.render(v, attrs, None).strip(), "template"
                except Cheetah.Parser.ParseError as e:
                    logging.warn('Unable to expand name: %s(%s): %s' % (filename, v, e))

        return filename, None

    def _remap_name(self, filename):
        filename = filename.lstrip('/')  # assumed
        # If possible, ignore pxelinux.0 added things we already know
        trimmed = self._remap_strip_ip(filename)

        if self.system.system is None:
            # Look for image match.  All we can do
            return self._remap_via_profiles(trimmed)

        # Specific hacks to handle the PXE/initrd case without any configuration
        if trimmed in self.system.attrs:
            if trimmed in ["pxelinux.cfg"]:
                return trimmed, "hash_value"
            elif trimmed in ["initrd"]:
                return self.system.attrs[trimmed], "template"

        # for the two tests below, I want to ignore "pytftp.*" in the string,
        # which allows for some minimal control over extensions, which matters
        # to pxelinux.0
        noext = re.sub("pytftpd.*", "", filename)
        if noext in self.system.attrs and noext in ["kernel"]:
            return self.system.attrs[noext], "template"

        (new_name, find_type) = self._remap_name_via_fetchable(trimmed)
        if find_type is not None:
            return new_name, find_type

        (new_name, find_type) = self._remap_name_via_boot_files(trimmed)
        if find_type is not None:
            return new_name, find_type

        # last try: try profiles
        return self._remap_via_profiles(trimmed)

    def _render_template(self):
        try:
            return RenderedFile(self.templar.render(open(self.filename, "r"),
                                self.system.attrs, None))
        except Cheetah.Parser.ParseError as e:
            logging.warn('Unable to expand template: %s: %s' % (self.filename, e))
            return None
        except IOError as e:
            logging.warn('Unable to expand template: %s: %s' % (self.filename, e))
            return None

    def _setup_xfer(self):
        """Open the file to be loaded, or materalize the template.
           This method can set the state to be an ERROR state, so
           avoid setting state after calling this method.
        """
        logging.info('host %s requesting %s' % (self.system.name, self.filename))

        self.filename, self.type = self._remap_name(self.filename)
        logging.debug('host %s getting %s: %s' %
                      (self.system.name, self.filename, self.type))
        if self.type == "template":
            # TODO: Add file magic here
            output = Popen([OPTIONS["file_cmd"], self.filename],
                           stdout=PIPE, stderr=STDOUT,
                           close_fds=True).communicate()[0]
            if output.find(" text") >= 0:
                self.file = self._render_template()
                if self.file:
                    self.block_count = 0
                    self.file_size = len(self.file.data)
                    return
                else:
                    logging.debug('Template failed to render.')
            else:
                logging.debug('Not rendering binary file %s (%s).' % (self.filename, output))
        elif self.type == "hash_value":
            self.file = RenderedFile(self.system.attrs[self.filename])
            self.block_count = 0
            self.file_size = len(self.file.data)
            return
        else:
            logging.debug('Relative path')

        # Oh well.  Look for the actual given file.
        # XXX: add per-host IP or Mac prefixes?
        #       add: for pxeboot, or other non pxelinux
        try:
            logging.debug('starting xfer of %s to %s' %
                          (self.filename, self.remote_addr))
            # Templates are specified by an absolute path
            if self.type == "template":
                self.file = open(self.filename, 'rb', 0)
            else:
                # TODO! restrict.  Chroot?
                # We are sanitizing in the input, but a second line of defense
                # wouldn't be a bad idea
                self.file = open(OPTIONS["prefix"] + "/" + self.filename, 'rb', 0)
            self.block_count = 0
            self.file_size = os.fstat(self.file.fileno()).st_size
        except IOError:
            logging.debug('%s requested %s: file not found.' %
                          (self.remote_addr, self.filename))
            self.state = TFTP_OPCODE_ERROR
            self.error_code = 1
            self.error_str = "No such file"
        return

    def finish(self):
        io_loop = ioloop.IOLoop.instance()
        logging.debug("finishing req from %s for %s" %
                      (self.filename, self.remote_addr))

        self.state = 0
        try:
            io_loop.remove_handler(self.local_sock.fileno())
            logging.debug("closing fd %d" % self.local_sock.fileno())
            self.local_sock.close()
        except:
            logging.debug("closed FD twice.  Ignoring")

        if self.timeout:
            io_loop.remove_timeout(self.timeout)
            self.timeout = None

        OPTIONS["active"] -= 1
        if (OPTIONS["idle"] > 0 and OPTIONS["active"] == 0 and OPTIONS["idle_timer"] is None):
            io_loop.stop()

    def handle_timeout(self):
        # We timed out.  We're done... (I hope)
        logging.info('Timeout.  Transfer of %s done' % self.filename)
        self.timeout = None
        self.finish()

    def handle_input(self, packet):
        """The client sent us a new packet.  Respond to it.
           RRQ is handled in the constructor sequence, basically.
           This should handle everything else"""
        # We got input, so didn't time out.  Refresh the timeout
        io_loop = ioloop.IOLoop.instance()
        io_loop.remove_timeout(self.timeout)
        self.timeout = io_loop.add_timeout(time.time() + self.options["timeout"], lambda: self.handle_timeout())

        if packet.opcode == TFTP_OPCODE_ACK:
            if self.state == TFTP_OPCODE_DATA:
                # Incremement offset.  They got the last bit
                # the FFFF are to permit wrap.  It's OK for the block
                # number to wrap, since it's one client (and not unicast),
                # so the client can figure that out.
                if ((packet.block_number & 0xFFFF) == ((self.block_count + 1) & 0xFFFF)):
                    # Only update if they actually ack the packet we
                    # sent, but we'll still resend the last packet either way
                    self.block_count += 1

                self.state = TFTP_OPCODE_ACK
            elif self.state == TFTP_OPCODE_OACK:
                # Ok, start feeding data
                self.state = TFTP_OPCODE_ACK

        elif packet.opcode == TFTP_OPCODE_ERROR:
            logging.warn("Error from clients %s: %d:%s" %
                         (self.remote_addr, packet.error_code,
                          packet.error_str))
            self.state = 0
        else:
            logging.warn("Unknown opcode from clients %s: %ds" %
                         (self.remote_addr, packet.opcode))
            self.state = 0

    def reply(self):
        """Given the current state, returns the next packet we should send
        to the client"""
        # Python doesn't have a switch statement (I presume on the theory
        # that needing one means you didn't set your classes up right)
        # so ... have a set of if/elif statements.

        # Fast path: it's an ACK.  Feed more data
        if self.state == TFTP_OPCODE_ACK:
            offset = self.block_count * self.options["blksize"]

            if self.file_size < offset:
                # We're done.
                logging.info('Transfer of %s to %s done' % (self.filename, self.remote_addr))
                return None

            self.file.seek(self.block_count * self.options["blksize"])
            data = self.file.read(self.options["blksize"])

            self.state = TFTP_OPCODE_DATA
            # Block Count starts at 1, so offset
            logging.log(9, "DATA to %s/%d, block_count %d/%d, size %d(%d/%d)" % (
                self.remote_addr[0], self.remote_addr[1],
                self.block_count + 1, (self.block_count + 1) & 0xFFFF,
                len(data), offset + len(data), self.file_size))
            return DATAPacket(data, self.block_count + 1)

        if self.state == 0:
            return None

        if self.state == TFTP_OPCODE_ERROR:
            # Don't bother waiting.. this was the first request
            # a "resend" would go to the well known port
            return ERRORPacket(self.error_code, self.error_str)

        if self.state == TFTP_OPCODE_RRQ and self.req_options:
            # They asked for various rfc2347 options.  Figure out
            # what we'll allow, and send an OACK.
            self.state = TFTP_OPCODE_OACK
            # Most clients will ask for tsize, which is the size of the
            # file we'll be giving them.   Let's look that up.
            self._setup_xfer()
            # Check for an error loading the file
            if self.state == TFTP_OPCODE_ERROR:
                # Don't bother waiting.. this was the first request
                # a "resend" would go to the well known port
                return ERRORPacket(self.error_code, self.error_str)

            # make sure we have defaults
            self.options = dict(blksize=OPTIONS["blksize"], timeout=OPTIONS["timeout"])

            accepted_opts = []
            # Sorry for the excessive complexity here.
            # I'm trying to maintain client's case and order, to protect
            # against braindamaged clients.  Given clients are frequently
            # written in assembly, they can be excused some braindamage
            logging.debug("Requested options: %s" % (repr(self.req_options)))
            for i in range(0, len(self.req_options), 2):
                key = self.req_options[i]
                value = self.req_options[i + 1]

                logging.debug("looking at key %s" % (key))
                if key.lower() == "tsize":
                    accepted_opts.append(key)
                    accepted_opts.append(self.file_size)
                elif ("min_" + key).lower() in OPTIONS:
                    value = int(value)  # string
                    # if it's an option we know about/can bound
                    upper_bound = OPTIONS[("max_" + key).lower()]
                    lower_bound = OPTIONS[("min_" + key).lower()]

                    logging.debug("%s: req: %d (%d - %d)" % (key, value, lower_bound, upper_bound))
                    if value < lower_bound:
                        value = lower_bound
                    if value > upper_bound:
                        value = upper_bound

                    self.options[key.lower()] = value
                    accepted_opts.append(key)
                    accepted_opts.append(str(value))
                else:
                    # ignore it, do not include in the OACK
                    logging.info("Unknown option requested %s" % (key))

            logging.debug("Using Options: %s" % (repr(self.options)))

            return OACKPacket(accepted_opts)

        if self.state == TFTP_OPCODE_RRQ:
            # No options.  Fill in the defaults
            # and then recurse, pretending we just got the ACK to our OACK
            self.options = dict(blksize=OPTIONS["blksize"], timeout=OPTIONS["timeout"])

            logging.debug("Using Options: %s" % (repr(self.options)))

            self.state = TFTP_OPCODE_ACK

            self._setup_xfer()
            if self.state == TFTP_OPCODE_ERROR:
                return ERRORPacket(self.error_code, self.error_str)

            return self.reply()

        raise NotImplementedError("Unknown state %d" % (self.state))


REQ_NAME = 0
REQ_CLASS = 1
REQUESTS = [
    ["INVALID", None],     # 0
    ["RRQ", RRQPacket],    # 1
    ["WRQ", None],         # 2
    ["DATA", None],        # 3
    ["ACK", ACKPacket],    # 4
    ["ERROR", None],       # 5
    ["OACK", OACKPacket]   # 6
]


def read_packet(data, local_sock, remote_addr):
    """Object factory.  Reads the first tiny bit of the packet to get the
       opcode, and returns a Packet object of the relevant type

       Returns None on failure
    """
    opcode, = unpack("!H", data[0:2])
    if opcode < 1 or opcode > 6:
        logging.warn("Unknown request id %d from %s" % (opcode, remote_addr))
        local_sock.sendto(ERRORPacket(0, "Unknown request").marshall(), remote_addr)
        return None

    if REQUESTS[opcode][REQ_CLASS] is None:
        if opcode != TFTP_OPCODE_ERROR:
            logging.warn("Unsupported request %d(%s) from %s" % (opcode, REQUESTS[opcode][REQ_NAME], remote_addr))
        local_sock.sendto(
            ERRORPacket(2, "Unsupported request").marshall(), remote_addr)
        return None

    try:
        return (REQUESTS[opcode][REQ_CLASS])(data, local_sock, remote_addr)
    except:
        return None


def partial(func, *args, **keywords):
    """
    Method factory.  Returns a semi-anonymous method that provides
    certain arguments to another method.
    Usually could be replaced by a lambda expression

    Example:
         def add(i,j):
             return i+j
         fn = partial(add,1) # always pass 1 as the first arg to add
         fn(2) # returns 1+2
    """
    def newfunc(*fargs, **fkeywords):
        newkeywords = keywords.copy()
        newkeywords.update(fkeywords)
        return func(*(args + fargs), **newkeywords)
    newfunc.func = func
    newfunc.args = args
    newfunc.keywords = keywords
    return newfunc


def handle_request(request, fd, events):
    """Used as the IO handler for subsequent requests.  Followup
       packets for a given request are sent to a different port, because
       UDP doesn't have it's own connection concept.  Also packets
       can be larger after option negotiation, so the amount to read
       can vary.

       This method handles packets sent to the transient ports,
       and calls the Request.handle_input method of the request associated
       with the port.
    """
    try:
        while request.state != 0:  # 0 is the "done" state
            try:
                data, address = request.local_sock.recvfrom(request.options["blksize"])
            except socket.error as e:
                if e[0] in (errno.EWOULDBLOCK, errno.EAGAIN):
                    return
                else:
                    raise

            if address == request.remote_addr:
                packet = read_packet(data, request.local_sock, address)
                if (packet is None):
                    request.finish()
                    continue

                request.handle_input(packet)
                reply = request.reply()

                if reply:
                    request.local_sock.sendto(reply.marshall(), address)

                if not reply or reply is ERRORPacket:
                    request.finish()
            else:
                raise NotImplementedError("Input from unexpected source")
    finally:
        # Reset the timer
        if OPTIONS["idle"] > 0:
            io_loop = ioloop.IOLoop.instance()
            try:
                io_loop.remove_timeout(OPTIONS["idle_timer"])
            except:
                pass
            OPTIONS["idle_timer"] = io_loop.add_timeout(
                time.time() + OPTIONS["idle"], lambda: idle_out())


def idle_out():
    logging.info("Idling out")
    io_loop = ioloop.IOLoop.instance()
    io_loop.remove_handler(OPTIONS["sock"].fileno())
    OPTIONS["sock"].close()
    if OPTIONS["active"] == 0:
        OPTIONS["idle_timer"] = None
        io_loop.stop()


# called from ioloop.py:245
def new_req(sock, templar, fd, events):
    """The IO handler for the well-known port.  Handles the RRQ
       packet of a known size (512), and sets up the transient port
       for future messages for the same request.
    """
    io_loop = ioloop.IOLoop.instance()
    if OPTIONS["idle"] > 0:
        try:
            io_loop.remove_timeout(OPTIONS["idle_timer"])
        except:
            pass

    while True:
        try:
            data, address = sock.recvfrom(OPTIONS["blksize"])
        except socket.error as e:
            if e[0] not in (errno.EWOULDBLOCK, errno.EAGAIN):
                raise
            break

        packet = read_packet(data, sock, address)
        # this is the new_request handler.  (packet had better be an RRQ
        # request)
        if packet is None or packet.opcode != TFTP_OPCODE_RRQ:
            sock.sendto(
                ERRORPacket(2, "Unsupported initial request").marshall(), address)
            break

        # Create the new transient port for this request
        new_address = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
        new_address.bind(("", 0))  # random port: XXX control?
        logging.debug("Bound to transient socket %d" % new_address.getsockname()[1])
        new_address.setblocking(0)
        packet.local_sock = new_address

        # Create the request object to handle this request, and bind it
        # to IO from the transient port
        request = Request(packet, new_address, templar)
        io_loop.add_handler(
            new_address.fileno(),
            partial(handle_request, request),
            io_loop.READ)
        request.timeout = io_loop.add_timeout(time.time() + OPTIONS["timeout"], lambda: request.handle_timeout())

        # Ask the request what to do now..
        reply = request.reply()
        if reply:
            new_address.sendto(reply.marshall(), address)

        if not reply or reply.is_error():
            request.finish()

    # After the while loop.  Re-add the idle timer
    if OPTIONS["idle"] > 0:
        OPTIONS["idle_timer"] = io_loop.add_timeout(time.time() + OPTIONS["idle"], lambda: idle_out())


def main():
    # If we're called from xinetd, set idle to non-zero
    mode = os.fstat(sys.stdin.fileno()).st_mode
    if stat.S_ISSOCK(mode):
        OPTIONS["idle"] = 30
        OPTIONS["logger"] = "syslog"

    # setup option parsing
    opt_help = dict(
        port=dict(type="int", help="The port to bind to for new requests"),
        idle=dict(type="int", help="How long to wait for input"),
        timeout=dict(type="int", help="How long to wait for a given request"),
        max_blksize=dict(type="int", help="The maximum block size to permit"),
        prefix=dict(type="string", help="Where files are stored by default [" + OPTIONS["prefix"] + "]"),
        logger=dict(type="string", help="How to log"),
        file_cmd=dict(type="string", help="The location of the 'file' command"),
        user=dict(type="string", help="The user to run as [nobody]"),
    )

    parser = optparse.OptionParser(
        formatter=optparse.IndentedHelpFormatter(),
        usage=globals()['__doc__'],
        version=VERSION)
    parser.add_option('-v', '--verbose', action='store_true', default=False,
                      help="Increase output verbosity")
    parser.add_option('-d', '--debug', action='store_true', default=False,
                      help="Debug (vastly increases output verbosity)")
    parser.add_option('-c', '--cache', action='store_true', default=True,
                      help="Use a cache to help find hosts w/o IP address")
    parser.add_option('--cache-time', action='store', type="int", default=5 * 60,
                      help="How long an ip->name mapping is valid")
    parser.add_option('--neg-cache-time', action='store', type="int", default=10,
                      help="How long an ip->name mapping is valid")

    opts = list(opt_help.keys())
    opts.sort()
    for k in opts:
        v = opt_help[k]
        parser.add_option("--" + k, default=OPTIONS[k], type=v["type"], help=v["help"])
    parser.add_option('-B', dest="max_blksize", type="int", default=1428,
                      help="alias for --max-blksize, for in.tftpd compatibility")

    # Actually read the args
    (options, args) = parser.parse_args()

    for attr in dir(options):
        if attr in OPTIONS:
            OPTIONS[attr] = getattr(options, attr)

    if stat.S_ISSOCK(mode) or OPTIONS["logger"] == "syslog":
        # log to syslog.  Facility 11 isn't in the class, but it's FTP on linux
        logger = logging.handlers.SysLogHandler("/dev/log", 11)
        logger.setFormatter(
            logging.Formatter('%(filename)s: %(levelname)s: %(message)s'))
    elif OPTIONS["logger"] == "stream":
        # log to stdout
        logger = logging.StreamHandler()
        logger.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
    else:
        logger = logging.FileHandler("/var/log/tftpd")
        logger.setFormatter(logging.Formatter(
            "%(asctime)s %(name)s: %(levelname)s: %(message)s"))

    logging.getLogger().addHandler(logger)

    if OPTIONS["debug"]:
        logging.getLogger().setLevel(logging.DEBUG)
    elif OPTIONS["verbose"]:
        logging.getLogger().setLevel(logging.INFO)
    else:
        logging.getLogger().setLevel(logging.WARN)

    if stat.S_ISSOCK(mode):
        OPTIONS["sock"] = socket.fromfd(sys.stdin.fileno(), socket.AF_INET, socket.SOCK_DGRAM, 0)
    else:
        OPTIONS["sock"] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
        OPTIONS["sock"].setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            OPTIONS["sock"].bind(("", OPTIONS["port"]))
        except socket.error as e:
            if e[0] in (errno.EPERM, errno.EACCES):
                print("Unable to bind to port %d" % OPTIONS["port"])
                return -1
            else:
                raise

    OPTIONS["sock"].setblocking(0)

    if os.getuid() == 0:
        uid = pwd.getpwnam(OPTIONS["user"])[2]
        os.setreuid(uid, uid)

    # This takes a while, so do it after we open the port, so we
    # don't drop the packet that spawned us
    templar = cobbler.templar.Templar(None)

    io_loop = ioloop.IOLoop.instance()
    io_loop.add_handler(OPTIONS["sock"].fileno(), partial(new_req, OPTIONS["sock"], templar), io_loop.READ)
    # Shove the timeout into OPTIONS, because it's there
    if OPTIONS["idle"] > 0:
        OPTIONS["idle_timer"] = io_loop.add_timeout(time.time() + OPTIONS["idle"], lambda: idle_out())

    logging.info('Starting Eventloop')
    try:
        try:
            io_loop.start()
        except KeyboardInterrupt:
            # Someone hit ^C
            logging.info('Exiting')
    finally:
        OPTIONS["sock"].close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
