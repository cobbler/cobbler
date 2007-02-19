#!/usr/bin/env python

"""
client module for memcached (memory cache daemon)

Overview
========

See U{the MemCached homepage<http://www.danga.com/memcached>} for more about memcached.

Usage summary
=============

This should give you a feel for how this module operates::

    import memcache
    mc = memcache.Client(['127.0.0.1:11211'], debug=0)

    mc.set("some_key", "Some value")
    value = mc.get("some_key")

    mc.set("another_key", 3)
    mc.delete("another_key")
    
    mc.set("key", "1")   # note that the key used for incr/decr must be a string.
    mc.incr("key")
    mc.decr("key")

The standard way to use memcache with a database is like this::

    key = derive_key(obj)
    obj = mc.get(key)
    if not obj:
        obj = backend_api.get(...)
        mc.set(key, obj)

    # we now have obj, and future passes through this code
    # will use the object from the cache.

Detailed Documentation
======================

More detailed documentation is available in the L{Client} class.
"""

import sys
import socket
import time
import types
try:
    import cPickle as pickle
except ImportError:
    import pickle

__author__    = "Evan Martin <martine@danga.com>"
__version__   = "1.2_tummy5"
__copyright__ = "Copyright (C) 2003 Danga Interactive"
__license__   = "Python"

class _Error(Exception):
    pass

