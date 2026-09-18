.. _docker-deployment:

*****************************
Container Deployment (Docker)
*****************************

Cobbler can be run as a set of separate containers instead of a single traditional host install: a ``cobblerd``
container (the daemon -- XML-RPC API, sync, templating, ...) and an ``http-api`` container (Gunicorn serving
``cobbler.services:application``, i.e. ``/cblr/svc``, ``/httpboot`` and ``/images``), fronted by a reverse proxy for
HTTP routing. Both containers run from the *same* image, built from the ``cobbler`` RPM; which role a given
container plays is selected purely by its ``command:`` override in the Compose file, not by anything baked into the
image itself. An optional ``web`` container can additionally be enabled to serve the actual Cobbler Web UI -- see
`Web UI`_ below; despite the similar name, it is unrelated to ``http-api`` (which was itself named ``web`` in an
earlier revision of this stack, before being renamed to free up the name for the real UI).

A reference/example Compose stack implementing this is shipped at the repository root as two core files, both
built around the single shared runtime image at ``docker/images/cobblerd/Dockerfile``:

* ``compose.yml`` -- **production**, the default a normal user reaches for. ``cobblerd``/``http-api`` pull the
  published ``ghcr.io/cobbler/cobblerd`` image; nothing builds locally.
* ``compose.dev.yml`` -- **development**. Identical apart from ``cobblerd``/``http-api``, which build from
  source instead of pulling.

Optional services (the ``web`` UI, ``cobbler-tftp``, and the DHCP/DNS sidecars) are not defined inline in either
core file -- they live in their own files under ``docker/compose/`` and are pulled in via Compose's ``include:``
directive, so enabling one is a matter of uncommenting its ``include:`` entry in whichever core file you're using.
These files are deliberately minimally commented; this page is the source of truth for the reasoning behind
every volume, label and environment variable.

Two mechanical details of ``include:`` matter if you're editing these files: Compose errors if the same
top-level ``networks:``/``volumes:``/``configs:`` name is declared in more than one file across the whole
include graph, which is why they're declared exactly once, in ``docker/compose/base.yml``; and a relative path
*inside* an included file (e.g. a ``build.context``) resolves relative to that file's own directory, not the
root file's -- ``docker/compose/dhcp.dev.yml``/``dns.dev.yml``'s ``build.context: ../..`` is relative to
``docker/compose/``, resolving to the repository root.

This is *not* the same thing as ``docker/develop`` (the interactive development container), ``docker/tests`` (the
package-build/test harness), or ``docker/compose.yml`` (the RPM/DEB package-build/test harness, an unrelated file
despite the similar name -- note it lives under ``docker/``, not at the repository root). Those exist to build and
test Cobbler itself; the files described on this page exist to *run* Cobbler.

Quick start:

.. code-block:: shell

    docker compose -f compose.yml up -d
    curl http://localhost/cobbler_api        # -> routed to cobblerd's XML-RPC server
    curl http://localhost/httpboot/          # -> routed to http-api's Gunicorn app
    curl http://localhost/                   # -> routed to the web UI (if enabled)

Building from source instead (development) is the same, using ``compose.dev.yml`` instead:

.. code-block:: shell

    docker compose -f compose.dev.yml up --build -d

Neither file sets a fixed Compose project name -- Compose derives one from the containing directory by
default, so both would otherwise collide on the same "cobbler" project name. If you need ``compose.yml`` and
``compose.dev.yml`` running side by side from the same checkout, pass distinct ``-p``/``COMPOSE_PROJECT_NAME``
values explicitly.

Images
######

``docker/images/cobblerd/Dockerfile`` builds a single shared, openSUSE-Leap-16.0-based runtime image for both roles:

