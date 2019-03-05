import pytest

from cobbler import utils


# TODO: scan output of import to build list of imported distros/profiles
#       and compare to expected list. Then use that list to run reports
#       and for later cleanup


@pytest.fixture(scope="class")
def setup():
    """
    Setup the import tests. Currently just "pass".
    """
    pass


@pytest.fixture(scope="class")
def teardown():
    """
    Teardown the import tests. Currently just "pass".
    """
    yield
    pass


@pytest.fixture()
def import_distro(name, path):
    """
    Imports a distribution with the cobbler cli-command into a running system.
    :param name: Name of the distro.
    :param path: Path to the distro.
    :return: A touple of the data which is returned by the cobbler-cli-client and the status.
    """
    return utils.subprocess_sp(None, ["cobbler", "import", "--name=test-%s" % name, "--path=%s" % path],
                               shell=False)


@pytest.fixture()
def report_distro(name):
    """
    Asks the cobbler cli about a report for the given distribution.
    :param name: Name of the distribution.
    :return: A touple of the data which is returned by the cobbler-cli-client and the status.
    """
    return utils.subprocess_sp(None, ["cobbler", "distro", "report", "--name=test-%s" % name], shell=False)


@pytest.fixture()
def report_profile(name):
    """
    Asks the cobbler cli about a report for a given profile.
    :param name: Name of the profile.
    :return: A touple of the data which is returned by the cobbler-cli-client and the status.
    """
    return utils.subprocess_sp(None, ["cobbler", "profile", "report", "--name=test-%s" % name], shell=False)


@pytest.fixture()
def remove_distro(name):
    """
    Performs a remove for a distribution via the cobbler-cli for a given distribution.
    :param name: Name of the distribution.
    :return: A touple of the data which is returned by the cobbler-cli-client and the status.
    """
    return utils.subprocess_sp(None, ["cobbler", "distro", "remove", "--recursive", "--name=test-%s" % name],
                               shell=False)
