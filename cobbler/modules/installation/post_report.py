"""
Post install trigger for Cobbler to send out a pretty email report that contains target information.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2008-2009 Bill Peck <bpeck@redhat.com>
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import smtplib
from builtins import str
from typing import TYPE_CHECKING, List, Optional

from cobbler import enums, utils
from cobbler.cexceptions import CX

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.items.template import Template


def register() -> str:
    """
    The mandatory Cobbler module registration hook.

    :return: Always ``/var/lib/cobbler/triggers/install/post/*``.
    """
    # this pure python trigger acts as if it were a legacy shell-trigger, but is much faster.
    # the return of this method indicates the trigger type
    return "/var/lib/cobbler/triggers/install/post/*"


def run(api: "CobblerAPI", args: List[str]) -> int:
    """
    This is the mandatory Cobbler module run trigger hook.

    :param api: The api to resolve information with.
    :param args: This is an array with three elements.
                 0: "system" or "profile"
                 1: name of target or profile
                 2: ip or "?"
    :return: ``0`` or ``1``.
    :raises CX: Raised if the blender result is empty.
    """
    # FIXME: make everything use the logger

    settings = api.settings()

    # go no further if this feature is turned off
    if not settings.build_reporting_enabled:
        return 0

    objtype = args[0]
    name = args[1]
    boot_ip = args[2]

    if objtype not in ("system", "profile"):
        return 1
    target = api.find_items(what=objtype, criteria={"name": name})

    if target is None or isinstance(target, list):
        raise ValueError("Error retrieving system/profile.")

    # collapse the object down to a rendered datastructure
    target_dict = utils.blender(api, False, target)

    if target_dict == {}:
        raise CX("failure looking up target")

    to_addr = settings.build_reporting_email
    if len(to_addr) < 1:
        return 0

    # add the ability to specify an MTA for servers that don't run their own
    smtp_server = settings.build_reporting_smtp_server
    if smtp_server == "":
        smtp_server = "localhost"

    # use a custom from address or fall back to a reasonable default
    from_addr = settings.build_reporting_sender
    if from_addr == "":
        from_addr = f"cobbler@{settings.server}"

    subject = settings.build_reporting_subject
    if subject == "":
        subject = "[Cobbler] install complete "

    to_addr_str = ",".join(to_addr)
    metadata = {
        "from_addr": from_addr,
        "to_addr": to_addr_str,
        "subject": subject,
        "boot_ip": boot_ip,
    }
    metadata.update(target_dict)

    search_result = api.find_template(
        True, False, tags=enums.TemplateTag.REPORTING_BUILD_EMAIL.value
    )
    if search_result is None or not isinstance(search_result, list):
        raise TypeError(
            "Search result for the build reporting Template must of of type list!"
        )
    build_reporting_template: Optional["Template"] = None
    for template in search_result:
        if enums.TemplateTag.ACTIVE.value in template.tags:
            build_reporting_template = template
            break
        if enums.TemplateTag.DEFAULT.value in template.tags:
            build_reporting_template = template

    if build_reporting_template is None:
        raise ValueError(
            "Neither specific nor default build reporting template could be found inside Cobbler!"
        )

    message = api.templar.render(build_reporting_template.content, metadata, None)

    sendmail = True
    for prefix in settings.build_reporting_ignorelist:
        if prefix != "" and name.startswith(prefix):
            sendmail = False

    if sendmail:
        # Send the mail
        # FIXME: on error, return non-zero
        server_handle = smtplib.SMTP(smtp_server)
        server_handle.sendmail(from_addr, to_addr, message)
        server_handle.quit()

    return 0
