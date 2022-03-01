# (c) 2008-2009
# Jeff Schroeder <jeffschroeder@computer.org>
# Michael DeHaan <michael.dehaan AT gmail>
#
# License: GPLv2+

# Post install trigger for Cobbler to send out a pretty email report that contains target information.

from builtins import str
import smtplib
from cobbler.cexceptions import CX
import cobbler.templar as templar
import cobbler.utils as utils


def register() -> str:
    """
    The mandatory Cobbler module registration hook.

    :return: Always ``/var/lib/cobbler/triggers/install/post/*``.
    """
    # this pure python trigger acts as if it were a legacy shell-trigger, but is much faster.
    # the return of this method indicates the trigger type
    return "/var/lib/cobbler/triggers/install/post/*"


def run(api, args) -> int:
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

    if objtype == "system":
        target = api.find_system(name)
    elif objtype == "profile":
        target = api.find_profile(name)
    else:
        return 1

    # collapse the object down to a rendered datastructure
    target = utils.blender(api, False, target)

    if target == {}:
        raise CX("failure looking up target")

    to_addr = settings.build_reporting_email
    if to_addr == "":
        return 0

    # add the ability to specify an MTA for servers that don't run their own
    smtp_server = settings.build_reporting_smtp_server
    if smtp_server == "":
        smtp_server = "localhost"

    # use a custom from address or fall back to a reasonable default
    from_addr = settings.build_reporting_sender
    if from_addr == "":
        from_addr = "cobbler@%s" % settings.server

    subject = settings.build_reporting_subject
    if subject == "":
        subject = "[Cobbler] install complete "

    to_addr = ",".join(to_addr)
    metadata = {
        "from_addr": from_addr,
        "to_addr": to_addr,
        "subject": subject,
        "boot_ip": boot_ip,
    }
    metadata.update(target)

    with open("/etc/cobbler/reporting/build_report_email.template") as input_template:
        input_data = input_template.read()

        message = templar.Templar(api).render(
            input_data, metadata, None
        )

        sendmail = True
        for prefix in settings.build_reporting_ignorelist:
            if prefix != "" and name.lower().startswith(prefix):
                sendmail = False

        if sendmail:
            # Send the mail
            # FIXME: on error, return non-zero
            server_handle = smtplib.SMTP(smtp_server)
            server_handle.sendmail(from_addr, to_addr.split(","), message)
            server_handle.quit()

    return 0
