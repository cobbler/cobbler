import os
import shutil
from contextlib import contextmanager

import pytest


def pytest_addoption(parser):
    parser.addoption("-E", action="store", metavar="NAME", help="only run tests matching the environment NAME.")


def pytest_configure(config):
    # register an additional marker
    config.addinivalue_line("markers", "env(name): mark test to run only on named environment")

@contextmanager
def does_not_raise():
    yield


@pytest.fixture(scope="session")
def file_basedir():
    """
    This is the base-directory for fake files which are needed for the test. The advantage of the location under
    ``/dev/shm`` is that it get's wiped per default after a reboot of the system.

    :return: ``/dev/shm/cobbler_test``
    """
    return "/dev/shm/cobbler_test"


@pytest.fixture(scope="session", autouse=True)
def create_file_basedir(file_basedir):
    """
    This creates the directory needed for the cobbler tests.

    :param file_basedir: See the corresponding fixture.
    """
    if not os.path.exists(file_basedir):
        os.makedirs(file_basedir)


@pytest.fixture(scope="session", autouse=True)
def delete_file_basedir(file_basedir):
    if os.path.exists(file_basedir):
        shutil.rmtree(file_basedir)


@pytest.fixture()
def create_testfile(file_basedir):
    def _create_testfile(filename):
        path = os.path.join(file_basedir, filename)
        if not os.path.exists(path):
            f = open(path, "w+")
            f.close()
    return _create_testfile


@pytest.fixture()
def delete_testfile(file_basedir):
    def _delete_testfile(filename):
        path = os.path.join(file_basedir, filename)
        if os.path.exists(path):
            os.remove(path)
    return _delete_testfile


@pytest.fixture()
def create_kernel_initrd(create_file_basedir, file_basedir, create_testfile):
    def _create_kernel_initrd(name_kernel, name_initrd):
        create_testfile(name_kernel)
        create_testfile(name_initrd)
    return _create_kernel_initrd


@pytest.fixture()
def delete_kernel_initrd(file_basedir, delete_testfile):
    def _delete_kernel_initrd(name_kernel, name_initrd):
        delete_testfile(name_kernel)
        delete_testfile(name_initrd)
    return _delete_kernel_initrd