class Client:
    """
    Object representing a pool of memcache servers.
    
    See L{memcache} for an overview.

    In all cases where a key is used, the key can be either:
        1. A simple hashable type (string, integer, etc.).
        2. A tuple of C{(hashvalue, key)}.  This is useful if you want to avoid
        making this module calculate a hash value.  You may prefer, for
        example, to keep all of a given user's objects on the same memcache
        server, so you could use the user's unique id as the hash value.

    @group Setup: __init__, set_servers, forget_dead_hosts, disconnect_all, debuglog
    @group Insertion: set, add, replace
    @group Retrieval: get, get_multi
    @group Integers: incr, decr
    @group Removal: delete
    @sort: __init__, set_servers, forget_dead_hosts, disconnect_all, debuglog,\
           set, add, replace, get, get_multi, incr, decr, delete
    """

    _usePickle = False
    _FLAG_PICKLE  = 1<<0
    _FLAG_INTEGER = 1<<1
    _FLAG_LONG    = 1<<2

    _SERVER_RETRIES = 10  # how many times to try finding a free server.

    def __init__(self, servers, debug=0):
        """
        Create a new Client object with the given list of servers.

        @param servers: C{servers} is passed to L{set_servers}.
        @param debug: whether to display error messages when a server can't be
        contacted.
        """
        self.set_servers(servers)
        self.debug = debug
        self.stats = {}
    
    def set_servers(self, servers):
        """
        Set the pool of servers used by this client.

        @param servers: an array of servers.
        Servers can be passed in two forms:
            1. Strings of the form C{"host:port"}, which implies a default weight of 1.
            2. Tuples of the form C{("host:port", weight)}, where C{weight} is
            an integer weight value.
        """
        self.servers = [_Host(s, self.debuglog) for s in servers]
        self._init_buckets()

    def get_stats(self):
        '''Get statistics from each of the servers.  

        @return: A list of tuples ( server_identifier, stats_dictionary ).
            The dictionary contains a number of name/value pairs specifying
            the name of the status field and the string value associated with
            it.  The values are not converted from strings.
        '''
        data = []
        for s in self.servers:
            if not s.connect(): continue
            name = '%s:%s (%s)' % ( s.ip, s.port, s.weight )
            s.send_cmd('stats')
            serverData = {}
            data.append(( name, serverData ))
            readline = s.readline
            while 1:
                line = readline()
                if not line or line.strip() == 'END': break
                stats = line.split(' ', 2)
                serverData[stats[1]] = stats[2]

        return(data)

    def flush_all(self):
        'Expire all data currently in the memcache servers.'
        for s in self.servers:
            if not s.connect(): continue
            s.send_cmd('flush_all')
            s.expect("OK")

    def debuglog(self, str):
        if self.debug:
            sys.stderr.write("MemCached: %s\n" % str)

    def _statlog(self, func):
        if not self.stats.has_key(func):
            self.stats[func] = 1
        else:
            self.stats[func] += 1

    def forget_dead_hosts(self):
        """
        Reset every host in the pool to an "alive" state.
        """
        for s in self.servers:
            s.dead_until = 0

    def _init_buckets(self):
        self.buckets = []
        for server in self.servers:
            for i in range(server.weight):
                self.buckets.append(server)

    def _get_server(self, key):
        if type(key) == types.TupleType:
            serverhash = key[0]
            key = key[1]
        else:
            serverhash = hash(key)

        for i in range(Client._SERVER_RETRIES):
            server = self.buckets[serverhash % len(self.buckets)]
            if server.connect():
                #print "(using server %s)" % server,
                return server, key
            serverhash = hash(str(serverhash) + str(i))
        return None, None

    def disconnect_all(self):
        for s in self.servers:
            s.close_socket()
    
    def delete(self, key, time=0):
        '''Deletes a key from the memcache.
        
        @return: Nonzero on success.
        @rtype: int
        '''
        server, key = self._get_server(key)
        if not server:
            return 0
        self._statlog('delete')
        if time != None:
            cmd = "delete %s %d" % (key, time)
        else:
            cmd = "delete %s" % key

        try:
            server.send_cmd(cmd)
            server.expect("DELETED")
        except socket.error, msg:
            server.mark_dead(msg[1])
            return 0
        return 1

    def incr(self, key, delta=1):
        """
        Sends a command to the server to atomically increment the value for C{key} by
        C{delta}, or by 1 if C{delta} is unspecified.  Returns None if C{key} doesn't
        exist on server, otherwise it returns the new value after incrementing.

        Note that the value for C{key} must already exist in the memcache, and it
        must be the string representation of an integer.

        >>> mc.set("counter", "20")  # returns 1, indicating success
        1
        >>> mc.incr("counter")
        21
        >>> mc.incr("counter")
        22

        Overflow on server is not checked.  Be aware of values approaching
        2**32.  See L{decr}.

        @param delta: Integer amount to increment by (should be zero or greater).
        @return: New value after incrementing.
        @rtype: int
        """
        return self._incrdecr("incr", key, delta)

    def decr(self, key, delta=1):
        """
        Like L{incr}, but decrements.  Unlike L{incr}, underflow is checked and
        new values are capped at 0.  If server value is 1, a decrement of 2
        returns 0, not -1.

        @param delta: Integer amount to decrement by (should be zero or greater).
        @return: New value after decrementing.
        @rtype: int
        """
        return self._incrdecr("decr", key, delta)

    def _incrdecr(self, cmd, key, delta):
        server, key = self._get_server(key)
        if not server:
            return 0
        self._statlog(cmd)
        cmd = "%s %s %d" % (cmd, key, delta)
        try:
            server.send_cmd(cmd)
            line = server.readline()
            return int(line)
        except socket.error, msg:
            server.mark_dead(msg[1])
            return None

    def add(self, key, val, time=0):
        '''
        Add new key with value.
        
        Like L{set}, but only stores in memcache if the key doesn\'t already exist.

        @return: Nonzero on success.
        @rtype: int
        '''
        return self._set("add", key, val, time)
    def replace(self, key, val, time=0):
        '''Replace existing key with value.
        
        Like L{set}, but only stores in memcache if the key already exists.  
        The opposite of L{add}.

        @return: Nonzero on success.
        @rtype: int
        '''
        return self._set("replace", key, val, time)
    def set(self, key, val, time=0):
        '''Unconditionally sets a key to a given value in the memcache.

        The C{key} can optionally be an tuple, with the first element being the
        hash value, if you want to avoid making this module calculate a hash value.
        You may prefer, for example, to keep all of a given user's objects on the
        same memcache server, so you could use the user's unique id as the hash
        value.

        @return: Nonzero on success.
        @rtype: int
        '''
        return self._set("set", key, val, time)
    
    def _set(self, cmd, key, val, time):
        server, key = self._get_server(key)
        if not server:
            return 0

        self._statlog(cmd)

        flags = 0
        if isinstance(val, types.StringTypes):
            pass
        elif isinstance(val, int):
            flags |= Client._FLAG_INTEGER
            val = "%d" % val
        elif isinstance(val, long):
            flags |= Client._FLAG_LONG
            val = "%d" % val
        elif self._usePickle:
            flags |= Client._FLAG_PICKLE
            val = pickle.dumps(val, 2)
        else:
            pass
        
        fullcmd = "%s %s %d %d %d\r\n%s" % (cmd, key, flags, time, len(val), val)
        try:
            server.send_cmd(fullcmd)
            server.expect("STORED")
        except socket.error, msg:
            server.mark_dead(msg[1])
            return 0
        return 1

    def get(self, key):
        '''Retrieves a key from the memcache.
        
        @return: The value or None.
        '''
        server, key = self._get_server(key)
        if not server:
            return None

        self._statlog('get')

        try:
            server.send_cmd("get %s" % key)
            rkey, flags, rlen, = self._expectvalue(server)
            if not rkey:
                return None
            value = self._recv_value(server, flags, rlen)
            server.expect("END")
        except (_Error, socket.error), msg:
            if type(msg) is types.TupleType:
                msg = msg[1]
            server.mark_dead(msg)
            return None
        return value

    def get_multi(self, keys):
        '''
        Retrieves multiple keys from the memcache doing just one query.
        
        >>> success = mc.set("foo", "bar")
        >>> success = mc.set("baz", 42)
        >>> mc.get_multi(["foo", "baz", "foobar"]) == {"foo": "bar", "baz": 42}
        1

        This method is recommended over regular L{get} as it lowers the number of
        total packets flying around your network, reducing total latency, since
        your app doesn\'t have to wait for each round-trip of L{get} before sending
        the next one.

        @param keys: An array of keys.
        @return:  A dictionary of key/value pairs that were available.

        '''

        self._statlog('get_multi')

        server_keys = {}

        # build up a list for each server of all the keys we want.
        for key in keys:
            server, key = self._get_server(key)
            if not server:
                continue
            if not server_keys.has_key(server):
                server_keys[server] = []
            server_keys[server].append(key)

        # send out all requests on each server before reading anything
        dead_servers = []
        for server in server_keys.keys():
            try:
                server.send_cmd("get %s" % " ".join(server_keys[server]))
            except socket.error, msg:
                server.mark_dead(msg[1])
                dead_servers.append(server)

        # if any servers died on the way, don't expect them to respond.
        for server in dead_servers:
            del server_keys[server]

        retvals = {}
        for server in server_keys.keys():
            try:
                line = server.readline()
                while line and line != 'END':
                    rkey, flags, rlen = self._expectvalue(server, line)
                    #  Bo Yang reports that this can sometimes be None
                    if rkey is not None:
                        val = self._recv_value(server, flags, rlen)
                        retvals[rkey] = val
                    line = server.readline()
            except (_Error, socket.error), msg:
                server.mark_dead(msg)
        return retvals

    def _expectvalue(self, server, line=None):
        if not line:
            line = server.readline()

        if line[:5] == 'VALUE':
            resp, rkey, flags, len = line.split()
            flags = int(flags)
            rlen = int(len)
            return (rkey, flags, rlen)
        else:
            return (None, None, None)

    def _recv_value(self, server, flags, rlen):
        rlen += 2 # include \r\n
        buf = server.recv(rlen)
        if len(buf) != rlen:
            raise _Error("received %d bytes when expecting %d" % (len(buf), rlen))

        if len(buf) == rlen:
            buf = buf[:-2]  # strip \r\n

        if flags == 0:
            val = buf
        elif flags & Client._FLAG_INTEGER:
            val = int(buf)
        elif flags & Client._FLAG_LONG:
            val = long(buf)
        elif self._usePickle and flags & Client._FLAG_PICKLE:
            try:
                val = pickle.loads(buf)
            except:
                self.debuglog('Pickle error...\n')
                val = None
        else:
            self.debuglog("unknown flags on get: %x\n" % flags)

        return val

