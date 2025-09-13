"""
This module defines the `Option` classes for managing power control settings of Cobbler items.
"""

from typing import TYPE_CHECKING, Any

from cobbler import power_manager
from cobbler.items.options.base import ItemOption
from cobbler.utils import filesystem_helpers

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.items.system import System

    LazyProperty = property
else:
    from cobbler.decorator import LazyProperty


class PowerOption(ItemOption["System"]):
    """
    Option class for managing power control settings for a Cobbler System.

    Provides properties and methods to configure power type, credentials, and connection options.
    """

    def __init__(self, api: "CobblerAPI", item: "System", **kwargs: Any) -> None:
        super().__init__(api=api, item=item, **kwargs)
        self._address = ""
        self._id = ""
        self._password = ""
        self._type = ""
        self._user = ""
        self._options = ""
        self._identity_file = ""

        if len(kwargs) > 0:
            self.from_dict(kwargs)

    @property
    def parent_name(self) -> str:
        return "power"

    @LazyProperty
    def type(self) -> str:
        """
        power_type property.

        :getter: Returns the value for ``power_type``.
        :setter: Sets the value for the property ``power_type``.
        """
        return self._type

    @type.setter
    def type(self, power_type: str):
        """
        Setter for the power_type of the System class.

        :param power_type: The new value for the ``power_type`` property.
        :raises TypeError: In case power_type is no string.
        """
        if not isinstance(power_type, str):  # type: ignore
            raise TypeError("power_type must be of type str")
        if not power_type:
            self._type = ""
            return
        power_manager.validate_power_type(power_type)
        self._type = power_type

    @LazyProperty
    def identity_file(self) -> str:
        """
        power_identity_file property.

        :getter: Returns the value for ``power_identity_file``.
        :setter: Sets the value for the property ``power_identity_file``.
        """
        return self._identity_file

    @identity_file.setter
    def identity_file(self, power_identity_file: str):
        """
        Setter for the power_identity_file of the System class.

        :param power_identity_file: The new value for the ``power_identity_file`` property.
        :raises TypeError: In case power_identity_file is no string.
        """
        if not isinstance(power_identity_file, str):  # type: ignore
            raise TypeError(
                "Field power_identity_file of object system needs to be of type str!"
            )
        filesystem_helpers.safe_filter(power_identity_file)
        self._identity_file = power_identity_file

    @LazyProperty
    def options(self) -> str:
        """
        power_options property.

        :getter: Returns the value for ``power_options``.
        :setter: Sets the value for the property ``power_options``.
        """
        return self._options

    @options.setter
    def options(self, power_options: str):
        """
        Setter for the power_options of the System class.

        :param power_options: The new value for the ``power_options`` property.
        :raises TypeError: In case power_options is no string.
        """
        if not isinstance(power_options, str):  # type: ignore
            raise TypeError(
                "Field power_options of object system needs to be of type str!"
            )
        filesystem_helpers.safe_filter(power_options)
        self._options = power_options

    @LazyProperty
    def user(self) -> str:
        """
        user property.

        :getter: Returns the value for ``power.user``.
        :setter: Sets the value for the property ``power.user``.
        """
        return self._user

    @user.setter
    def user(self, power_user: str):
        """
        Setter for the power.user of the System class.

        :param power_user: The new value for the ``power.user`` property.
        :raises TypeError: In case power_user is no string.
        """
        if not isinstance(power_user, str):  # type: ignore
            raise TypeError(
                "Field power_user of object system needs to be of type str!"
            )
        filesystem_helpers.safe_filter(power_user)
        self._user = power_user

    @LazyProperty
    def password(self) -> str:
        """
        power password property.

        :getter: Returns the value for ``power_pass``.
        :setter: Sets the value for the property ``power_pass``.
        """
        return self._password

    @password.setter
    def password(self, power_pass: str):
        """
        Setter for the power password of the System class.

        :param power_pass: The new value for the ``power_pass`` property.
        :raises TypeError: In case power_pass is no string.
        """
        if not isinstance(power_pass, str):  # type: ignore
            raise TypeError(
                "Field power_pass of object system needs to be of type str!"
            )
        filesystem_helpers.safe_filter(power_pass)
        self._password = power_pass

    @LazyProperty
    def address(self) -> str:
        """
        address property.

        :getter: Returns the value for ``power_address``.
        :setter: Sets the value for the property ``power_address``.
        """
        return self._address

    @address.setter
    def address(self, power_address: str):
        """
        Setter for the power_address of the System class.

        :param power_address: The new value for the ``power_address`` property.
        :raises TypeError: In case power_address is no string.
        """
        if not isinstance(power_address, str):  # type: ignore
            raise TypeError(
                "Field power_address of object system needs to be of type str!"
            )
        filesystem_helpers.safe_filter(power_address)
        self._address = power_address

    @LazyProperty
    def id(self) -> str:
        """
        id property.

        :getter: Returns the value for ``power_id``.
        :setter: Sets the value for the property ``power_id``.
        """
        return self._id

    @id.setter
    def id(self, power_id: str):
        """
        Setter for the power_id of the System class.

        :param power_id: The new value for the ``power_id`` property.
        :raises TypeError: In case power_id is no string.
        """
        if not isinstance(power_id, str):  # type: ignore
            raise TypeError("Field power_id of object system needs to be of type str!")
        filesystem_helpers.safe_filter(power_id)
        self._id = power_id
