# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Cobbler contributors
"""
Direct-disk distro tree file server.

This WSGI app serves the files of a distro's original, uncopied source tree (``repodata/``,
``Packages/``, etc.) straight from disk, so that clients such as ``anaconda``/installer HTTP
clients can fetch package/repo data from ``$tree`` URLs of the form::

    http://<server>/cblr/svc/tree/<distro_name>/<relative_path>

without cobblerd having to stream every byte through an XML-RPC round trip (XML-RPC is only used
here for a single, briefly-cached metadata lookup: resolving a distro name to its
``source_tree_path``). This mirrors ``cobbler.services.svc``'s pattern for reaching cobblerd
(same settings file, same ``xmlrpc_port``/``xmlrpc_host`` keys, same unauthenticated
``xmlrpc.client.Server`` construction) but never uses XML-RPC for file bytes themselves.

Security note: the path-resolution logic in this module (:func:`is_safe_path` /
:func:`resolve_within_root`) is the only thing standing between an unauthenticated client and
arbitrary file disclosure. Both textual traversal (``../../etc/passwd``) and a symlink *inside*
the tree pointing outside of it must be rejected; both are defeated by resolving
``os.path.realpath`` on the fully-joined candidate path and requiring it to be the root or a
descendant of the root's own realpath -- never by textual ``..`` rejection alone (which a symlink
trivially bypasses).
"""

import html
import mimetypes
import os
import time
import xmlrpc.client
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib import parse

import yaml

# The client-facing mount point Apache's reverse proxy uses to route requests into this WSGI
# app (see the "ProxyPass /cblr/svc/ http://localhost:8000/" rule in
# cobbler/data/config/apache/cobbler.conf). Unlike the "/cobbler_api" ProxyPass block a couple of
# lines below it, this one has no accompanying ProxyPassReverse, so Apache forwards any Location
# header we emit to the client byte-for-byte, unmodified. Any absolute redirect URL we build must
# therefore be prefixed with this constant ourselves -- building it from our *internal*,
# post-proxy-strip path (e.g. "/tree/<distro>/...") would produce a Location the client's next
# request can't reach, since Apache never proxies bare "/tree/..." paths. See
# ``cobbler.services.svc``'s ``find_autoinstall()`` for the same hardcoded-prefix precedent.
EXTERNAL_MOUNT_PREFIX = "/cblr/svc"

# --------------------------------------------------------------------------------------------
# Metadata resolution (distro name -> source_tree_path), via a cached XML-RPC lookup.
# --------------------------------------------------------------------------------------------

#: How long a resolved ``source_tree_path`` (or a negative "not available" result) is cached for,
#: per distro name, before another XML-RPC ``get_distro`` call is made.
CACHE_TTL_SECONDS = 30.0

#: Module-level, per-process cache: ``{distro_name: (source_tree_path_or_None, expiry_time)}``.
#:
#: This is a plain dict with no locking. The dev/packaged deployment runs a single Gunicorn
#: worker (see ``docker/develop/supervisord/conf.d/gunicorn.conf`` and
#: ``cobbler/data/config/service/cobblerd-gunicorn.service``, both of which invoke
#: ``gunicorn cobbler.services:application`` with no ``--workers``/``--threads`` override, i.e.
#: Gunicorn's default of one sync worker/one thread). Should that ever change to a
#: multi-threaded worker class, concurrent access to this dict from two requests for the *same*
#: previously-uncached distro name could race (both miss the cache and both issue a redundant
#: XML-RPC call) -- harmless (just a duplicate lookup, not a correctness bug) under CPython's GIL,
#: since dict reads/writes here are simple enough not to interleave into a corrupted state. No
#: locking is added without evidence a multi-threaded worker is actually in use.
_source_tree_cache: Dict[str, Tuple[Optional[str], float]] = {}

_SETTINGS_PATH = "/etc/cobbler/settings.yaml"


