"""
TODO
"""

import shlex
from typing import Any, Dict, Optional, Union

from cobbler import enums


def input_string_or_list_no_inherit(options: Optional[Union[str, list]]) -> list:
    """
    Accepts a delimited list of stuff or a list, but always returns a list.

    :param options: The object to split into a list.
    :return: If ``option`` is ``delete``, ``None`` (object not literal) or an empty str, then an empty list is returned.
             Otherwise, this function tries to return the arg option or tries to split it into a list.
    :raises TypeError: In case the type of ``options`` was neither ``None``, str or list.
    """
    if not options or options == "delete":
        return []
    if isinstance(options, list):
        return options
    if isinstance(options, str):
        tokens = shlex.split(options)
        return tokens
    raise TypeError("invalid input type")


def input_string_or_list(options: Optional[Union[str, list]]) -> Union[list, str]:
    """
    Accepts a delimited list of stuff or a list, but always returns a list.
    :param options: The object to split into a list.
    :return: str when this functions get's passed ``<<inherit>>``. if option is delete then an empty list is returned.
             Otherwise, this function tries to return the arg option or tries to split it into a list.
    :raises TypeError: In case the type of ``options`` was neither ``None``, str or list.
    """
    if options == enums.VALUE_INHERITED:
        return enums.VALUE_INHERITED
    return input_string_or_list_no_inherit(options)


def input_string_or_dict(
    options: Union[str, list, dict], allow_multiples=True
) -> Union[str, dict]:
    """
    Older Cobbler files stored configurations in a flat way, such that all values for strings. Newer versions of Cobbler
    allow dictionaries. This function is used to allow loading of older value formats so new users of Cobbler aren't
    broken in an upgrade.

    :param options: The str or dict to convert.
    :param allow_multiples: True (default) to allow multiple identical keys, otherwise set this false explicitly.
    :return: A dict or the value ``<<inherit>>`` in case it is the only content of ``options``.
    :raises TypeError: Raised in case the input type is wrong.
    """
    if options == enums.VALUE_INHERITED:
        return enums.VALUE_INHERITED
    return input_string_or_dict_no_inherit(options, allow_multiples)


def input_string_or_dict_no_inherit(
    options: Union[str, list, dict], allow_multiples=True
) -> dict:
    """
    See :meth:`~cobbler.utils.input_converters.input_string_or_dict`
    """
    if options is None or options == "delete":
        return {}
    if isinstance(options, list):
        raise TypeError(f"No idea what to do with list: {options}")
    if isinstance(options, str):
        new_dict: Dict[str, Any] = {}
        tokens = shlex.split(options)
        for token in tokens:
            tokens2 = token.split("=", 1)
            if len(tokens2) == 1:
                # this is a singleton option, no value
                key = tokens2[0]
                value = None
            else:
                key = tokens2[0]
                value = tokens2[1]

            # If we're allowing multiple values for the same key, check to see if this token has already been inserted
            # into the dictionary of values already.

            if key in new_dict and allow_multiples:
                # If so, check to see if there is already a list of values otherwise convert the dictionary value to an
                # array, and add the new value to the end of the list.
                if isinstance(new_dict[key], list):
                    new_dict[key].append(value)
                else:
                    new_dict[key] = [new_dict[key], value]
            else:
                new_dict[key] = value
        # make sure we have no empty entries
        new_dict.pop("", None)
        return new_dict
    if isinstance(options, dict):
        options.pop("", None)
        return options
    raise TypeError("invalid input type")


def input_boolean(value: Union[str, bool, int]) -> bool:
    """
    Convert a str to a boolean. If this is not possible or the value is false return false.

    :param value: The value to convert to boolean.
    :return: True if the value is in the following list, otherwise false: "true", "1", "on", "yes", "y" .
    """
    if not isinstance(value, (str, bool, int)):
        raise TypeError(
            "The value handed to the input_boolean function was not convertable due to a wrong type "
            f"(found: {type(value)})!"
        )
    value = str(value).lower()
    return value in ["true", "1", "on", "yes", "y"]


def input_int(value: Union[str, int, float]) -> int:
    """
    Convert a value to integer.

    :param value: The value to convert.
    :raises TypeError: In case after the attempted conversion we still don't have an int.
    :return: The integer if the conversion was successful.
    """
    error_message = "value must be convertable to type int."
    if isinstance(value, (str, float)):
        try:
            converted_value = int(value)
        except ValueError as value_error:
            raise TypeError(error_message) from value_error
        if not isinstance(converted_value, int):
            raise TypeError(error_message)
        return converted_value
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    raise TypeError(error_message)
