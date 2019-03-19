import logging
import sys
import xmlrpc.client as xmlrpcclient

import pytest

from cobbler.utils import local_get_cobbler_api_url, get_shared_secret

# "import xmlrpc.client" does currently not work. No explanation found anywhere.


def pytest_addoption(parser):
    parser.addoption("-E", action="store", metavar="NAME", help="only run tests matching the environment NAME.")


def pytest_configure(config):
    # register an additional marker
    config.addinivalue_line("markers", "env(name): mark test to run only on named environment")


@pytest.fixture(scope="session")
def remote(cobbler_xmlrpc_base):
    """

    :param cobbler_xmlrpc_base:
    :return:
    """
    return cobbler_xmlrpc_base[0]


@pytest.fixture(scope="session")
def token(cobbler_xmlrpc_base):
    """

    :param cobbler_xmlrpc_base:
    :return:
    """
    return cobbler_xmlrpc_base[1]


@pytest.fixture(scope="session")
def cobbler_xmlrpc_base():
    """
    Initialises the api object and makes it available to the test.
    """
    # create logger
    logging.basicConfig(stream=sys.stderr)
    logger = logging.getLogger("xobbler_xmlrpc_base")
    logger.setLevel(logging.DEBUG)

    # create XML-RPC client and connect to server
    api_url = local_get_cobbler_api_url()
    remote = xmlrpcclient.Server(api_url, allow_none=True)
    shared_secret = get_shared_secret()
    token = remote.login("", shared_secret)
    if not token:
        sys.exit(1)
    yield (remote, token)