def _build_remote() -> xmlrpc.client.Server:
    """
    Build an XML-RPC client pointed at cobblerd, mirroring
    ``cobbler.services.svc.application``'s own construction exactly (same settings file, same
    ``xmlrpc_port``/``xmlrpc_host`` keys/defaults and ``COBBLER_XMLRPC_HOST`` env var override,
    same unauthenticated, ``allow_none``-enabled server).

    :return: A ready-to-use XML-RPC server proxy.
    """
    with open(_SETTINGS_PATH, encoding="UTF-8") as main_settingsfile:
        ydata = yaml.safe_load(main_settingsfile)
    xmlrpc_port = ydata.get("xmlrpc_port", 25151)
    xmlrpc_host = os.environ.get(
        "COBBLER_XMLRPC_HOST", ydata.get("xmlrpc_host", "127.0.0.1")
    )
    return xmlrpc.client.Server(f"http://{xmlrpc_host}:{xmlrpc_port}", allow_none=True)


def resolve_source_tree_path(distro_name: str) -> Optional[str]:
    """
    Resolve a distro name to its ``source_tree_path``, via a short-TTL cached XML-RPC lookup.

    :param distro_name: The name of the distro to resolve.
    :return: The distro's ``source_tree_path``, or ``None`` if the distro doesn't exist or has no
             ``source_tree_path`` set (both are treated identically by callers: a 404).
    """
    now = time.monotonic()
    cached = _source_tree_cache.get(distro_name)
    if cached is not None and cached[1] > now:
        return cached[0]

    remote = _build_remote()
    try:
        distro_handle = remote.get_distro_handle(distro_name)
        data = remote.get_distro(distro_handle)
    except (xmlrpc.client.Fault, xmlrpc.client.ProtocolError, OSError):
        data = None

    source_tree_path: Optional[str] = None
    if isinstance(data, dict):
        value = data.get("source_tree_path")
        if isinstance(value, str) and value:
            source_tree_path = value

    _source_tree_cache[distro_name] = (source_tree_path, now + CACHE_TTL_SECONDS)
    return source_tree_path


# --------------------------------------------------------------------------------------------
# Path resolution and the security-critical traversal guard.
# --------------------------------------------------------------------------------------------


def is_safe_path(root_real: str, candidate_real: str) -> bool:
    """
    Check whether an already-``realpath``-resolved candidate path is the root itself or a proper
    descendant of it.

    Both inputs must already have been passed through ``os.path.realpath`` by the caller -- this
    function itself does no filesystem access, which is what makes it cheaply, deterministically
    unit-testable on plain strings. The actual security property (catching symlink escapes) comes
    entirely from the caller having resolved ``candidate_real`` with ``realpath`` *after* joining
    in the untrusted relative path, not from anything this function does.

    :param root_real: The realpath of the distro's ``source_tree_path`` root.
    :param candidate_real: The realpath of the fully-joined candidate path.
    :return: ``True`` if ``candidate_real`` is ``root_real`` or a descendant of it.
    """
    return candidate_real == root_real or candidate_real.startswith(root_real + os.sep)


def resolve_within_root(root: str, relative_path: str) -> Optional[str]:
    """
    Join ``relative_path`` onto ``root`` and validate the result stays within ``root``.

    This is the security-critical traversal guard. It defends against two distinct attacks:

    - **Textual traversal**: a ``relative_path`` containing ``../`` segments that would
      lexically escape ``root`` (e.g. ``../../etc/passwd``).
    - **Symlink escape**: a symlink that lives *inside* ``root`` (so it wouldn't be caught by
      rejecting ``..`` in the URL) but whose target points outside of ``root``.

    Both are defeated the same way: ``os.path.realpath`` is applied to the *final* joined
    candidate path (not just to the root), which fully resolves both ``..`` segments and any
    symlinks encountered anywhere along the path -- including a symlink as the last component.
    The resolved result is then required to be exactly ``root``'s own realpath, or a path
    beginning with ``root_real + os.sep``. A leading ``/`` on ``relative_path`` is stripped
    first so an absolute-looking segment (e.g. from a doubled slash in the URL) can't make
    ``os.path.join`` discard ``root`` outright.

    :param root: The distro's ``source_tree_path`` (already validated elsewhere to be an
                 absolute, existing directory).
    :param relative_path: The untrusted, already-URL-decoded path requested by the client.
    :return: The resolved, validated, absolute realpath if it is safe, or ``None`` if the request
             must be rejected (the caller maps this to ``403 Forbidden``).
    """
    root_real = os.path.realpath(root)
    candidate = os.path.join(root_real, relative_path.lstrip("/"))
    candidate_real = os.path.realpath(candidate)
    if is_safe_path(root_real, candidate_real):
        return candidate_real
    return None


