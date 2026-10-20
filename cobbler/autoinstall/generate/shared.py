"""
Module-level helper functions shared by multiple per-breed auto-installation generators. These exist because
:class:`~cobbler.autoinstall.generate.legacy.LegacyGenerator` originally implemented breed-specific metavariable
derivations (the Red Hat ``$yum_repo_stanza``/``$yum_config_stanza`` substitutions, and the Debian/Ubuntu
``install_source_directory`` substitution) that the newer per-format generators replacing it need too, without
duplicating or silently drifting from that logic.
"""

import urllib.parse
from typing import TYPE_CHECKING, Dict, Optional
from urllib.parse import SplitResult

from cobbler import utils, validate

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.items.abstract.bootable_item import BootableItem
    from cobbler.items.distro import Distro


def generate_repo_stanza(
    api: "CobblerAPI", obj: "BootableItem", is_profile: bool
) -> str:
    """
    Automatically attaches yum repos to profiles/systems in automatic installation files (template files) that
    contain the magic ``$yum_repo_stanza`` variable. This includes repo objects as well as the yum repos that are
    part of split tree installs, whose data is stored with the distro (example: RHEL5 imports).

    :param api: The API to resolve repos/settings with.
    :param obj: The profile or system to generate the repo stanza for.
    :param is_profile: ``True`` if ``obj`` is a profile, ``False`` if ``obj`` is a system.
    :return: The string with the attached yum repos.
    """
    buf = ""
    blended = utils.blender(api, False, obj)
    repos = blended.get("repos", [])

    # keep track of URLs and be sure to not include any duplicates
    included: Dict[str, int] = {}

    for repo in repos:
        # see if this is a source_repo or not
        repo_obj = api.find_repo(return_list=False, uid=repo)
        if repo_obj is not None and not isinstance(repo_obj, list):
            yumopts = ""
            for opt in repo_obj.yumopts:
                # filter invalid values to the repo statement in automatic installation files
                if opt in ["exclude", "include"]:
                    value = repo_obj.yumopts[opt].replace(" ", ",")
                    yumopts = yumopts + f" --{opt}pkgs={value}"
                elif not opt.lower() in validate.AUTOINSTALL_REPO_BLACKLIST:
                    yumopts += f" {opt}={repo_obj.yumopts[opt]}"
            if "enabled" not in repo_obj.yumopts or repo_obj.yumopts["enabled"] == "1":
                if repo_obj.mirror_locally:
                    baseurl = f"http://{blended['http_server']}/cobbler/repo_mirror/{repo_obj.name}"
                    if baseurl not in included:
                        buf += f"repo --name={repo_obj.name} --baseurl={baseurl}\n"
                    included[baseurl] = 1
                else:
                    if repo_obj.mirror not in included:
                        buf += f"repo --name={repo_obj.name} --baseurl={repo_obj.mirror} {yumopts}\n"
                    included[repo_obj.mirror] = 1
        else:
            # FIXME: what to do if we can't find the repo object that is listed?
            # This should be a warning at another point, probably not here so we'll just not list it so the
            # automatic installation file will still work as nothing will be here to read the output noise.
            # Logging might be useful.
            pass

    if is_profile:
        distro: Optional["Distro"] = obj.get_conceptual_parent()  # type: ignore
    else:
        parent = obj.get_conceptual_parent()
        distro = parent.get_conceptual_parent() if parent is not None else None  # type: ignore

    if distro is not None:
        source_repos = distro.source_repos
        count = 0
        for repo in source_repos:
            count += 1
            if not repo[1] in included:
                buf += f"repo --name=source-{count} --baseurl={repo[1]}\n"
                included[repo[1]] = 1

    return buf


def generate_config_stanza(
    api: "CobblerAPI", obj: "BootableItem", is_profile: bool
) -> str:
    """
    Generates the ``curl`` invocation used to configure ``/etc/yum.repos.d`` on the remote system, for automatic
    installation files (template files) that contain the magic ``$yum_config_stanza`` variable.

    :param api: The API to resolve settings with.
    :param obj: The profile or system to generate the config stanza for.
    :param is_profile: ``True`` if ``obj`` is a profile, ``False`` if ``obj`` is a system.
    :return: The curl command to execute to get the configuration for a system or profile, or an empty string if
        ``yum_post_install_mirror`` is disabled in the settings.
    """
    if not api.settings().yum_post_install_mirror:
        return ""

    blended = utils.blender(api, False, obj)
    autoinstall_scheme = api.settings().autoinstall_scheme
    if is_profile:
        url = f"{autoinstall_scheme}://{blended['http_server']}/cblr/svc/op/yum/profile/{obj.name}"
    else:
        url = f"{autoinstall_scheme}://{blended['http_server']}/cblr/svc/op/yum/system/{obj.name}"

    return f'curl "{url}" --output /etc/yum.repos.d/cobbler-config.repo\n'


def resolve_install_source_directory(tree: str) -> str:
    """
    Derives the ``install_source_directory`` metavariable from a distro's ``tree`` autoinstall-meta value, for
    Debian/Ubuntu Preseed-based automatic installation files. ``tree`` is set by ``cobbler import`` and holds the
    full mirror URL; only the path component is needed here.

    :param tree: The ``tree`` autoinstall-meta value (a full URL).
    :return: The path component of ``tree``.
    """
    urlparts: "SplitResult" = urllib.parse.urlsplit(tree)
    return urlparts[2]
