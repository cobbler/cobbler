FROM registry.opensuse.org/opensuse/leap:16.0

LABEL org.opencontainers.image.title="cobbler-dns"
LABEL cobbler.io/managed-service="dns"

RUN zypper install --no-recommends -y bind && zypper clean -a

# bind ships its own default /etc/named.conf. Docker's "mount a named volume directly onto a path
# that's a plain file in the image" seeding behavior is known-fragile/version-dependent (confirmed
# outright broken on at least one real Docker Engine build, regardless of that file's content) -- rather
# than depend on it, remove the packaged default and share a plain *directory* volume instead (see
# docker/compose/base.yml's "cobbler-dns-config"), symlinking the exact path named/
# namedconf_location() expect into it. This mirrors the identical trick in docker/images/cobblerd/
# Dockerfile so both sides of the shared volume agree on where the real file lives.
RUN mkdir -p /etc/cobbler-dns && rm -f /etc/named.conf && ln -s /etc/cobbler-dns/named.conf /etc/named.conf

# The actual shared volume mount point -- /etc/named.conf itself is a symlink into this directory, set
# up above, so named (invoked below with its normal, unchanged "-c /etc/named.conf" argument) reads
# straight through to whatever cobblerd's bind.py last wrote into the shared volume.
VOLUME ["/etc/cobbler-dns"]
ENTRYPOINT ["named", "-f", "-c", "/etc/named.conf"]
