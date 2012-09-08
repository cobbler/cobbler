import threading
from cobbler import api as cobbler_api
from cobbler import remote

class TestException(Exception):
    def __init__(self, value):
        self.parameter = value
    def __str__(self):
        return repr(self.parameter)

class CobblerTestXMLRPCServer(remote.CobblerXMLRPCServer):
    def __init__(self,args):
        self.shutdown = False
        remote.CobblerXMLRPCServer.__init__(self,args)
    def do_shutdown(self):
        raise TestException("exiting...")

class CobblerTestXMLRPCInterface(remote.CobblerXMLRPCInterface):
    def __init__(self, api):
        self.shutdown = False
        remote.CobblerXMLRPCInterface.__init__(self,api)

class TestXMLRPCThread(threading.Thread):
    running = True
    def __init__(self):
        self.running = True
        self.capi = cobbler_api.BootAPI()

        self.xmliface = CobblerTestXMLRPCInterface(self.capi)

        self.server = CobblerTestXMLRPCServer(('127.0.0.1', 55555))
        self.server.logRequests = 0
        self.server.register_instance(self.xmliface)

        threading.Thread.__init__(self)
    def run(self):
        while self.running:
            try:
                self.server.serve_forever()
            except:
                pass
        print "XMLRPC thread is no longer running"
    def stop(self):
        self.running = False
        self.server.server_close()
        try:
            self.server.do_shutdown()
        except:
            pass

