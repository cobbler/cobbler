# Shared runtime image for both the cobblerd daemon and the HTTP/XML-RPC API (Gunicorn) role.
#
# This is *not* docker/develop/develop.dockerfile, which bundles a full supervisor/apache2/gdb/
# build-tooling development & test environment. This image installs the "cobbler" RPM (built from
# source in the builder stage below) and only the OS packages it declares as Requires -- no Apache,
# no supervisord, no build tooling. It serves both the "cobblerd" and "http-api" services in
# compose.yml/compose.dev.yml; which role a given container plays is selected purely by the
# "command:" override on that service, not by anything baked into this image.
#
# Build (from the repository root):
#   docker build -f docker/images/cobblerd/Dockerfile -t cobbler-cobblerd .

# -----------------------------------------------------------------------------------------------
# Builder stage: build the "cobbler" RPM from source on openSUSE Leap 16.0, mirroring
# docker/rpms/opensuse_leap/openSUSE_Leap16.dockerfile's build environment (kept in sync manually).
# -----------------------------------------------------------------------------------------------
FROM registry.opensuse.org/opensuse/leap:16.0 AS rpm-builder

RUN zypper ar -f https://download.opensuse.org/repositories/systemsmanagement:/cobbler:/release40/16.0/ \
      systemsmanagement:cobbler:release40 && \
    zypper --gpg-auto-import-keys refresh

# Only what "make rpms" needs -- trimmed from openSUSE_Leap16.dockerfile's list by dropping lint/dev-only
# extras (python3-pyflakes, python3-pycodestyle, supervisor, qemu-kvm) that file installs for its own
# separate purpose (interactive package-build/test container). Unlike the plan's original snippet,
# python3-Sphinx, python3-coverage and bash-completion are kept: cobbler.spec's BuildRequires (not just
# openSUSE_Leap16.dockerfile's list) actually needs all three -- rpmbuild fails dependency resolution
# without them, confirmed by a real build attempt.
RUN zypper install -y \
    git python-rpm-macros python3 python3-pip python3-devel python3-setuptools python3-setuptools_scm \
    python3-wheel rpm-build make gzip apache2 apache2-devel tftp systemd-devel cyrus-sasl-devel \
    python3-Cheetah3 python3-dnspython python3-distro python3-magic python3-ldap python3-netaddr \
    python3-schema python3-systemd python3-PyYAML python3-gunicorn libcobblersignatures \
    python3-Sphinx python3-coverage bash-completion \
    createrepo_c fence-agents rsync xorriso mtools dosfstools

WORKDIR /usr/src/cobbler
COPY . .
RUN make rpms

# -----------------------------------------------------------------------------------------------
# Final stage: install only the base "cobbler" RPM.
# -----------------------------------------------------------------------------------------------
FROM registry.opensuse.org/opensuse/leap:16.0

LABEL org.opencontainers.image.title="cobbler"
LABEL org.opencontainers.image.description="Cobbler runtime image; run as cobblerd or the HTTP/XML-RPC API (Gunicorn) via command: override."

RUN zypper ar -f https://download.opensuse.org/repositories/systemsmanagement:/cobbler:/release40/16.0/ \
      systemsmanagement:cobbler:release40 && \
    zypper --gpg-auto-import-keys refresh

# Anchored on a leading digit to exclude cobbler-tests-*/cobbler-tests-containers-*/cobbler-apache2-*/
# cobbler-nginx-*, all of which also match a naive "cobbler-*" glob. NOTE: RPMs land directly under
# RPMS/ here, not RPMS/<arch>/ as rpmbuild does by default -- "make rpms"' custom "_rpmfilename" macro
# (see the Makefile's "rpms" target) omits the "%{ARCH}/" path component that macro normally includes,
# confirmed by inspecting a real build's output layout.
COPY --from=rpm-builder /usr/src/cobbler/rpm-build/RPMS/cobbler-[0-9]*.noarch.rpm /tmp/rpms/

# --no-recommends: cobbler.spec's Recommends: (bash-completion, syslinux, grub2-*-efi, logrotate,
# python3-librepo) are irrelevant to a container that never builds bootable media locally. python3-docker
# is added explicitly (a --no-recommends install would skip a spec-level Recommends: anyway) so the
# optional process_management.docker backend stays available.
RUN zypper --no-gpg-checks install --no-recommends -y /tmp/rpms/cobbler-[0-9]*.noarch.rpm python3-docker && \
    rm -rf /tmp/rpms && zypper clean -a

