import time


def register():
    # this pure python trigger acts as if it were a legacy shell-trigger, but is much faster.
    # the return of this method indicates the trigger type
    return "/var/lib/cobbler/triggers/install/pre/*"


def run(api, args, logger):
    objtype = args[0]   # "system" or "profile"
    name = args[1]      # name of system or profile
    ip = args[2]        # ip or "?"

    # FIXME: use the logger

    fd = open("/var/log/cobbler/install.log", "a+")
    fd.write("%s\t%s\t%s\tstart\t%s\n" % (objtype, name, ip, time.time()))
    fd.close()

    return 0