# --------------------------------------------------------------------------------------------
# HTTP Range parsing.
# --------------------------------------------------------------------------------------------


class RangeUnsatisfiable(Exception):
    """
    Raised by :func:`parse_range` when the ``Range`` header is syntactically a byte-range but
    requests a start offset beyond the file's size, i.e. a ``416 Range Not Satisfiable``.
    """


def parse_range(header: str, size: int) -> Optional[Tuple[int, int]]:
    """
    Parse an HTTP ``Range`` header of the form ``bytes=start-end`` (both bounds optional, per
    RFC 7233), against a known file size.

    Suffix ranges (``bytes=-N``, meaning "the last N bytes") and multi-range requests
    (``bytes=0-99,200-299``) are treated as unsupported and cause the request to be served in
    full (``None`` is returned, i.e. "no usable range, ignore it"), rather than as an error --
    this mirrors the permissive behavior most HTTP servers fall back to for Range syntax they
    don't implement.

    :param header: The raw ``Range`` header value, e.g. ``bytes=0-99``.
    :param size: The total size of the file in bytes.
    :return: An inclusive ``(start, end)`` tuple, or ``None`` if the header should be ignored and
             the full file served instead.
    :raises RangeUnsatisfiable: if the requested start offset is beyond ``size``.
    """
    if not header.startswith("bytes="):
        return None
    spec = header[len("bytes=") :].strip()
    if "," in spec or "-" not in spec:
        return None

    start_str, _, end_str = spec.partition("-")
    if start_str == "":
        # Suffix range (bytes=-N): not supported, fall back to serving the full file.
        return None

    try:
        start = int(start_str)
    except ValueError:
        return None
    if start < 0:
        return None
    # A start offset at or beyond the file's size is unsatisfiable regardless of the end bound
    # (or its absence) -- this must be checked before an absent end defaults to "size - 1",
    # otherwise a too-large start would just look like "start > end" and be silently ignored.
    if start >= size:
        raise RangeUnsatisfiable()

    if end_str == "":
        end = size - 1
    else:
        try:
            end = int(end_str)
        except ValueError:
            return None
        if end < start:
            return None

    end = min(end, size - 1)
    return start, end


# --------------------------------------------------------------------------------------------
# WSGI response helpers.
# --------------------------------------------------------------------------------------------

_WsgiStartResponse = Callable[[str, List[Any]], None]


def _error_response(
    start_response: _WsgiStartResponse,
    status: str,
    message: str,
    is_head: bool = False,
) -> List[bytes]:
    """
    Build a short, plain-text error response. Never includes any resolved filesystem path, to
    avoid leaking server-side layout to an unauthenticated client.

    :param is_head: If ``True``, headers (including ``Content-Length``) reflect ``message`` as
                     they would for ``GET``, but no body is returned, per RFC 7231 section 4.3.2.
    """
    content = message.encode("utf-8")
    start_response(
        status,
        [
            ("Content-Type", "text/plain; charset=utf-8"),
            ("Content-Length", str(len(content))),
        ],
    )
    if is_head:
        return []
    return [content]


