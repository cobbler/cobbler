import pytest

from cobbler.actions import mkloaders


@pytest.fixture(scope="function", autouse=True)
def create_loaders(cobbler_api):
    loaders = mkloaders.MkLoaders(cobbler_api)
    loaders.run()
