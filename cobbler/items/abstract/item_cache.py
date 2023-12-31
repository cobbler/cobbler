"""
Module that contains the logic for Cobbler to cache an item.

The cache significantly speeds up Cobbler. This effect is achieved thanks to the reduced amount of lookups that are
required to be done.
"""

from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class ItemCache:
    """
    A Cobbler ItemCache object.
    """

    def __init__(self, api: "CobblerAPI"):
        """
        Constructor

        Generalized parameterized cache format:
           cache_key        cache_value
         {(P1, P2, .., Pn): value}
        where P1, .., Pn are cache parameters

        Parameterized cache for to_dict(resolved: bool).
        The values of the resolved parameter are the key for the Dict.
        In the to_dict case, there is only one cache parameter and only two key values:
         {True:  cache_value or None,
          False: cache_value or None}
        """
        self._cached_dict: Dict[bool, Optional[Dict[str, Any]]] = {
            True: None,
            False: None,
        }

        self.api = api
        self.settings = api.settings()

    def get_dict_cache(self, resolved: bool) -> Optional[Dict[str, Any]]:
        """
        Gettinging the dict cache.

        :param resolved: "resolved" parameter for Item.to_dict().
        :return: The cache value for the object, or None if not set.
        """
        if self.settings.cache_enabled:
            return self._cached_dict[resolved]
        return None

    def set_dict_cache(self, value: Optional[Dict[str, Any]], resolved: bool):
        """
        Setter for the dict cache.

        :param value: Sets the value for the dict cache.
        :param resolved: "resolved" parameter for Item.to_dict().
        """
        if self.settings.cache_enabled:
            self._cached_dict[resolved] = value

    def clean_dict_cache(self):
        """
        Cleaninig the dict cache.
        """
        if self.settings.cache_enabled:
            self.set_dict_cache(None, True)
            self.set_dict_cache(None, False)

    def clean_cache(self):
        """
        Cleaninig the Item cache.
        """
        if self.settings.cache_enabled:
            self.clean_dict_cache()
