"""
Utility module to abstract the construction of the Kernel Command Line for Linux. The options available differ by
version and the backported patches that fix and add functionality.

More information: https://docs.kernel.org/admin-guide/kernel-parameters.html
"""

from typing import TYPE_CHECKING, Any, Dict, List, Tuple, Union

from cobbler import utils

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class KernelCommandLine:
    """
    Class to interface with a given Kernel Command Line.
    """

    def __init__(self, api: "CobblerAPI"):
        self.__api = api
        self.__append_line: List[Union[Tuple[str, str], Tuple[str]]] = []

    def append_key_value(self, key: str, value: str) -> None:
        """
        Append a key-value pair to the Kernel Command Line.

        :param key: The key of the option.
        :param value: The value of the option.
        """
        self.__append_line.append((key, value))

    def append_key(self, key: str) -> None:
        """
        Append a keyword-only argument to the Kernel Command Line.

        :param key: The key of the option.
        """
        self.__append_line.append((key,))

    def append_raw(self, value: str) -> None:
        """
        Append a raw string to the kernel command line. This is most likely useful for initializing the "APPEND" option
        for GRUB.

        :param value: The value of the option.
        """
        self.__append_line.append((value,))

    def replace_key(self, key: str, condition: str, new_value: str) -> None:
        """
        Replace a given key with a given condition inside the kernel command line. This replaces all occurences, not
        only the first one.

        :param key: The key of the option.
        :param condition: The condition that is applied to the value of the key.
        :param new_value: The value that replaces the old one.
        """
        for idx, element in enumerate(self.__append_line):
            if len(element) == 1:
                continue
            if element[0] == key and element[1] == condition:
                self.__append_line[idx] = (key, new_value)

    def render(self, blended: Dict[str, Any]) -> str:
        """
        Render the Kernel Command Line with the default templating language.

        :param blended: The context used for variable substitution.
        :returns: The rendered Kernel Command Line.
        """
        append_line = ""
        for element in self.__append_line:
            if len(element) == 1:
                append_line += f" {element[0]}"
            else:
                append_line += f" {element[0]}={element[1]}"
        append_line = append_line.lstrip()
        # do variable substitution on the append line promote all of the autoinstall_meta variables
        if "autoinstall_meta" in blended:
            blended.update(blended["autoinstall_meta"])
        return self.__api.templar.render(
            append_line,
            utils.flatten(blended),  # type: ignore
            None,
        )