class _Host:
    _DEAD_RETRY = 30  # number of seconds before retrying a dead server.

    def __init__(self, host, debugfunc=None):
        if isinstance(host, types.TupleType):
            host = host[0]
            self.weight = host[1]
        else:
            self.weight = 1

        if host.find(":") > 0:
            self.ip, self.port = host.split(":")
            self.port = int(self.port)
        else:
            self.ip, self.port = host, 11211

        if not debugfunc:
            debugfunc = lambda x: x
        self.debuglog = debugfunc

        self.deaduntil = 0
        self.socket = None
    
    def _check_dead(self):
        if self.deaduntil and self.deaduntil > time.time():
            return 1
        self.deaduntil = 0
        return 0

    def connect(self):
        if self._get_socket():
            return 1
        return 0

    def mark_dead(self, reason):
        self.debuglog("MemCache: %s: %s.  Marking dead." % (self, reason))
        self.deaduntil = time.time() + _Host._DEAD_RETRY
        self.close_socket()
        
    def _get_socket(self):
        if self._check_dead():
            return None
        if self.socket:
            return self.socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Python 2.3-ism:  s.settimeout(1)
        try:
            s.connect((self.ip, self.port))
        except socket.error, msg:
            self.mark_dead("connect: %s" % msg[1])
            return None
        self.socket = s
        return s
    
    def close_socket(self):
        if self.socket:
            self.socket.close()
            self.socket = None

    def send_cmd(self, cmd):
        if len(cmd) > 100:
            self.socket.sendall(cmd)
            self.socket.sendall('\r\n')
        else:
            self.socket.sendall(cmd + '\r\n')

    def readline(self):
        buffers = ''
        recv = self.socket.recv
        while 1:
            data = recv(1)
            if not data:
                self.mark_dead('Connection closed while reading from %s'
                        % repr(self))
                break
            if data == '\n' and buffers and buffers[-1] == '\r':
                return(buffers[:-1])
            buffers = buffers + data
        return(buffers)

    def expect(self, text):
        line = self.readline()
        if line != text:
            self.debuglog("while expecting '%s', got unexpected response '%s'" % (text, line))
        return line
    
    def recv(self, rlen):
        buf = ''
        recv = self.socket.recv
        while len(buf) < rlen:
            buf = buf + recv(rlen - len(buf))
        return buf

    def __str__(self):
        d = ''
        if self.deaduntil:
            d = " (dead until %d)" % self.deaduntil
        return "%s:%d%s" % (self.ip, self.port, d)

