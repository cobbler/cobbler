"""
TODO
"""

from cobbler.items.item import Item


class Template(Item):
    """
    TODO
    """

    TYPE_NAME = "template"
    COLLECTION_TYPE = "template"

    def __init__(self, api):
        super().__init__(api)
        self._template_type = ""
        self._template_uri = ""
        self._built_in = False

    def make_clone(self):
        pass
