import pytest


@pytest.fixture()
def collection_mgr(cobbler_api):
    return cobbler_api._collection_mgr
