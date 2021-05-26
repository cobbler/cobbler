import os
import shutil
from contextlib import contextmanager
from pathlib import Path

import pytest


def pytest_addoption(parser):
    parser.addoption("-E", action="store", metavar="NAME", help="only run tests matching the environment NAME.")


def pytest_configure(config):
    # register an additional marker
    config.addinivalue_line("markers", "env(name): mark test to run only on named environment")


@contextmanager
def does_not_raise():
    yield


@pytest.fixture(scope="function")
def create_testfile(tmp_path):
    def _create_testfile(filename):
        path = os.path.join(tmp_path, filename)
        if not os.path.exists(path):
            Path(path).touch()
        return path
    return _create_testfile


@pytest.fixture(scope="function")
def create_kernel_initrd(create_testfile):
    def _create_kernel_initrd(name_kernel, name_initrd):
        create_testfile(name_kernel)
        return os.path.dirname(create_testfile(name_initrd))
    return _create_kernel_initrd
