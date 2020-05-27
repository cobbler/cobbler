import time


def register():
    """
    This pure python trigger acts as if it were a legacy shell-trigger, but is much faster. The return of this method
    indicates the trigger type.

    :return: Always: "/var/lib/cobbler/triggers/install/pre/\*"
    :rtype: str
    """
    return "/var/lib/cobbler/triggers/install/pre/*"


def run(api, args, logger):
    """
    The method runs the trigger, meaning this logs that an installation has started.

    The list of args should have three elements:
        - 0: system or profile
        - 1: the name of the system or profile
        - 2: the ip or a "?"

    :param api: This parameter is currently unused.
    :param args: Already described above.
    :type args: list
    :param logger: This parameter is currently unused.
    :return: A "0" on success.
    """
    objtype = args[0]
    name = args[1]
    ip = args[2]

    # FIXME: use the logger

    fd = open("/var/log/cobbler/install.log", "a+")
    fd.write("%s\t%s\t%s\tstart\t%s\n" % (objtype, name, ip, time.time()))
    fd.close()

    return 0
