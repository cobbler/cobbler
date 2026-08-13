FROM registry.opensuse.org/opensuse/leap:15.6

LABEL org.opencontainers.image.title="cobbler-dhcp"
LABEL cobbler.io/managed-service="dhcp"

# Deliberately Leap 15.6, not 16.0: Leap 16.0's dhcp-server package is Kea-based, and
# cobbler/modules/managers/isc.py only generates classic ISC dhcpd.conf syntax, which Kea can't consume.
RUN zypper install --no-recommends -y dhcp-server && zypper clean -a

# dhcp-server ships its own default /etc/dhcpd.conf. Docker's "mount a named volume directly onto a
# path that's a plain file in the image" seeding behavior is known-fragile/version-dependent (confirmed
# outright broken on at least one real Docker Engine build, regardless of that file's content) -- rather
# than depend on it, remove the packaged default and share a plain *directory* volume instead (see
# docker/compose/base.yml's "cobbler-dhcp-config"), symlinking the exact path dhcpd/
# dhcpconf_location() expect into it. This mirrors the identical trick in docker/images/cobblerd/
# Dockerfile so both sides of the shared volume agree on where the real file lives.
RUN mkdir -p /etc/cobbler-dhcp && rm -f /etc/dhcpd.conf && ln -s /etc/cobbler-dhcp/dhcpd.conf /etc/dhcpd.conf

# ISC dhcpd (unlike most daemons) does not create its own lease database file on first start -- it
# expects /var/lib/dhcp/db/dhcpd.leases to already exist, even empty, or it exits immediately with
# "Can't open lease database ...: No such file or directory" (confirmed by a real run; the "db"
# directory itself is already packaged by dhcp-server, but the file inside it is not).
RUN mkdir -p /var/lib/dhcp/db && touch /var/lib/dhcp/db/dhcpd.leases

# The actual shared volume mount point -- /etc/dhcpd.conf itself is a symlink into this directory, set
# up above, so dhcpd (invoked below with its normal, unchanged "-cf /etc/dhcpd.conf" argument) reads
# straight through to whatever cobblerd's isc.py last wrote into the shared volume.
VOLUME ["/etc/cobbler-dhcp"]
ENTRYPOINT ["dhcpd", "-f", "-cf", "/etc/dhcpd.conf"]
