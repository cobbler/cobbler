"""
All code blonging to Cobbler Templates.

Changelog:

V3.4.0 (unrelased):
    * Initial add of datatype.
"""

import copy
import os
import pathlib
from typing import TYPE_CHECKING, Any, List, Set, Type

from cobbler import enums, validate
from cobbler.items.abstract.base_item import BaseItem
from cobbler.items.options.uri import URIOption

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.items.options.uri import URIOption

    LazyProperty = property
else:
    from cobbler.decorator import LazyProperty


class Template(BaseItem):
    """
    A Cobbler template object.
    """

    TYPE_NAME = "template"
    COLLECTION_TYPE = "template"

    def __init__(self, api: "CobblerAPI", *args: Any, **kwargs: Any):
        """
        Constructor

        :param api: The Cobbler API object which is used for resolving information.
        """
        super().__init__(api)
        # Prevent attempts to clear the to_dict cache before the object is initialized.
        self._has_initialized = False

        def autoinstall_path_validation(
            self: "URIOption", cobbler_api: "CobblerAPI", value: str
        ) -> bool:
            """
            Autoinstall Path validation hook that allows to validate if the path is a valid one.

            :param api: The Cobbler API object to search for data.
            :param value: The new value for the path component.
            :returns: True in case the path is valid, False otherwhise.
            """
            return validate.validate_autoinstall_template_file_path(
                cobbler_api,
                enums.TemplateSchema.to_enum(self.schema),
                self._item.template_type,  # type: ignore
                value,
            )

        self._template_type = ""
        self._uri = URIOption(api, self, path_validator=autoinstall_path_validation)
        self._built_in = False
        self._tags: Set[str] = set()
        self.__content = ""
        self._inmemory = True

        if len(kwargs) > 0:
            if "template_type" in kwargs:
                self.template_type = kwargs["template_type"]
            self.from_dict(kwargs)

        if self._uri.schema == enums.TemplateSchema.IMPORTLIB.value:
            # All templates that are sourced via importlib are built-in
            self._built_in = True
            self.__content = pathlib.Path(self._uri.path).read_text(encoding="UTF-8")
            self._inmemory = True
        if not self._has_initialized:
            self._has_initialized = True

    def make_clone(self) -> "Template":
        seed_dict = copy.deepcopy(self.to_dict())
        seed_dict.pop("uid", None)
        seed_dict.pop("built_in", None)
        return Template(self.api, **seed_dict)

    def _resolve(self, property_name: List[str]) -> Any:
        settings_name = property_name[-1]
        if property_name[-1] == "owners":
            settings_name = "default_ownership"
        raw_value = self.__get_raw_value(self, property_name)
        if raw_value == enums.VALUE_INHERITED:
            return getattr(self.api.settings(), settings_name)
        else:
            return raw_value

    def _resolve_enum(
        self, property_name: List[str], enum_type: Type[enums.ConvertableEnum]
    ) -> Any:
        # The template doesn't have any enum types that need resolving
        return None

    def _resolve_list(self, property_name: List[str]) -> Any:
        # The template doesn't have any enum types that need resolving
        return None

    def __get_raw_value(self, obj: Any, property_name: List[str]) -> Any:
        """
        Retrieves the raw value of a nested attribute from an object using a list of property names.

        :returns: The raw value of the property.
        :raises AttributeError: In case the property doesn't have the requested attribute.
        """
        if hasattr(obj, f"_{property_name[0]}"):
            property_key = property_name.pop(0)
            if len(property_name) > 0:
                return self.__get_raw_value(getattr(obj, property_key), property_name)
            return getattr(obj, f"_{property_key}")
        raise AttributeError(
            f'Could not retrieve "{property_name[0]}" with obj "{obj}!'
        )

    def refresh_content(self) -> bool:
        """
        Reads the template from the currently set uri and caches it in-memory. In case a given URI is
        unavailable, the old template content is kept and a message is written to the log.

        :returns: If reading the template was successful.
        """
        if self._uri.schema == enums.TemplateSchema.IMPORTLIB.value:
            # Built-In templates never change. If users edit them, this is undefined behavior.
            return True
        elif self._uri.schema == enums.TemplateSchema.ENVIRONMENT.value:
            self.__content = os.environ[self._uri.path]
            return True
        elif self._uri.schema == enums.TemplateSchema.FILE.value:
            self.__content = (
                pathlib.Path(self.api.settings().autoinstall_templates_dir)
                / self._uri.path
            ).read_text(encoding="UTF-8")
            return True
        return False

    @property
    def content(self) -> str:
        """
        Property for the content of the template.

        :getter: Returns a cached version of the template content.
        :setter: In case a supported template type is set this will write the given content to the target URI.
        """
        return self.__content

    @content.setter
    def content(self, val: str) -> None:
        """
        The setter for the content of a given template. Accept a string.

        :raises ValueError: In case the URI is empty, the schema is of type improtlib or the template schema is
            unsupported.
        """
        if not self._uri.path:
            raise ValueError("Setting the content with an empty URI is not possible!")
        if self._uri.schema == enums.TemplateSchema.IMPORTLIB:
            raise ValueError("The content of built-in templates cannot be updated.")
        elif self._uri.schema == enums.TemplateSchema.ENVIRONMENT:
            os.environ[self.uri.path] = val
        elif self._uri.schema == enums.TemplateSchema.FILE:
            pathlib.Path(self._uri.path).write_text(val, encoding="UTF-8")
        else:
            raise ValueError("Unspported template type!")
        self.__content = val

    @property
    def uri(self) -> URIOption:
        """
        Represents the location where the template is located at.

        :getter: Returns the current URIOption object.
        """
        return self._uri

    @LazyProperty
    def template_type(self) -> str:
        """
        This represents the template type/language that must be used to render the template.

        :getter: Returns the current template_type.
        :setter: Sets the new value for the template_type property.
        """
        return self._template_type

    @template_type.setter
    def template_type(self, val: str):
        """
        Setter for the template_type property.

        :param val: The string with the new value.
        """
        template_providers = self.api.templar.available_template_providers
        if val not in template_providers:
            raise ValueError(
                "Given template type not in the list of available template providers"
                f" ({', '.join(template_providers)})!"
            )
        self._template_type = val

    @LazyProperty
    def built_in(self) -> bool:
        """
        Property that represents if a template is built-in or not.

        If a template is built-in it is not persisted to disk and none of it effectively becomes read-only.

        :getter: Returns True if the template is built-in.
        """
        return self._built_in

    @LazyProperty
    def tags(self) -> Set[str]:
        """
        Property that represents the set of tags a template has. A tag can be any string, there are however strings with
        special meanings that means that a template is used for a special purpose inside of Cobbler.

        :getter: Returns the current Set of tags.
        :setter: Sets the new value for the tags property.
        """
        return self._tags

    @tags.setter
    def tags(self, val: Set[str]):
        """
        Setter for the tags property.

        :param val: The string with the new value.
        """
        self._tags = val