* A builder stage builds the ``cobbler`` RPM from source (mirroring
  ``docker/rpms/opensuse_leap/openSUSE_Leap16.dockerfile``'s build environment), and the final stage installs only
  the base ``cobbler`` package -- explicitly excluding the ``cobbler-apache2``/``cobbler-nginx`` subpackages (the
  webserver-integration packages split out of the base package) and the ``cobbler-tests``/
  ``cobbler-tests-containers`` packages. The resulting image genuinely has no Apache/httpd installed.
* It declares volumes for ``/etc/cobbler``, ``/srv/www/cobbler``, ``/var/lib/cobbler`` and ``/srv/tftpboot``, and
  exposes both the XML-RPC port (``25151``) and the HTTP/XML-RPC API's Gunicorn port (``8000``).
* The image ships no default ``ENTRYPOINT``/``CMD``. ``compose.yml``/``compose.dev.yml`` instead sets ``command:``
  per service: the ``cobblerd`` service runs ``cobblerd -F``, while the ``http-api`` service overrides this with
  ``command: ["gunicorn", "cobbler.services:application", "--bind", "0.0.0.0:8000"]``. Round 1's rationale for a
  separately-minimized API image (avoiding pulling in ``cobbler.api``/items/collections/modules just to run
  Gunicorn) no longer applies once installation is RPM-package-based rather than pip-based: there is no lighter
  subset of the package to install for just the ``http-api`` role, so both roles simply share this one image.
* ``distro_signatures.json`` and ``/var/lib/cobbler/misc`` are seeded into the image directly by the RPM's own
  install step (``cobblerd setup``, run as part of building the package) -- the Dockerfile itself does no manual
  seeding. A fresh named-volume mount over ``/var/lib/cobbler`` still gets this content on first
  ``docker compose up`` (Docker seeds an empty named volume from the image's content at that mount point).

``compose.yml`` never builds this image -- it only pulls ``ghcr.io/cobbler/cobblerd:latest``. To build it yourself,
either run ``docker build -f docker/images/cobblerd/Dockerfile -t cobbler-cobblerd .`` from the repository root
directly, or use ``compose.dev.yml``, which builds it as part of ``docker compose -f compose.dev.yml up --build``.

Settings overrides
###################

``docker/compose/base.yml`` (included by both ``compose.yml`` and ``compose.dev.yml``) injects a single shared
``settings.yaml`` (via a Compose ``config:``) into both ``cobblerd`` and ``http-api``. It only lists the keys that
differ from ``cobbler.settings.Settings``'s built-in
Python defaults (see ``cobbler/settings/__init__.py``); every other setting keeps its normal default. This works
because ``Settings.from_dict()`` (called from ``cobbler.api.CobblerAPI``'s settings generation) starts from a
fully-populated ``Settings()`` object and overlays only the keys present in the file on top of it.

.. important::

   ``modules`` is given in full in that file, not as a partial override. ``from_dict()`` replaces each top-level key
   *wholesale* rather than deep-merging nested dicts, so a partial ``modules: {httpd: ..., tftpd: ...}`` override
   would silently blank out the ``authentication``/``authorization``/``dns``/``dhcp``/``process_management``/
   ``serializers`` choices instead of leaving them at their defaults. Any edit to one ``modules`` sub-key must repeat
   the rest of the block.

The ``modules`` block sets:

* ``authentication.module: "authentication.configfile"`` with ``hash_algorithm: "sha3_512"`` -- the standard
  file-backed authentication backend, unchanged from Cobbler's own default choice of backend but pinned to a modern
  hash algorithm.
* ``authorization.module: "authorization.allowall"`` -- the permissive default; tighten this for a real deployment.
* ``dns.module: "managers.bind"`` and ``dhcp.module: "managers.isc"`` -- the traditional BIND/ISC-dhcpd managers,
  unchanged from Cobbler's own defaults.
* ``httpd``/``tftpd`` -- see `Dynamic HTTP and TFTP serving`_ below.
* ``process_management`` -- see `Process management and DHCP/DNS sidecar containers`_ below.
* ``serializers.module: "serializers.file"`` -- the default flat-file storage backend, unchanged.

One setting is deliberately **not** overridden: ``server`` (defaults to ``127.0.0.1``) is the hostname/IP PXE
clients use to reach Cobbler for templates/files. Set it to this stack's externally-reachable address (e.g. the
reverse proxy host's IP/DNS name) -- this is environment-specific and out of scope for the container-to-container
wiring described on this page.

Required volumes
#################

``cobblerd`` needs read-write access to:

* ``/etc/cobbler`` -- ``settings.yaml`` and other runtime configuration (``users.digest``/``users.conf``, etc).
* ``/var/lib/cobbler`` -- collections (distros/profiles/systems/...), triggers state, the signatures cache.
* ``/srv/www/cobbler`` -- webdir (templates, misc, images, ...). This follows ``webdir``, whatever it is set to.
* ``/srv/tftpboot`` -- the TFTP root. This follows ``tftpboot_location``, whatever it is set to.

``http-api`` only ever needs read-only access to the webdir and TFTP-root content (so its ``/cblr/svc``, ``/httpboot``
and ``/images`` routes have something to read), plus a read-only copy of ``/etc/cobbler/settings.yaml`` for the
``xmlrpc_port``/``xmlrpc_host`` values it needs to reach ``cobblerd``.

The shipped ``docker/images/cobblerd/Dockerfile`` image follows the openSUSE packaging convention of rooting these
under ``/srv`` (``/srv/www/cobbler``, ``/srv/tftpboot``), which does **not** match Cobbler's own Python-level
defaults (``/var/www/cobbler``, ``/var/lib/tftpboot``). ``docker/compose/base.yml`` overrides ``webdir`` and
``tftpboot_location`` in its injected ``settings.yaml`` to match the image; if you build your own image with
different paths, override these two settings accordingly.

On an SELinux-enforcing host (e.g. openSUSE/Fedora/RHEL, the same distro family these images target), the named
volumes shared between ``cobblerd`` (read-write) and ``http-api`` (read-only) are mounted with the ``:z`` suffix so
Docker relabels them with a shared SELinux content label. Without it, the two containers' concurrent,
differing-mode mounts of the same volume can race during labeling and leave ``cobblerd`` unable to stat/create its
own directories, failing startup with a plain ``PermissionError``. This is a no-op (and harmless) on hosts where
SELinux isn't enforcing.

XML-RPC host/bind settings
###########################

Splitting the daemon and the HTTP/XML-RPC API application into separate containers only works because of two
settings added for this purpose:

* ``xmlrpc_bind_address`` (default ``"127.0.0.1"``, overridable via the ``COBBLER_XMLRPC_BIND_ADDRESS`` environment
  variable) controls what address ``cobblerd`` binds its XML-RPC server to. The Python-level default is
  loopback-only, which a separate ``http-api`` container could never reach; the compose stack sets this to ``"0.0.0.0"``
  on ``cobblerd`` so the ``http-api`` container can dial in over the shared Docker network.
* ``xmlrpc_host`` (default ``"127.0.0.1"``, overridable via the ``COBBLER_XMLRPC_HOST`` environment variable)
  controls what host/address the ``http-api`` application (``cobbler/services/svc.py`` and ``cobbler/services/files.py``)
  dials to reach ``cobblerd``. The compose stack sets this to ``"cobblerd"`` (the Compose service name) on ``http-api``.

Both are ordinary entries under the top level of ``settings.yaml`` (see :ref:`settings-ref`); the environment
variables only exist so the *same* ``settings.yaml`` can be shared, read-only, between both containers while each
one still gets the value it individually needs.

``cobblerd`` is never published to the host directly in the reference stack -- only Traefik's port 80 is; binding
``xmlrpc_bind_address`` to ``0.0.0.0`` is only safe to the extent that nothing outside the Docker network can reach
that port.

Traefik and routing
#####################

``docker/compose/base.yml`` runs `Traefik <https://traefik.io/traefik/>`_ as the stack's single entry point on
host port 80, using Traefik's Docker provider (``--providers.docker=true``, with
``--providers.docker.exposedbydefault=false`` so a container only gets routed once it carries an explicit
``traefik.enable=true`` label). Traefik auto-detects each labeled container's address on the shared ``cobbler``
bridge network -- every service has exactly one network attached, so no ``traefik.docker.network`` label is
needed to disambiguate.

Each backend's Traefik labels declare a router rule and, where needed, a ``stripprefix`` middleware:

* ``cobblerd`` is matched on ``PathPrefix(`/cobbler_api`)``, but its raw XML-RPC server (a plain
  ``SimpleXMLRPCRequestHandler``, see ``cobbler/remote.py``) only ever answers on ``/`` (and ``/RPC2``) --
  ``cobbler-api-strip`` strips the ``/cobbler_api`` prefix before the request reaches it.
* ``http-api`` is matched on ``PathPrefix(`/cblr`) || PathPrefix(`/httpboot`) || PathPrefix(`/images`)`` (Traefik
  v3's matchers take exactly one argument each -- the v2 multi-value ``PathPrefix`` syntax was removed, hence
  the ``||``). Gunicorn expects the ``/cblr/svc`` prefix already stripped (historically done by Apache's
  ``ProxyPass``), but ``/httpboot``/``/images`` must arrive un-stripped -- so ``cobbler-svc-strip`` only strips
  ``/cblr/svc``, chained onto the router via ``middlewares=cobbler-svc-strip``.
* ``web`` (see `Web UI`_ below) matches the catch-all ``PathPrefix(`/`)`` at the lowest priority in the stack, so
  it only ever receives requests the two more specific routers above don't match. The ``cobbler-api`` router also
  carries a CORS middleware for this service's benefit -- see `Web UI`_ for why.
* ``http-api`` also carries a second router, ``cobbler-sso``, matched on ``PathPrefix(`/sso_login`)`` and pointed
  at the same ``cobbler-http-api`` backend service (no separate ``loadbalancer.server.port`` needed -- it's the
  same Gunicorn process). It carries its own dedicated CORS middleware, ``cobbler-sso-cors``, rather than reusing
  ``cobbler-api-cors`` -- see `Kerberos/GSSAPI Single Sign-On (native)`_ below for why the two endpoints need
  different CORS treatment even though both are called cross-origin.

Traefik needs its own read-only mount of the host's Docker socket to watch for labeled containers -- the same
class of trust boundary as ``process_management.docker``'s socket mount discussed above: even read-only, it
grants Traefik root-equivalent control over the **entire host Docker daemon**. This is accepted here as a
deliberate trade-off for local, label-based service discovery.

On an SELinux-enforcing host, the Docker socket's own SELinux context (typically ``container_var_run_t``) is
not one a bind-mounted volume can be transparently relabeled to (unlike the named volumes described above,
which use the ``:z`` suffix for that) -- SELinux denies Traefik's container access to the socket outright,
surfacing as a plain "permission denied" error talking to the socket rather than an SELinux-specific one.
``docker/compose/base.yml`` sets ``security_opt: [label:disable]`` on the ``traefik`` service to work around
this, turning off SELinux label confinement for that one container instead of relabeling the socket itself.

The reference stack pins ``traefik:v3.6``. Older ``v3.3`` was found, while testing this stack, to negotiate a
stale Docker API version against some newer Docker Engine releases, failing with "client version ... is too
old" errors when talking to the socket; ``v3.6`` does not have this problem.

Dynamic HTTP and TFTP serving
##############################

By default Cobbler copies imported distro trees into ``webdir``/``distro_mirror`` and materializes boot files under
``tftpboot_location``. In a container deployment it is usually preferable to serve content directly from wherever
it already lives instead of duplicating it into a (potentially large) writable volume:

* ``modules.httpd.module: "managers.dynamic_httpd"`` serves a distro's source tree on demand, straight from its
  original location, through the ``http-api`` container's ``/cblr/svc/tree`` route, instead of copying it into
  ``webdir``/``distro_mirror``.
* ``modules.tftpd.module: "managers.dynamic_tftp"`` skips writing boot files into ``tftpboot_location`` entirely;
  something else (for example the separately-maintained
  `cobbler-tftp <https://github.com/cobbler/cobbler-tftp>`_ daemon, enabled by default via ``docker/compose/tftp.yml``,
  included by both ``compose.yml`` and ``compose.dev.yml``) has to actually answer TFTP (UDP/69) requests by calling
  back into ``cobblerd``'s XML-RPC API.

``docker/compose/base.yml`` selects both of these by default in its injected settings, and ``compose.yml``/
``compose.dev.yml`` bind-mount a read-only ``distro-sources`` directory into both ``cobblerd`` and ``http-api``
for this purpose, so a large distro tree can be served without ever being copied into a Docker volume.

.. warning::

   The traditional copying managers (``managers.in_httpd``/``managers.in_tftpd``) are **not** supported by this
   reference stack, even though ``cobblerd`` would happily copy content into ``webdir``/``distro_mirror`` if you
   selected them and pointed ``webdir``/``tftpboot_location`` at a writable volume. The problem is on the serving
   side: Apache historically served that copied webdir content back out at ``/cblr`` (the non-``/svc`` paths),
   ``/cobbler`` and ``/cobbler_track``, but the Gunicorn ``http-api`` application only implements ``/cblr/svc``,
   ``/httpboot`` and ``/images`` (see ``cobbler/services/__init__.py``), and ``compose.yml``/``compose.dev.yml``'s
   Traefik router for ``http-api`` only matches ``/cblr``, ``/httpboot``, ``/images`` -- there is no route at all for
   ``/cobbler`` or ``/cobbler_track``. Content copied into the volume by ``in_httpd``/``in_tftpd`` would therefore
   sit there unreachable over HTTP in this reference stack. Using either manager requires adding your own Traefik
   route(s) and a way to actually serve that content, neither of which this plan provides -- stick with
   ``managers.dynamic_httpd``/``managers.dynamic_tftp`` (the defaults above) unless you build that yourself.

Manually-created distros (bypassing ``cobbler import``)
##########################################################

Everything above happens automatically only inside ``cobbler import``: that is the only code path that sets a
distro's ``source_tree_path`` for you. If you create ``Distro``/``Profile`` objects yourself -- for example
directly through the XML-RPC API, without ever calling ``cobbler import`` -- ``source_tree_path`` stays empty
unless you set it yourself, and ``/cblr/svc/tree/<distro_name>/...`` returns ``404 Not Found`` for that distro even
though ``managers.dynamic_httpd`` is selected.

To make ``/cblr/svc/tree`` work for a manually-created distro:

1. Place the distro's extracted tree (or a mount of it) somewhere under the host directory bind-mounted at
   ``/srv/distro-sources`` (``${COBBLER_DISTRO_SOURCE_DIR:-./distro-sources}``, see `Settings overrides`_ above).
   This is the only location that resolves to the *same* path inside both the ``cobblerd`` and ``http-api``
   containers. Content placed anywhere ``http-api`` doesn't also have mounted -- for example under
   ``/var/lib/cobbler``, which is a volume only ``cobblerd`` has -- looks fine when ``cobblerd`` resolves the
   distro's metadata over XML-RPC, but ``http-api`` still 404s when it tries to actually open the file, since the
   path simply doesn't exist inside its own container.
2. Set the distro's ``source_tree_path`` to that same path, as seen *inside the containers*
   (``/srv/distro-sources/<something>``, not the host-side path you used to place the files there):

   .. code-block:: python

       import xmlrpc.client

       remote = xmlrpc.client.Server("http://localhost/cobbler_api", allow_none=True)
       token = remote.login("cobbler", "cobbler")
       did = remote.get_distro_handle("example_distro")
       remote.modify_distro(did, ["source_tree_path"], "/srv/distro-sources/example_distro", token)
       remote.save_distro(did, True, True, "bypass", token)

3. Verify: ``curl http://localhost/cblr/svc/tree/example_distro/`` should return a directory listing instead of
   ``404 Not Found``.

.. note:: ``http-api`` caches the distro-name-to-``source_tree_path`` lookup for up to 30 seconds (see
          ``CACHE_TTL_SECONDS`` in ``cobbler/services/files.py``) to avoid an XML-RPC round trip per served file.
          A ``source_tree_path`` you just set may not be picked up immediately -- no container restart is needed,
          just retry after the cache entry expires.

Process management and DHCP/DNS sidecar containers
#####################################################

Managing DHCP/DNS as local processes (systemd services, or processes supervised by supervisord) does not make sense
once ``cobblerd`` runs in its own minimal container with no DHCP/DNS daemon inside it. The
``modules.process_management.module`` setting controls how Cobbler restarts these services after a
``cobbler sync``:

* ``"auto"`` (the shipped default) -- auto-detects whether ``cobblerd`` is running inside a container (see
  ``cobbler/modules/process_management/detection.py``'s ``is_containerized()``) and resolves to
  ``"process_management.docker"`` if so, or ``"process_management.service"`` otherwise. Outside a container this
  reproduces today's traditional behavior byte-for-byte, so a containerized ``cobblerd`` picks up the Docker
  backend with no explicit override needed, while a non-containerized install keeps working unchanged.
* ``"process_management.service"`` -- today's behavior, unchanged: restart a local systemd/supervisord-managed
  process. Explicitly setting this always wins, even inside a container -- ``"auto"`` is the only value affected
  by container detection.
* ``"process_management.docker"`` -- an opt-in alternative that restarts a DHCP/DNS **sidecar container** instead
  of a local process. It requires the optional ``docker`` Python extra (``pip install cobbler[docker]``) and
  mounting the host's Docker socket into the ``cobblerd`` container. Like ``"process_management.service"``, an
  explicit setting here is never overridden by container detection.

When ``process_management.docker`` is selected, ``cobblerd`` (see ``cobbler/modules/process_management/docker.py``)
picks the container to restart purely by Docker label: it looks for exactly one running container carrying the
label ``cobbler.io/managed-service=<value>``, where ``<value>`` is one of ``dhcp``, ``dns`` or ``dnsmasq``. The
mapping from Cobbler's internal service names (``dhcpd``, ``dhcpd4``, ``dhcpd6``, ``named``, ``dnsmasq``) to those
label values is configurable via ``modules.process_management.docker_service_labels``, whose default is:

.. code-block:: yaml

    modules:
      process_management:
        module: "auto"
        docker_socket_path: "/var/run/docker.sock"
        docker_service_labels:
          dhcpd: "dhcp"
          dhcpd4: "dhcp"
          dhcpd6: "dhcp"
          named: "dns"
          dnsmasq: "dnsmasq"

``modules.process_management.docker_socket_path`` (default ``/var/run/docker.sock``) is the path, inside the
``cobblerd`` container, of the Docker Engine API Unix socket to connect to. The Docker Engine API connection is
always local-only (a Unix socket) -- this module never connects to a remote or TLS-secured Docker host, by design.

If zero containers or more than one container carry the expected label, this is treated as a hard error (logged and
reported as a non-zero return from the restart call), never a silent no-op and never a guess at which container to
restart. There is no retry loop and no fallback.

``compose.yml``/``compose.dev.yml`` ship a commented-out example of mounting the socket into ``cobblerd``, plus
commented-out ``include:`` entries pulling in ``docker/compose/dhcp.yml``/``dns.yml``/``dnsmasq.yml``
(``dhcp.dev.yml``/``dns.dev.yml`` in ``compose.dev.yml``, which build from source instead of pulling) -- sidecar
service definitions carrying the matching labels. Read the comments in those files before enabling any of it, in
particular the trust-boundary warning below. The ``dhcp``/``dns`` sidecars' config-sharing volumes (described in
the next paragraph) are a real, working mechanism, verified end-to-end with an actual cross-container config
write/read test -- not illustrative placeholders. The ``dnsmasq`` example remains illustrative only (see
`Known limitations and non-goals`_ for the one genuine remaining caveat with the ``dhcp``/``dns`` sidecars).

The ``cobbler-dhcp-config``/``cobbler-dns-config`` volumes that ``cobblerd`` and the sidecars would share are
mounted at plain directories (``/etc/cobbler-dhcp``, ``/etc/cobbler-dns``), not directly at ``/etc/dhcpd.conf`` or
``/etc/named.conf``. Both images instead create those config files as symlinks into the mounted directory
(``cobbler/utils/dhcpconf_location()``/``namedconf_location()`` still resolve to the plain path; ``open()`` follows
the symlink transparently). This sidesteps Docker's fragile, version-dependent behavior for seeding a named volume
mounted directly onto a path that is a plain file in the image -- confirmed outright broken (container creation
fails unconditionally) on at least one real Docker Engine build, regardless of whether that file is empty or has
real content. Mounting onto a directory instead is the unambiguous, universally-supported case.

``named.conf`` alone isn't enough for the ``dns`` sidecar to actually serve anything, though: ``bind.py`` also
renders the zone files it references to ``bind_zonefile_path`` (``/var/lib/named`` by default), a directory
separate from ``/etc/cobbler-dns``. The ``cobbler-dns-zones`` volume, mounted at ``/var/lib/named`` on both
``cobblerd`` (read-write) and the ``dns`` sidecar (read-only), carries that zone data across -- the same
plain-directory-volume approach as ``cobbler-dns-config``, without needing a symlink trick since
``/var/lib/named`` is already a directory in both images, not a single file. ``docker/compose/base.yml`` also
pins ``bind_zonefile_path: "/var/lib/named"`` explicitly in the ``cobbler-settings`` config so it can't silently
drift out of sync with this mount path.

The ``dhcp`` sidecar additionally runs with ``network_mode: host`` instead of joining the ``cobbler`` bridge
network like everything else in the stack -- ISC ``dhcpd`` needs real L2 broadcast visibility to serve DHCP
clients, which a NAT'd bridge network does not provide. The ``dns`` sidecar has no such requirement and stays
on the ``cobbler`` network.

.. warning::

   Mounting the Docker socket into ``cobblerd`` -- even read-only -- grants ``cobblerd`` root-equivalent control
   over the **entire host Docker daemon**, not just the ``dhcp``/``dns``/``dnsmasq``-labeled sibling containers it
   is meant to restart. Anyone who can reach ``cobblerd``'s XML-RPC API (or exploit it) can, via this socket, create
   a new privileged container, bind-mount arbitrary host paths into it, or inspect/stop/remove *any* container on
   the host. Mounting it read-only only prevents the socket file itself from being replaced or deleted -- it does
   not restrict which Docker Engine API calls can be made over it. This is accepted here only as a deliberate
   trade-off for local-only sidecar management; do not extend it to a remote or TLS-secured Docker endpoint.

Health checks
#############

The ``http-api`` container exposes a ``/healthz`` endpoint (``cobbler/services/files.py``'s ``healthz_application``)
that performs a real XML-RPC ``ping()`` round trip against ``cobblerd`` and returns ``200 OK`` if it succeeds or
``503 Service Unavailable`` otherwise. The ``cobblerd`` container's own health check performs an equivalent XML-RPC
round trip directly against its own port. Since both roles now share one image, ``docker/images/cobblerd/Dockerfile``
only declares a ``HEALTHCHECK`` suited to the ``cobblerd`` role (a plain TCP connect to the XML-RPC port);
``compose.yml``/``compose.dev.yml``'s ``http-api`` service overrides this with its own ``healthcheck:`` hitting
``/healthz`` instead, since a bare TCP connect to the Gunicorn port would only prove Gunicorn is listening, not that
it can actually reach ``cobblerd``. Both are used for ``depends_on: condition: service_healthy``.

``/healthz`` is **not** routed externally by Traefik in the reference stack -- only ``/cblr``, ``/httpboot``,
``/images`` (routed to ``http-api``) and ``/cobbler_api`` (routed to ``cobblerd``) are. The health check is
container-internal only: it is consumed by Docker's own ``HEALTHCHECK``/``depends_on`` machinery, not reachable
from outside the Compose network.

Web UI
######

``docker/compose/web.yml`` -- included by both ``compose.yml`` and ``compose.dev.yml`` -- ships an optional
``web`` service running the actual `Cobbler Web UI <https://github.com/cobbler/cobbler-web>`_ -- a
separately-maintained Angular application, published as ``ghcr.io/cobbler/cobbler-web`` on GHCR and
built/versioned independently of the ``cobbler`` package itself. It is **not** the same thing as this stack's
``http-api`` service: an earlier revision of this reference stack named the Gunicorn HTTP/XML-RPC-API container
``web``, and that service was renamed to ``http-api`` specifically to free up the ``web`` name for this real UI.
If you are looking for the code that serves ``/cblr/svc``, ``/httpboot`` and ``/images``, that is ``http-api``,
not ``web``.

Unlike ``http-api``, the ``web`` UI does no server-side proxying at all: it is a static Angular application served by
``nginx-unprivileged`` on port ``8080``, and every XML-RPC call it makes to Cobbler is issued directly from the end
user's *browser* to ``/cobbler_api``. Two consequences follow from that:

* **The UI needs to be told where the API is.** It reads ``/cobbler_api``'s URL at container start from a
  runtime-mounted ``/config/app-config.json`` (the image's own entrypoint script copies it into the webroot -- there
  is no build-time environment variable for this). ``docker/compose/web.yml`` supplies this content inline via a
  Compose ``configs:`` entry (no separate tracked file at the repository root):

  .. code-block:: yaml

      configs:
        cobbler-web-app-config:
          content: |
            {"cobblerUrls": ["http://localhost/cobbler_api"]}
      services:
        web:
          configs:
            - source: cobbler-web-app-config
              target: /config/app-config.json

  The shipped ``"http://localhost/cobbler_api"`` value is a *local-development-only* default: it only resolves
  correctly when the browser and the Docker host are the same machine. Before using the ``web`` service anywhere
  else, edit the ``content:`` block in ``docker/compose/web.yml`` (or supply a Compose override file overriding
  just this config's ``content:``) to your deployment's real, externally-reachable hostname, e.g.:

  .. code-block:: yaml

      content: |
        {"cobblerUrls": ["https://cobbler.example.org/cobbler_api"]}

* **The API needs CORS headers.** Because the browser -- not a server-side process -- is the one making the
  cross-origin request, ``cobblerd``'s XML-RPC endpoint must answer with ``Access-Control-Allow-Origin`` (and related)
  headers, which its raw ``SimpleXMLRPCRequestHandler`` (``cobbler/remote.py``) never sends on its own.
  ``compose.yml``/``compose.dev.yml`` handle this with a Traefik middleware chained onto the existing
  ``cobbler-api`` router, rather than a code change:

  .. code-block:: yaml

      - "traefik.http.middlewares.cobbler-api-cors.headers.accessControlAllowOriginList=*"
      - "traefik.http.middlewares.cobbler-api-cors.headers.accessControlAllowMethods=GET,POST,OPTIONS"
      - "traefik.http.middlewares.cobbler-api-cors.headers.accessControlAllowHeaders=content-type"
      - "traefik.http.middlewares.cobbler-api-cors.headers.accessControlMaxAge=100"
      - "traefik.http.routers.cobbler-api.middlewares=cobbler-api-strip,cobbler-api-cors"

  ``accessControlAllowHeaders`` matters as much as the origin/methods headers above: cobblerd's XML-RPC endpoint
  requires ``Content-Type: text/xml``, which is not a CORS-"simple" content type, so browsers send a preflight
  ``OPTIONS`` request (``Access-Control-Request-Headers: content-type``) before the real one. Without a matching
  ``Access-Control-Allow-Headers`` response, that preflight fails and the browser blocks the real request outright,
  even though the origin/method headers look correct.

  If you front ``/cobbler_api`` with your own reverse proxy instead of this reference stack's Traefik, you need to
  replicate the equivalent CORS headers yourself, or the UI's browser-side requests will be blocked by the browser's
  own CORS enforcement even though ``cobblerd`` itself answered the request successfully.

The ``web`` service's Traefik router matches the catch-all root path (``PathPrefix(`/`)``) at the lowest priority in
the stack (``priority=1``), so it only ever receives requests that ``cobbler-api``'s and ``cobbler-http-api``'s more
specific routes (``/cobbler_api``, ``/cblr``, ``/httpboot``, ``/images``) don't match.

.. note::

   As of this writing, the ``cobbler-web`` project's ``v1.0.0`` release may not yet be fully compatible with this
   version of Cobbler (4.0.0) -- the two projects are versioned and released independently. The compose wiring,
   Traefik routing and CORS headers described above are independent of that and can be verified purely at the HTTP
   level even if the UI application itself does not yet fully work end-to-end against a given Cobbler version.

Kerberos/GSSAPI Single Sign-On (native)
########################################

``cobbler/services/sso.py`` adds a ``/sso_login`` endpoint to the same Gunicorn WSGI app that already serves
``/cblr/svc``, ``/httpboot`` and ``/images`` -- i.e. it runs inside the ``http-api`` container, on the same
process, with no extra container or service to deploy. This is a *different* mechanism from the release33
Apache/``mod_auth_gssapi`` bridge (``svc/sso_login.py`` there, fronted by an Apache ``<Location>`` block): this
branch's ``http-api`` container has no Apache in front of it at all (see `Images`_ above), so ``sso.py`` performs
the SPNEGO/Kerberos negotiation itself, natively in Python, using the ``gssapi`` library. Both approaches share the
same backend: a successful negotiation is exchanged for a normal Cobbler XML-RPC session token via
``cobbler.modules.authentication.passthru`` and the shared secret cobblerd writes to
``/var/lib/cobbler/web.ss`` -- only the front door (Apache module vs. native Python) differs.

Enabling it end-to-end requires *all of the following steps* -- doing only the keytab/``KRB5_KTNAME``/Traefik parts
(the only ones this section used to call out) leaves the feature non-functional, since ``/sso_login`` still
authenticates against whatever ``modules.authentication.module`` is actually selected:

1. **Switch ``modules.authentication.module`` to ``authentication.passthru``.** The reference stack's
   ``docker/compose/base.yml`` ships ``authentication.configfile`` by default (see `Settings overrides`_ above) --
   without switching this, ``sso.py`` still calls ``passthru.authenticate()`` internally to exchange the SPNEGO
   negotiation for a session token, but that call is checked against the shared secret, and the *overall* login
   decision path Cobbler exposes elsewhere still reflects ``configfile``. In practice this means a successful
   Kerberos negotiation is exchanged for a token, but every other login path in the stack -- and the plain
   username/password login most operators expect -- has silently changed behavior, so this is not something to
   flip without accounting for its next paragraph. As with any other ``modules`` sub-key, follow the
   ``.. important::`` note in `Settings overrides`_ above: repeat the *entire* ``modules`` block in the
   ``cobbler-settings`` config, not just the ``authentication`` line, or you will silently blank out
   ``authorization``/``dns``/``dhcp``/``process_management``/``serializers`` back to their built-in defaults.

   .. warning::

      Enabling ``authentication.passthru`` disables all ``configfile`` username/password logins **system-wide**,
      not just for browser/SSO clients -- ``passthru`` authenticates *any* username paired with the correct
      shared secret (see ``cobbler/modules/authentication/passthru.py``), and once it is selected as
      ``modules.authentication.module`` there is no longer a ``configfile``-backed username/password check to
      fall back to. Anyone who can reach ``/cobbler_api`` and knows (or can read) the current contents of
      ``/var/lib/cobbler/web.ss`` can log in as any username, Kerberos or not.

      Separately, the *default* ``authorization.module`` in this reference stack is ``authorization.allowall``
      (see `Settings overrides`_ above), which grants full admin access to every authenticated user. Combined
      with ``authentication.passthru``, this means **every** Kerberos principal in your realm becomes a full
      Cobbler admin the moment they complete SSO. Before enabling this feature in production, tighten the
      authorization module too -- e.g. ``authorization.ownership`` or ``authorization.configfile`` -- so that
      Kerberos-authenticated users are not implicitly granted full administrative rights. See the
      ``authorization`` section of ``docs/cobbler-conf.rst`` for the available choices.

2. **A Kerberos service principal and keytab.** Create a service principal named ``HTTP/<hostname>@REALM``, where
   ``<hostname>`` is the externally-reachable hostname clients use to reach this stack (it must match exactly --
   Kerberos service principal names are hostname-specific) and ``REALM`` is your Kerberos realm, then export it to
   a keytab file. With MIT Kerberos' ``kadmin``:

   .. code-block:: shell

       kadmin -q "addprinc -randkey HTTP/cobbler.example.org@EXAMPLE.ORG"
       kadmin -q "ktadd -k /path/on/host/http-api.keytab HTTP/cobbler.example.org@EXAMPLE.ORG"

   Keep this keytab file readable only by whatever will run the ``http-api`` container -- it is equivalent to a
   long-lived credential for that service principal.

3. **The keytab mounted into the ``http-api`` container, and ``KRB5_KTNAME`` pointing at it.** ``compose.yml``/
   ``compose.dev.yml`` ship this as a commented-out, opt-in example on the ``http-api`` service. That service
   already has its own real ``environment:`` and ``volumes:`` blocks (for ``COBBLER_XMLRPC_HOST`` and the
   webdir/tftproot/distro-sources mounts) -- **add the keys below into those existing blocks**, do not uncomment
   a second, standalone ``environment:``/``volumes:`` mapping, since YAML mappings cannot have duplicate keys and
   a second copy would break the compose file:

   .. code-block:: yaml

       services:
         http-api:
           environment:
             # ... existing keys (e.g. COBBLER_XMLRPC_HOST) stay here too ...
             KRB5_KTNAME: /etc/krb5/http-api.keytab
           volumes:
             # ... existing volume entries stay here too ...
             - /path/on/host/http-api.keytab:/etc/krb5/http-api.keytab:ro

   ``sso.py`` reads ``KRB5_KTNAME`` from the server process's own environment (a Kerberos/krb5 convention, not a
   WSGI ``environ`` key) at request time -- without it (or without ``gssapi`` installed, see
   ``docker/images/cobblerd/Dockerfile``'s optional ``gssapi`` dependency), ``/sso_login`` always answers
   ``501 Not Implemented`` rather than failing to start.

4. **A ``krb5.conf`` with your realm/KDC configuration, mounted into the ``http-api`` container.** The runtime
   image installs the ``krb5`` package (for the ``gssapi`` library's native dependencies) but ships no realm
   configuration of its own -- without a realm-aware ``/etc/krb5.conf`` inside the container, GSSAPI has no way to
   find your KDC and negotiation fails even with a valid keytab. Mount your realm's ``krb5.conf`` read-only,
   again by adding to the *existing* ``volumes:`` block from the previous step:

   .. code-block:: yaml

       services:
         http-api:
           volumes:
             # ... existing volume entries, plus the keytab mount from the previous step ...
             - /path/on/host/krb5.conf:/etc/krb5.conf:ro

5. **The Traefik router and CORS middleware from** `Traefik and routing`_ **above**, which are *not* opt-in --
   they are always present in ``compose.yml``/``compose.dev.yml`` so the endpoint is reachable the moment an
   operator supplies a keytab, with no separate Compose edit needed.

   A browser calling ``/sso_login`` cross-origin (e.g. from the separate ``web`` container's origin) needs this
   to survive CORS, but -- unlike ``/cobbler_api`` -- it cannot reuse ``cobbler-api-cors`` unchanged: the
   ``cobbler-web`` frontend's ``SsoService`` calls this endpoint with ``withCredentials: true`` (its XML-RPC
   calls to ``/cobbler_api`` are uncredentialed, so ``cobbler-api-cors``'s wildcard
   ``accessControlAllowOriginList=*`` is fine there), and the Fetch/CORS spec forbids a wildcard
   ``Access-Control-Allow-Origin`` on any response to a credentialed request -- browsers reject it outright even
   if every other CORS header looks correct. ``cobbler-sso``'s router therefore carries its own dedicated
   ``cobbler-sso-cors`` middleware instead, which sets a **specific** allowed origin plus
   ``accessControlAllowCredentials=true``:

   .. code-block:: yaml

       - "traefik.http.middlewares.cobbler-sso-cors.headers.accessControlAllowOriginList=http://localhost"
       - "traefik.http.middlewares.cobbler-sso-cors.headers.accessControlAllowCredentials=true"
       - "traefik.http.middlewares.cobbler-sso-cors.headers.accessControlAllowMethods=GET,OPTIONS"
       - "traefik.http.middlewares.cobbler-sso-cors.headers.accessControlAllowHeaders=content-type"
       - "traefik.http.middlewares.cobbler-sso-cors.headers.accessControlMaxAge=100"

   The shipped ``http://localhost`` is, like ``docker/compose/web.yml``'s ``cobblerUrls`` default, a
   *local-development-only* placeholder that only resolves correctly when the browser and the Docker host are
   the same machine. **Before deploying this anywhere else, change ``accessControlAllowOriginList`` to your real
   frontend's externally-reachable origin** (e.g. ``https://cobbler.example.org``, with no path component --
   CORS origins never include one), matching whatever you set ``docker/compose/web.yml``'s ``cobblerUrls`` to.
   A mismatched or still-wildcarded origin here does not fail loudly: the endpoint keeps answering requests
   normally, but the browser silently discards the response before JavaScript ever sees it.

6. **Browser-side SPNEGO trust configuration.** Even with everything above in place, browsers do not answer a
   ``WWW-Authenticate: Negotiate`` challenge for just any origin -- each browser keeps its own allowlist of
   origins it will negotiate Kerberos with, and without adding yours the flow silently stops dead at the first
   ``401`` (no error dialog, just no retry with credentials). At minimum:

   * **Firefox:** add your origin to the ``network.negotiate-auth.trusted-uris`` preference (``about:config``),
     e.g. ``https://cobbler.example.org``.
   * **Chrome/Chromium:** set the ``AuthServerAllowlist`` policy (and, on older versions,
     ``AuthNegotiateDelegateAllowlist`` if you also need credential delegation) to your origin, via
     ``chrome://policy`` on a managed machine or the equivalent enterprise policy mechanism -- there is no
     per-user ``about:config``-style override.

   Neither of these is a Cobbler-side setting; both are configured on the client machines that will use SSO.

7. **The Angular frontend's own ``ssoLoginUrl`` configuration (forward reference).** Steps 1-6 above are enough
   to make ``/sso_login`` itself work end-to-end (verifiable directly with ``curl``), but they do not by
   themselves turn on the SSO login button in the ``cobbler-web`` frontend from `Web UI`_ above.
   ``docker/compose/web.yml``'s bundled ``app-config.json`` only sets ``cobblerUrls`` by default -- the frontend
   also needs, on the relevant server entry in that same ``app-config.json`` content block, both ``authMode`` set
   to ``"sso"`` or ``"both"`` **and** ``ssoLoginUrl`` set to this stack's ``/sso_login`` route -- keep it
   same-origin/root-relative (e.g. ``"/sso_login"``) rather than an absolute URL, per the ``cobbler-web``
   project's own deployment docs. It is easy to do everything above, confirm ``/sso_login`` works with ``curl``,
   and then still not see an SSO option in the UI because these frontend config keys were never added -- do not
   forget this step.

Once steps 1-6 are in place, the flow is: a client requests ``/sso_login`` with no credentials, gets back
``401 Unauthorized`` with ``WWW-Authenticate: Negotiate`` (the standard SPNEGO challenge, not an error), retries
with an ``Authorization: Negotiate <token>`` header carrying a real Kerberos ticket, and -- on successful
negotiation -- receives a normal Cobbler session token in the JSON response body, exactly as if it had called
``login()`` over XML-RPC directly.

.. warning::

   Use **HTTPS in production**. The SPNEGO negotiation and the resulting Cobbler session token both travel over
   plain HTTP otherwise, on the same trust-boundary basis as the release33 Apache bridge. Also note that this
   endpoint only strengthens the *browser login path*: ``/cobbler_api`` itself still has no authentication in
   front of it in this reference stack (see `Traefik and routing`_ above) -- direct XML-RPC or command-line
   clients can still call it, unauthenticated at the transport level, exactly as before. Enabling
   ``authentication.passthru`` also has the same system-wide implication it always has: **any** username paired
   with the correct shared secret authenticates successfully, not just ones that went through a real Kerberos
   negotiation. See step 1 above for the additional ``authorization.allowall`` admin-escalation implication of
   combining ``passthru`` with this reference stack's default authorization module.

Known limitations and non-goals
#################################

This deployment model is deliberately scoped. Before relying on it, be aware of the following:

* **Sidecar restart is not sidecar management.** `GH #3138
  <https://github.com/cobbler/cobbler/issues/3138>`_ (remote sibling-service management) is only *partially*
  closed by ``process_management.docker``: restarting a DHCP/DNS sidecar container by label works, but broader
  remote-service management -- pushing configuration changes to a sidecar, scaling it, or managing it through a
  non-Docker orchestrator -- is still open. Getting ``cobblerd``'s rendered DHCP/DNS configuration into the sidecar
  container in the first place **is** solved for the ``dhcp``/``dns`` sidecars, via the directory+symlink
  volume-sharing mechanism described above (verified end-to-end); it remains genuinely unsolved only for the
  illustrative ``dnsmasq`` example, whose config paths (``dnsmasq_settings_file``/``-hosts_file``/``-ethers_file``)
  are not covered by any volume in the reference stack.
* **One container per service, local Docker only.** The label-based restart mechanism requires exactly one running
  container per service label and a local-only Docker daemon. There is no support for multiple replicas of the same
  service, no support for a remote or TLS-secured Docker API, and no Kubernetes support. A Kubernetes "pod"
  selection mechanism would need a different, Kubernetes-native implementation -- it is not something this Docker
  Engine API-based module can grow into.
* **Partial environment-variable configuration.** `GH #3137
  <https://github.com/cobbler/cobbler/issues/3137>`_ (full environment-variable-driven configuration) is only
  partially covered: only the XML-RPC host/bind-address settings needed to split ``cobblerd`` and ``http-api`` into
  separate containers (``COBBLER_XMLRPC_BIND_ADDRESS``/``COBBLER_XMLRPC_HOST``) have environment variable
  overrides. Every other ``settings.yaml`` key must still be set through the settings file itself.
* **Kubernetes is out of scope.** Nothing on this page or in the referenced Dockerfile/Compose file has been
  designed, tested, or is intended for Kubernetes. Running this image under Kubernetes is not supported.
* **DHCP/DNS sidecars need cobblerd to have rendered real config at least once.** The ``dhcp``/``dns`` sidecar
  images (see above) set up ``/etc/dhcpd.conf``/``/etc/named.conf`` as symlinks into the shared
  ``cobbler-dhcp-config``/``cobbler-dns-config`` volumes; ``cobblerd``'s image sets up the identical symlinks on its
  side. If a sidecar starts before ``cobblerd`` has ever run a ``cobbler sync`` with ``manage_dhcp``/``manage_dns``
  enabled, that symlink is dangling and the sidecar's ``dhcpd``/``named`` process exits immediately. ``restart:
  unless-stopped`` on those services (already set in ``docker/compose/dhcp.yml``/``dns.yml`` and their
  ``.dev.yml`` variants) mitigates this: the sidecar keeps retrying and comes up cleanly as soon as the first sync
  writes real config into the shared volume. The illustrative ``dnsmasq`` example remains a genuine placeholder --
  no image is built for it in this repository, and its config paths are not covered by any volume in the
  reference stack.
* **Publishing is GHCR-only for now.** `.github/workflows/docker-publish.yml` publishes all three images it
  builds -- the shared ``cobblerd`` runtime image plus the ``cobbler-dhcp``/``cobbler-dns`` sidecar images -- to
  GHCR (``ghcr.io``). Cobbler's existing packages and CI test image are built and published through openSUSE's
  Open Build Service (OBS) instead; building/publishing these container images through OBS as well is out of
  scope for now.

See also
########

* ``compose.yml``/``compose.dev.yml`` and ``docker/compose/*.yml`` -- the reference Compose stack itself.
* ``docker/images/cobblerd/Dockerfile`` -- the single shared runtime image for both the ``cobblerd`` and
  ``http-api`` roles.
* `cobbler-web <https://github.com/cobbler/cobbler-web>`_ -- the Cobbler Web UI project itself, served by this
  stack's optional ``web`` service.
* :ref:`settings-ref` for the full list of ``settings.yaml`` keys.
* :ref:`dhcp-management` and :ref:`dns-management` for the DHCP/DNS managers that ``process_management`` restarts.
* :ref:`tftp-directory` for background on TFTP directory materialization and ``dynamic_tftp``.
