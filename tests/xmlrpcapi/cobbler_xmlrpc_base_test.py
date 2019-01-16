import unittest
import logging
import sys
import xmlrpc.client as xmlrpcclient
from cobbler.utils import local_get_cobbler_api_url, get_shared_secret

# "import xmlrpc.client" does currently not work. No explanation found anywhere.


class CobblerXmlRpcBaseTest(unittest.TestCase):

    def setUp(self):
        """
        Setup Cobbler XML-RPC connection and login
        """

        # create logger
        logging.basicConfig(stream=sys.stderr)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)

        # create XML-RPC client and connect to server
        api_url = local_get_cobbler_api_url()
        self.remote = xmlrpcclient.Server(api_url, allow_none=True)
        shared_secret = get_shared_secret()
        self.token = self.remote.login("", shared_secret)
        if not self.token:
            sys.exit(1)

    def tearDown(self):
        """
        Cleanup here
        """
        return


if __name__ == '__main__':
    unittest.main()
