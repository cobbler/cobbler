"""
TODO
"""

import uuid
from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Union

from cobbler import enums
from cobbler.decorator import InheritableDictProperty, LazyProperty
from cobbler.items.abstract.item_inheritable import InheritableItem
from cobbler.utils import input_converters

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class BootableItem(InheritableItem):
    """
    TODO
    """

    # Constants
    TYPE_NAME = "bootableitem"
    COLLECTION_TYPE = "bootableitem"

    @classmethod
    def _remove_depreacted_dict_keys(cls, dictionary: Dict[Any, Any]) -> None:
        super()._remove_depreacted_dict_keys(dictionary)
        if "ks_meta" in dictionary:
            dictionary.pop("ks_meta")
        if "kickstart" in dictionary:
            dictionary.pop("kickstart")

    def __init__(
        self, api: "CobblerAPI", *args: Any, is_subobject: bool = False, **kwargs: Any
    ) -> None:
        """

        :param api: The Cobbler API object which is used for resolving information.
        :param is_subobject: See above extensive description.
        """
        super().__init__(api, *args, is_subobject=is_subobject, **kwargs)
        # Prevent attempts to clear the to_dict cache before the object is initialized.
        self._has_initialized = False

        self._kernel_options: Union[Dict[Any, Any], str] = {}
        self._kernel_options_post: Union[Dict[Any, Any], str] = {}
        self._autoinstall_meta: Union[Dict[Any, Any], str] = {}
        self._boot_files: Union[Dict[Any, Any], str] = {}
        self._template_files: Dict[str, Any] = {}

        if len(kwargs) > 0:
            kwargs.update({"is_subobject": is_subobject})
            BootableItem.from_dict(self, kwargs)
        if self._uid == "":
            self._uid = uuid.uuid4().hex

        if not self._has_initialized:
            self._has_initialized = True

    @abstractmethod
    def make_clone(self) -> "ITEM":  # type: ignore
        """
        Must be defined in any subclass
        """
        raise NotImplementedError("Must be implemented in a specific Item")

    @InheritableDictProperty
    def kernel_options(self) -> Dict[Any, Any]:
        """
        Kernel options are a space delimited list, like 'a=b c=d e=f g h i=j' or a dict.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: The parsed kernel options.
        :setter: The new kernel options as a space delimited list. May raise ``ValueError`` in case of parsing problems.
        """
        return self._resolve_dict("kernel_options")

    @kernel_options.setter  # type: ignore[no-redef]
    def kernel_options(self, options: Dict[str, Any]):
        """
        Setter for ``kernel_options``.

        :param options: The new kernel options as a space delimited list.
        :raises ValueError: In case the values set could not be parsed successfully.
        """
        try:
            value = input_converters.input_string_or_dict(options, allow_multiples=True)
            if value == enums.VALUE_INHERITED:
                self._kernel_options = enums.VALUE_INHERITED
                return
            # pyright doesn't understand that the only valid str return value is this constant.
            self._kernel_options = self._deduplicate_dict("kernel_options", value)  # type: ignore
        except TypeError as error:
            raise TypeError("invalid kernel value") from error

    @InheritableDictProperty
    def kernel_options_post(self) -> Dict[str, Any]:
        """
        Post kernel options are a space delimited list, like 'a=b c=d e=f g h i=j' or a dict.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: The dictionary with the parsed values.
        :setter: Accepts str in above mentioned format or directly a dict.
        """
        return self._resolve_dict("kernel_options_post")

    @kernel_options_post.setter  # type: ignore[no-redef]
    def kernel_options_post(self, options: Union[Dict[Any, Any], str]) -> None:
        """
        Setter for ``kernel_options_post``.

        :param options: The new kernel options as a space delimited list.
        :raises ValueError: In case the options could not be split successfully.
        """
        try:
            self._kernel_options_post = input_converters.input_string_or_dict(
                options, allow_multiples=True
            )
        except TypeError as error:
            raise TypeError("invalid post kernel options") from error

    @InheritableDictProperty
    def autoinstall_meta(self) -> Dict[Any, Any]:
        """
        A comma delimited list of key value pairs, like 'a=b,c=d,e=f' or a dict.
        The meta tags are used as input to the templating system to preprocess automatic installation template files.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: The metadata or an empty dict.
        :setter: Accepts anything which can be split by :meth:`~cobbler.utils.input_converters.input_string_or_dict`.
        """
        return self._resolve_dict("autoinstall_meta")

    @autoinstall_meta.setter  # type: ignore[no-redef]
    def autoinstall_meta(self, options: Dict[Any, Any]):
        """
        Setter for the ``autoinstall_meta`` property.

        :param options: The new options for the automatic installation meta options.
        :raises ValueError: If splitting the value does not succeed.
        """
        value = input_converters.input_string_or_dict(options, allow_multiples=True)
        if value == enums.VALUE_INHERITED:
            self._autoinstall_meta = enums.VALUE_INHERITED
            return
        # pyright doesn't understand that the only valid str return value is this constant.
        self._autoinstall_meta = self._deduplicate_dict("autoinstall_meta", value)  # type: ignore

    @LazyProperty
    def template_files(self) -> Dict[Any, Any]:
        """
        File mappings for built-in configuration management

        :getter: The dictionary with name-path key-value pairs.
        :setter: A dict. If not a dict must be a str which is split by
                 :meth:`~cobbler.utils.input_converters.input_string_or_dict`. Raises ``TypeError`` otherwise.
        """
        return self._template_files

    @template_files.setter
    def template_files(self, template_files: Union[str, Dict[Any, Any]]) -> None:
        """
        A comma seperated list of source=destination templates that should be generated during a sync.

        :param template_files: The new value for the template files which are used for the item.
        :raises ValueError: In case the conversion from non dict values was not successful.
        """
        try:
            self._template_files = input_converters.input_string_or_dict_no_inherit(
                template_files, allow_multiples=False
            )
        except TypeError as error:
            raise TypeError("invalid template files specified") from error

    @LazyProperty
    def boot_files(self) -> Dict[Any, Any]:
        """
        Files copied into tftpboot beyond the kernel/initrd

        :getter: The dictionary with name-path key-value pairs.
        :setter: A dict. If not a dict must be a str which is split by
                 :meth:`~cobbler.utils.input_converters.input_string_or_dict`. Raises ``TypeError`` otherwise.
        """
        return self._resolve_dict("boot_files")

    @boot_files.setter
    def boot_files(self, boot_files: Dict[Any, Any]) -> None:
        """
        A comma separated list of req_name=source_file_path that should be fetchable via tftp.

        .. note:: This property can be set to ``<<inherit>>``.

        :param boot_files: The new value for the boot files used by the item.
        """
        try:
            self._boot_files = input_converters.input_string_or_dict(
                boot_files, allow_multiples=False
            )
        except TypeError as error:
            raise TypeError("invalid boot files specified") from error