# /etc/cobbler: settings.yaml and other config.
# /srv/www/cobbler: webdir (openSUSE packaging convention for cobbler.spec's %apache_dir/cobbler;
#   follow whatever "webdir" is set to in the mounted settings.yaml).
# /var/lib/cobbler: data storage (collections, triggers state, etc.) -- already seeded with
#   distro_signatures.json and misc/ by the RPM's own %post ("cobblerd setup"), so a fresh named-volume
#   mount over this path still gets seeded correctly on first "docker compose up" (Docker seeds an
#   empty named volume from the image's content at that mount point).
# /srv/tftpboot: tftproot (openSUSE packaging convention for cobbler.spec's %tftpboot_dir; follow
#   whatever "tftpboot_location" is set to in the mounted settings.yaml).
RUN mkdir -p /etc/cobbler /srv/www/cobbler /var/lib/cobbler /srv/tftpboot
# /etc/dhcpd.conf, /etc/dhcpd6.conf, /etc/named.conf: this image never installs dhcp-server/bind
# (DHCP/DNS run in the separate "dhcp"/"dns" sidecar containers -- see docker/images/dhcp/Dockerfile,
# docker/images/dns/Dockerfile), but cobbler/modules/managers/isc.py and bind.py still open() these
# exact, hardcoded paths for writing whenever manage_dhcp_v4/manage_dhcp_v6/manage_dns is enabled --
# and compose.yml/compose.dev.yml needs to share whatever lands there with the "dhcp"/"dns" sidecars
# via a volume. dhcpconf_location() resolves protocol=V6 to "/etc/dhcpd6.conf" on this image's distro
# family (see cobbler/utils/dhcpconf_location()'s "dist == \"suse\"" branch) -- without a symlink for
# it too, a v6 sync silently writes straight to this container's own ephemeral filesystem instead of
# the shared volume, never reaching the "dhcp" sidecar.
#
# Mounting a named volume directly onto a path that's a plain file (rather than a directory) relies on
# Docker's "seed a fresh volume from the image's own content at that mount point" feature -- which is a
# known-fragile, version-dependent corner of Docker's volume handling (confirmed outright broken on at
# least one real Docker Engine build: mounting *any* named volume onto *any* pre-existing file fails at
# container start, regardless of that file's content, while the identical directory-target case always
# works). Sidestep the whole class of problem: share a plain *directory* per service instead (Docker's
# directory-volume case is unambiguous and robust everywhere) and symlink the exact file path isc.py/
# bind.py expect into it. open() transparently follows symlinks, so no cobbler source changes are
# needed -- dhcpconf_location()/namedconf_location() still resolve to "/etc/dhcpd.conf"/
# "/etc/dhcpd6.conf"/"/etc/named.conf" exactly as before. The "dhcp"/"dns" sidecar images set up the
# identical symlink so both sides of each shared volume agree on where the real file actually lives.
RUN mkdir -p /etc/cobbler-dhcp /etc/cobbler-dns && \
    ln -s /etc/cobbler-dhcp/dhcpd.conf /etc/dhcpd.conf && \
    ln -s /etc/cobbler-dhcp/dhcpd6.conf /etc/dhcpd6.conf && \
    ln -s /etc/cobbler-dns/named.conf /etc/named.conf
VOLUME ["/etc/cobbler", "/srv/www/cobbler", "/var/lib/cobbler", "/srv/tftpboot", "/etc/cobbler-dhcp", "/etc/cobbler-dns"]

# XML-RPC port (settings.yaml's "xmlrpc_port"), and the HTTP/XML-RPC API's Gunicorn port. NOTE: the
# shipped default for "xmlrpc_bind_address" is 127.0.0.1; it must be changed to a non-loopback
# address in the mounted settings.yaml for the "http-api" container to reach this daemon over the
# network.
EXPOSE 25151 8000

# Health check: a real XML-RPC round trip against cobblerd's own port, calling
# CobblerXMLRPCInterface.ping() (cobbler/remote.py) -- one of the very few XML-RPC methods that
# needs no token/check_access() call, so it works before any operator/user has been configured.
# "localhost" is used deliberately instead of settings.yaml's configured xmlrpc_bind_address: this
# check runs *inside* the container itself, where the daemon is always reachable on loopback
# regardless of whether xmlrpc_bind_address has been widened to 0.0.0.0 for the "http-api"
# container's benefit. This check is only meaningful for the "cobblerd" service; the "http-api"
# service overrides this via its own healthcheck in compose.yml/compose.dev.yml.
HEALTHCHECK --interval=10s --timeout=5s --retries=6 \
    CMD python3 -c "import socket; socket.create_connection(('localhost', 25151), 2)"

# No default ENTRYPOINT/CMD -- compose.yml/compose.dev.yml sets "command:" per service (cobblerd vs.
# gunicorn cobbler.services:application) since both roles now share this one image.
