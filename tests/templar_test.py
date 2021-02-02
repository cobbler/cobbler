import pytest

from cobbler.api import CobblerAPI
from cobbler.cexceptions import CX
from cobbler.cobbler_collections.manager import CollectionManager
from cobbler.templar import Templar


class TemplarTest:
    def test_check_for_invalid_imports(self):
        # Arrange
        test_api = CobblerAPI()
        test_collection_mgr = CollectionManager(test_api)
        test_templar = Templar(test_collection_mgr)
        testdata = "#import json"

        # Act & Assert
        with pytest.raises(CX):
            test_templar.check_for_invalid_imports(testdata)

    def test_render(self):
        # Arrange
        test_api = CobblerAPI()
        test_collection_mgr = CollectionManager(test_api)
        test_templar = Templar(test_collection_mgr)

        # Act
        result = test_templar.render("", {}, None, template_type="cheetah")

        # Assert
        assert False

    def test_render_cheetah(self):
        # Arrange
        test_api = CobblerAPI()
        test_collection_mgr = CollectionManager(test_api)
        test_templar = Templar(test_collection_mgr)

        # Act
        test_templar.render_cheetah()

        # Assert
        assert False

    def test_render_jinja2(self):
        # Arrange
        test_api = CobblerAPI()
        test_collection_mgr = CollectionManager(test_api)
        test_templar = Templar(test_collection_mgr)

        # Act
        test_templar.render_jinja2()

        # Assert
        assert False
