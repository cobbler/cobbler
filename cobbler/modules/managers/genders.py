"""
Cobbler Module that manages the cluster configuration tool from CHAOS. For more information please see:
`GitHub - chaos/genders <https://github.com/chaos/genders>`_
"""

import logging
import pathlib
import time
from typing import TYPE_CHECKING, Any, Dict, Optional, Union

from cobbler import enums

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.items.template import Template


logger = logging.getLogger()


def register() -> str:
    """
    We should run anytime something inside of Cobbler changes.

    :return: Always ``/var/lib/cobbler/triggers/change/*``
    """
    return "/var/lib/cobbler/triggers/change/*"


def write_genders_file(
    config: "CobblerAPI",
    profiles_genders: Dict[str, str],
    distros_genders: Dict[str, str],
    mgmtcls_genders: Dict[str, str],
):
    """
    Genders file is over-written when ``manage_genders`` is set in our settings.

    :param config: The API instance to template the data with.
    :param profiles_genders: The profiles which should be included.
    :param distros_genders: The distros which should be included.
    :param mgmtcls_genders: The management classes which should be included.
    :raises OSError: Raised in case the template could not be read.
    """
    search_result = config.find_template(
        True, False, tags=enums.TemplateTag.GENDERS.value
    )
    if search_result is None or not isinstance(search_result, list):
        raise TypeError("Search result for Genders Template must of of type list!")
    genders_template: Optional["Template"] = None
    for template in search_result:
        if enums.TemplateTag.ACTIVE.value in template.tags:
            genders_template = template
            break
        if enums.TemplateTag.DEFAULT.value in template.tags:
            genders_template = template

    if genders_template is None:
        raise ValueError(
            "Neither specific nor default iPXE menu template could be found inside Cobbler!"
        )

    metadata: Dict[str, Union[str, Dict[str, str]]] = {
        "date": time.asctime(time.gmtime()),
        "profiles_genders": profiles_genders,
        "distros_genders": distros_genders,
        "mgmtcls_genders": mgmtcls_genders,
    }

    config.templar.render(
        genders_template.content, metadata, config.settings().genders_settings_file
    )


def run(api: "CobblerAPI", args: Any) -> int:
    """
    Mandatory Cobbler trigger hook.

    :param api: The api to resolve information with.
    :param args: For this implementation unused.
    :return: ``0`` or ``1``, depending on the outcome of the operation.
    """
    # do not run if we are not enabled.
    if not api.settings().manage_genders:
        return 0

    profiles_genders: Dict[str, str] = {}
    distros_genders: Dict[str, str] = {}
    mgmtcls_genders: Dict[str, str] = {}

    # let's populate our dicts

    # TODO: the lists that are created here are strictly comma separated.
    # /etc/genders allows for host lists that are in the notation similar to: node00[01-07,08,09,70-71] at some point,
    # need to come up with code to generate these types of lists.

    # profiles
    for prof in api.profiles():
        # create the key
        profiles_genders[prof.name] = ""
        my_systems = api.find_system(profile=prof.name, return_list=True)
        if my_systems is None or not isinstance(my_systems, list):
            raise ValueError("Search error!")
        for system in my_systems:
            profiles_genders[prof.name] += system.name + ","
        # remove a trailing comma
        profiles_genders[prof.name] = profiles_genders[prof.name][:-1]
        if profiles_genders[prof.name] == "":
            profiles_genders.pop(prof.name, None)

    # distros
    for dist in api.distros():
        # create the key
        distros_genders[dist.name] = ""
        my_systems = api.find_system(distro=dist.name, return_list=True)
        if my_systems is None or not isinstance(my_systems, list):
            raise ValueError("Search error!")
        for system in my_systems:
            distros_genders[dist.name] += system.name + ","
        # remove a trailing comma
        distros_genders[dist.name] = distros_genders[dist.name][:-1]
        if distros_genders[dist.name] == "":
            distros_genders.pop(dist.name, None)

    # The file doesn't exist and for some reason the template engine won't create it, so spit out an error and tell the
    # user what to do.
    genders_settings_file = pathlib.Path(api.settings().genders_settings_file)
    if not genders_settings_file.exists():
        logger.info(
            'Genders configuration file doesn\'t exist! Please run: "touch %s" as root and try again.',
            api.settings().genders_settings_file,
        )
        return 1

    write_genders_file(api, profiles_genders, distros_genders, mgmtcls_genders)
    return 0