def _bounded_file_iter(file_obj: Any, remaining: int, chunk_size: int = 65536):
    """
    Chunked-read fallback generator, used whenever ``wsgi.file_wrapper`` isn't available, and
    always used to serve bounded ``Range`` responses (since a raw ``wsgi.file_wrapper`` has no
    way to be told to stop before EOF, which would leak bytes past the requested range).
    """
    try:
        while remaining > 0:
            chunk = file_obj.read(min(chunk_size, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk
    finally:
        file_obj.close()


def _serve_file(
    resolved_path: str,
    relative_path: str,
    environ: Dict[str, Any],
    start_response: _WsgiStartResponse,
    is_head: bool = False,
) -> Any:
    """
    Serve a single file, honoring an optional ``Range`` request.

    :param resolved_path: The validated, absolute, on-disk path of the file to serve.
    :param relative_path: The (decoded) client-relative path, used only for MIME-type guessing.
    :param environ: The WSGI environ (read for ``HTTP_RANGE`` and ``wsgi.file_wrapper``).
    :param start_response: The WSGI ``start_response`` callable.
    :param is_head: If ``True``, compute/send the exact same headers a ``GET`` would produce, but
                     never open the file on disk and never return a body.
    """
    try:
        size = os.path.getsize(resolved_path)
    except OSError:
        return _error_response(start_response, "404 Not Found", "Not Found", is_head)

    guessed_type, guessed_encoding = mimetypes.guess_type(relative_path)
    if guessed_encoding is not None:
        # e.g. "primary.xml.gz" guesses as ("text/xml", "gzip"). We don't do HTTP content-encoding
        # negotiation here (no "Content-Encoding" header, no transparent decompression by this
        # server or by intermediaries), so serving it with the un-encoded guessed type
        # ("text/xml") would actively mislabel a gzip blob. Fall back to a generic binary type
        # instead of trying to bolt on a "Content-Encoding" header, which would incorrectly imply
        # the HTTP layer will decompress the response.
        content_type = "application/octet-stream"
    else:
        content_type = guessed_type or "application/octet-stream"

    start = 0
    end = size - 1
    status = "200 OK"

    range_header = environ.get("HTTP_RANGE")
    if range_header:
        try:
            parsed = parse_range(range_header, size)
        except RangeUnsatisfiable:
            return _serve_range_unsatisfiable(start_response, size, is_head)
        if parsed is not None:
            start, end = parsed
            status = "206 Partial Content"

    length = end - start + 1

    if is_head:
        # Compute/send the exact same headers a GET would, but never touch the file's actual
        # bytes -- opening it would be pure overhead for a request whose response has no body.
        headers = [
            ("Content-Type", content_type),
            ("Content-Length", str(length)),
            ("Accept-Ranges", "bytes"),
        ]
        if status == "206 Partial Content":
            headers.append(("Content-Range", f"bytes {start}-{end}/{size}"))
        start_response(status, headers)
        return []

    try:
        file_obj = open(resolved_path, "rb")  # pylint: disable=consider-using-with
    except OSError:
        return _error_response(start_response, "404 Not Found", "Not Found")
    file_obj.seek(start)

    headers: List[Any] = [
        ("Content-Type", content_type),
        ("Content-Length", str(length)),
        ("Accept-Ranges", "bytes"),
    ]
    if status == "206 Partial Content":
        headers.append(("Content-Range", f"bytes {start}-{end}/{size}"))

    start_response(status, headers)

    is_full_file = start == 0 and length == size
    file_wrapper = environ.get("wsgi.file_wrapper")
    if is_full_file and file_wrapper is not None:
        return file_wrapper(file_obj, 65536)
    return _bounded_file_iter(file_obj, length)


def _serve_range_unsatisfiable(
    start_response: _WsgiStartResponse, size: int, is_head: bool = False
) -> List[bytes]:
    """
    Build a ``416 Range Not Satisfiable`` response with the ``Content-Range: bytes */<size>``
    header required by RFC 7233.
    """
    start_response(
        "416 Range Not Satisfiable",
        [
            ("Content-Type", "text/plain; charset=utf-8"),
            ("Content-Length", "0"),
            ("Content-Range", f"bytes */{size}"),
            ("Accept-Ranges", "bytes"),
        ],
    )
    return [] if is_head else [b""]


def _list_directory(
    resolved_path: str, start_response: _WsgiStartResponse, is_head: bool = False
) -> List[bytes]:
    """
    Generate a simple, browsable HTML directory listing of the *immediate* children of
    ``resolved_path`` (not recursive), sorted, excluding dotfiles, with directory entries linked
    with a trailing ``/``. All hrefs are relative, self-contained self-generated markup (not a
    reuse of ``http.server.SimpleHTTPRequestHandler``, which isn't designed to be reused this
    way).
    """
    try:
        names = sorted(
            name for name in os.listdir(resolved_path) if not name.startswith(".")
        )
    except OSError:
        return _error_response(start_response, "404 Not Found", "Not Found", is_head)

    items: List[str] = []
    for name in names:
        is_dir = os.path.isdir(os.path.join(resolved_path, name))
        display_name = name + "/" if is_dir else name
        href = parse.quote(display_name)
        items.append(f'<li><a href="{href}">{html.escape(display_name)}</a></li>')

    body = (
        "<!DOCTYPE html>\n"
        '<html>\n<head><meta charset="utf-8"><title>Directory listing</title></head>\n'
        "<body>\n<h1>Directory listing</h1>\n<ul>\n"
        + "\n".join(items)
        + "\n</ul>\n</body>\n</html>\n"
    )
    content = body.encode("utf-8")
    start_response(
        "200 OK",
        [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Content-Length", str(len(content))),
        ],
    )
    return [] if is_head else [content]


# --------------------------------------------------------------------------------------------
# WSGI entry point.
# --------------------------------------------------------------------------------------------


def application(environ: Dict[str, Any], start_response: _WsgiStartResponse) -> Any:
    """
    WSGI entrypoint for direct-disk distro tree file serving.

    Expects to be invoked (via ``cobbler.services.application``'s dispatch) for request paths of
    the shape ``/tree/<distro_name>/<relative_path>`` -- i.e. the client-facing
    ``/cblr/svc/tree/...`` URL with Apache's ``ProxyPass`` prefix already stripped, exactly like
    ``cobbler.services.svc.application`` sees its own paths via ``environ["RAW_URI"]``.

    Only ``GET`` and ``HEAD`` are supported. ``HEAD`` runs through the exact same
    resolution/header-computation logic as ``GET`` (so e.g. ``Content-Length``/``Content-Type``
    reflect the same values a ``GET`` would have produced) but the response body is discarded
    before returning, per RFC 7231 section 4.3.2. Any other method (``POST``, ``DELETE``, ...) is
    rejected outright with ``405 Method Not Allowed`` rather than being treated as a ``GET``.

    :param environ: The WSGI environ.
    :param start_response: The WSGI ``start_response`` callable.
    """
    method = environ.get("REQUEST_METHOD", "GET")
    if method not in ("GET", "HEAD"):
        return _error_response(
            start_response, "405 Method Not Allowed", "Method Not Allowed"
        )

    return _dispatch(environ, start_response, is_head=(method == "HEAD"))


def _dispatch(
    environ: Dict[str, Any], start_response: _WsgiStartResponse, is_head: bool = False
) -> Any:
    """
    Resolve and serve a single ``GET``/``HEAD`` request. See :func:`application` for the public
    entrypoint, which additionally handles HTTP method validation.

    :param environ: The WSGI environ.
    :param start_response: The WSGI ``start_response`` callable.
    :param is_head: If ``True``, compute/send the same headers a ``GET`` would, but never return
                     a body (and, for file responses, never open the file on disk at all).
    """
    raw_uri = environ.get("RAW_URI", "")
    base_path, _, query = raw_uri.partition("?")
    decoded_path = parse.unquote(base_path)

    # decoded_path looks like "/tree/<distro_name>/<relative...>" (or "/tree/<distro_name>",
    # or "/tree/<distro_name>/" for the tree root). Split as one opaque tail, not
    # alternating key/value tokens like svc.py's __fillup_form_dict does -- the relative path
    # can itself contain any number of "/"-separated segments that must stay intact.
    parts = decoded_path.split("/")
    if len(parts) < 3 or parts[1] != "tree" or not parts[2]:
        return _error_response(start_response, "404 Not Found", "Not Found", is_head)

    distro_name = parts[2]
    relative_path = "/".join(parts[3:])

    source_tree_path = resolve_source_tree_path(distro_name)
    if not source_tree_path:
        return _error_response(start_response, "404 Not Found", "Not Found", is_head)

    return _serve_path_under_root(
        source_tree_path,
        relative_path,
        base_path,
        query,
        environ,
        start_response,
        is_head,
        redirect_prefix=EXTERNAL_MOUNT_PREFIX,
    )


def _serve_path_under_root(
    root: str,
    relative_path: str,
    base_path: str,
    query: str,
    environ: Dict[str, Any],
    start_response: _WsgiStartResponse,
    is_head: bool,
    redirect_prefix: str = "",
) -> Any:
    """
    Shared tail of request handling once a ``root`` directory and an untrusted ``relative_path``
    within it are known: apply the path-traversal guard, then serve a file, a directory listing,
    or a redirect to add a trailing slash, exactly as :func:`_dispatch` (the ``/tree/...`` route)
    has always done. Used both by :func:`_dispatch` and by :func:`_dispatch_static` (the
    ``/httpboot``/``/images`` routes), so the traversal guard and file-serving logic are never
    duplicated between them.

    :param root: The already-known, absolute on-disk directory to serve ``relative_path`` from.
    :param relative_path: The untrusted, already-URL-decoded path requested by the client,
                           relative to ``root``.
    :param base_path: The internal request path (post any proxy-prefix-stripping), used to build
                       a same-path-plus-trailing-slash redirect ``Location``.
    :param query: The raw (still-encoded) query string, re-appended to a redirect ``Location`` if
                  non-empty.
    :param environ: The WSGI environ (passed through to :func:`_serve_file` for ``HTTP_RANGE``).
    :param start_response: The WSGI ``start_response`` callable.
    :param is_head: If ``True``, compute/send the same headers a ``GET`` would, but never return
                     a body.
    :param redirect_prefix: Prepended to ``base_path`` when building a trailing-slash redirect's
                             ``Location`` header, for routes that sit behind a proxy prefix that
                             was already stripped from ``base_path`` itself (see
                             :data:`EXTERNAL_MOUNT_PREFIX`). Routes with no such stripped prefix
                             (``/httpboot``, ``/images``) pass the default, empty string.
    """
    try:
        resolved_path = resolve_within_root(root, relative_path)
    except (OSError, ValueError):
        # A malformed path (e.g. an embedded NUL byte from a decoded "%00") makes
        # os.path.realpath raise rather than return a comparable string. Fail closed as a
        # plain 404 rather than letting the exception propagate into an unhandled 500.
        return _error_response(start_response, "404 Not Found", "Not Found", is_head)
    if resolved_path is None:
        return _error_response(start_response, "403 Forbidden", "Forbidden", is_head)

    if not os.path.exists(resolved_path):
        return _error_response(start_response, "404 Not Found", "Not Found", is_head)

    if os.path.isdir(resolved_path):
        if not base_path.endswith("/"):
            # redirect_prefix is only non-empty for routes whose base_path is the internal,
            # post-proxy-strip path (see EXTERNAL_MOUNT_PREFIX's own docstring for why that
            # matters: no accompanying ProxyPassReverse, so the client gets our Location
            # byte-for-byte).
            location = (
                redirect_prefix + base_path + "/" + (f"?{query}" if query else "")
            )
            start_response(
                "301 Moved Permanently",
                [("Location", location), ("Content-Length", "0")],
            )
            return [b""]
        return _list_directory(resolved_path, start_response, is_head)

    if os.path.isfile(resolved_path):
        return _serve_file(
            resolved_path, relative_path, environ, start_response, is_head
        )

    return _error_response(start_response, "404 Not Found", "Not Found", is_head)


# --------------------------------------------------------------------------------------------
# /httpboot and /images: direct-disk serving of tftproot/grub content for UEFI HTTP(S) boot.
#
# These mirror Apache's ``Alias /httpboot @@tftproot@@/grub`` and
# ``Alias /images @@tftproot@@/grub/images`` (cobbler/data/config/apache/cobbler.conf), which the
# containerized Traefik proxy cannot replicate (it has no on-disk static file serving). Unlike the
# ``/tree/<distro_name>/...`` route above, there is no per-distro XML-RPC metadata lookup: the
# on-disk root is fixed and derived directly from the ``tftpboot_location`` setting, and the
# client-facing URL prefix is served as-is (these routes are not proxied under a stripped prefix
# like ``/cblr/svc/``, so ``base_path`` is already the correct external path for redirects).
# --------------------------------------------------------------------------------------------


def _tftpboot_location() -> str:
    """
    Read the ``tftpboot_location`` setting fresh from ``settings.yaml``.

    Deliberately uncached and re-read on every call, mirroring
    ``cobbler.services.svc.application``'s own settings read (which also happens once per
    request): this is a cheap local file read, not an XML-RPC round trip like
    :func:`resolve_source_tree_path`'s cached distro metadata lookup, so there is no latency here
    worth amortizing with a cache.

    :return: The configured ``tftpboot_location``, or its packaged default if unset.
    """
    with open(_SETTINGS_PATH, encoding="UTF-8") as main_settingsfile:
        ydata = yaml.safe_load(main_settingsfile)
    return ydata.get("tftpboot_location", "/var/lib/tftpboot")


def _httpboot_root() -> str:
    """The on-disk root ``/httpboot`` serves, i.e. ``<tftpboot_location>/grub``."""
    return os.path.join(_tftpboot_location(), "grub")


def _images_root() -> str:
    """The on-disk root ``/images`` serves, i.e. ``<tftpboot_location>/grub/images``."""
    return os.path.join(_tftpboot_location(), "grub", "images")


def _dispatch_static(
    environ: Dict[str, Any],
    start_response: _WsgiStartResponse,
    url_prefix: str,
    root: str,
    is_head: bool = False,
) -> Any:
    """
    Resolve and serve a single ``GET``/``HEAD`` request for a fixed on-disk root mounted at a
    fixed URL prefix. See :func:`httpboot_application`/:func:`images_application` for the public
    entrypoints, which additionally handle HTTP method validation.

    :param environ: The WSGI environ.
    :param start_response: The WSGI ``start_response`` callable.
    :param url_prefix: The fixed external URL prefix this route is mounted at (e.g.
                        ``/httpboot``). ``environ["RAW_URI"]`` is expected to start with this
                        prefix unmodified -- no proxy-prefix-stripping happens ahead of this
                        route, unlike ``/cblr/svc/tree/...``.
    :param root: The on-disk directory ``url_prefix`` maps to.
    :param is_head: If ``True``, compute/send the same headers a ``GET`` would, but never return
                     a body (and, for file responses, never open the file on disk at all).
    """
    raw_uri = environ.get("RAW_URI", "")
    base_path, _, query = raw_uri.partition("?")
    decoded_path = parse.unquote(base_path)

    if decoded_path == url_prefix:
        relative_path = ""
    elif decoded_path.startswith(url_prefix + "/"):
        relative_path = decoded_path[len(url_prefix) + 1 :]
    else:
        return _error_response(start_response, "404 Not Found", "Not Found", is_head)

    return _serve_path_under_root(
        root, relative_path, base_path, query, environ, start_response, is_head
    )


def httpboot_application(
    environ: Dict[str, Any], start_response: _WsgiStartResponse
) -> Any:
    """
    WSGI entrypoint for direct-disk serving of ``/httpboot`` (UEFI HTTP(S) boot files), the
    Gunicorn equivalent of Apache's ``Alias /httpboot @@tftproot@@/grub``.

    Only ``GET`` and ``HEAD`` are supported, exactly like :func:`application`.

    :param environ: The WSGI environ.
    :param start_response: The WSGI ``start_response`` callable.
    """
    method = environ.get("REQUEST_METHOD", "GET")
    if method not in ("GET", "HEAD"):
        return _error_response(
            start_response, "405 Method Not Allowed", "Method Not Allowed"
        )
    return _dispatch_static(
        environ,
        start_response,
        "/httpboot",
        _httpboot_root(),
        is_head=(method == "HEAD"),
    )


def images_application(
    environ: Dict[str, Any], start_response: _WsgiStartResponse
) -> Any:
    """
    WSGI entrypoint for direct-disk serving of ``/images`` (UEFI HTTP(S) boot files), the
    Gunicorn equivalent of Apache's ``Alias /images @@tftproot@@/grub/images``.

    Only ``GET`` and ``HEAD`` are supported, exactly like :func:`application`.

    :param environ: The WSGI environ.
    :param start_response: The WSGI ``start_response`` callable.
    """
    method = environ.get("REQUEST_METHOD", "GET")
    if method not in ("GET", "HEAD"):
        return _error_response(
            start_response, "405 Method Not Allowed", "Method Not Allowed"
        )
    return _dispatch_static(
        environ, start_response, "/images", _images_root(), is_head=(method == "HEAD")
    )


# --------------------------------------------------------------------------------------------
# /healthz: a lightweight, unauthenticated liveness check for the Gunicorn "web" service,
# backed by an actual XML-RPC round trip against cobblerd. Reuses _build_remote() for host/port
# resolution (same settings.yaml, same COBBLER_XMLRPC_HOST override) exactly like the routes
# above, and CobblerXMLRPCInterface.ping() -- one of the very few XML-RPC methods that takes no
# token and performs no check_access() call, i.e. it does no real work and needs no
# authentication, which is exactly what a health check wants.
# --------------------------------------------------------------------------------------------


def healthz_application(
    environ: Dict[str, Any], start_response: _WsgiStartResponse
) -> Any:
    """
    WSGI entrypoint for ``/healthz``: reports whether cobblerd's XML-RPC endpoint is reachable
    and responsive.

    Only ``GET`` and ``HEAD`` are supported, exactly like :func:`application`. A successful XML-RPC
    ``ping()`` round trip yields ``200 OK``; any failure to reach or get a response from cobblerd
    (connection refused, timeout, an XML-RPC fault, or a malformed/missing settings file, all of
    which surface as ``OSError``/``xmlrpc.client.Fault``/``xmlrpc.client.ProtocolError``) yields
    ``503 Service Unavailable`` rather than propagating as an unhandled exception/500.

    :param environ: The WSGI environ.
    :param start_response: The WSGI ``start_response`` callable.
    """
    method = environ.get("REQUEST_METHOD", "GET")
    is_head = method == "HEAD"
    if method not in ("GET", "HEAD"):
        return _error_response(
            start_response, "405 Method Not Allowed", "Method Not Allowed", is_head
        )

    try:
        remote = _build_remote()
        remote.ping()
    except (xmlrpc.client.Fault, xmlrpc.client.ProtocolError, OSError):
        return _error_response(
            start_response, "503 Service Unavailable", "Service Unavailable", is_head
        )

    content = b"OK"
    start_response(
        "200 OK",
        [
            ("Content-Type", "text/plain; charset=utf-8"),
            ("Content-Length", str(len(content))),
        ],
    )
    return [] if is_head else [content]