def _doctest():
    import doctest, memcache
    servers = ["127.0.0.1:11211"]
    mc = Client(servers, debug=1)
    globs = {"mc": mc}
    return doctest.testmod(memcache, globs=globs)

if __name__ == "__main__":
    print "Testing docstrings..."
    _doctest()
    print "Running tests:"
    print
    #servers = ["127.0.0.1:11211", "127.0.0.1:11212"]
    servers = ["127.0.0.1:11211"]
    mc = Client(servers, debug=1)

    def to_s(val):
        if not isinstance(val, types.StringTypes):
            return "%s (%s)" % (val, type(val))
        return "%s" % val
    def test_setget(key, val):
        print "Testing set/get {'%s': %s} ..." % (to_s(key), to_s(val)),
        mc.set(key, val)
        newval = mc.get(key)
        if newval == val:
            print "OK"
            return 1
        else:
            print "FAIL"
            return 0

    class FooStruct:
        def __init__(self):
            self.bar = "baz"
        def __str__(self):
            return "A FooStruct"
        def __eq__(self, other):
            if isinstance(other, FooStruct):
                return self.bar == other.bar
            return 0
        
    test_setget("a_string", "some random string")
    test_setget("an_integer", 42)
    if test_setget("long", long(1<<30)):
        print "Testing delete ...",
        if mc.delete("long"):
            print "OK"
        else:
            print "FAIL"
    print "Testing get_multi ...",
    print mc.get_multi(["a_string", "an_integer"])

    print "Testing get(unknown value) ...",
    print to_s(mc.get("unknown_value"))

    f = FooStruct()
    test_setget("foostruct", f)

    print "Testing incr ...",
    x = mc.incr("an_integer", 1)
    if x == 43:
        print "OK"
    else:
        print "FAIL"

    print "Testing decr ...",
    x = mc.decr("an_integer", 1)
    if x == 42:
        print "OK"
    else:
        print "FAIL"



# vim: ts=4 sw=4 et :
