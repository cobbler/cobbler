import pytest

from cobbler.api import CobblerAPI


@pytest.fixture()
def api():
    return CobblerAPI()


@pytest.fixture()
def collection_mgr(api):
    return api._collection_mgr
