# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Cobbler contributors
"""
Tests for ``cobbler.services.files``, the direct-disk distro tree file server.

The XML-RPC metadata lookup (``get_distro``) is mocked/stubbed throughout -- these are unit tests
and must not require a live cobblerd. Everything filesystem-related uses real temporary files,
directories, and symlinks under ``tmp_path``; this is deliberate and non-negotiable for the
path-traversal tests in particular, since mocking ``os.path``/``open`` there could hide a real
traversal bug instead of proving its absence.
"""

import xmlrpc.client
from pathlib import Path
from typing import Any, Dict, Generator, List
from unittest.mock import MagicMock

import pytest

from cobbler.services import files


class _Response:
    """Small helper that captures a WSGI ``start_response`` call and the resulting body."""

    def __init__(self) -> None:
        self.status: str = ""
        self.headers: List[Any] = []

    def start_response(self, status: str, headers: List[Any]) -> None:
        self.status = status
        self.headers = headers

    def header(self, name: str) -> str:
        for key, value in self.headers:
            if key.lower() == name.lower():
                return value
        raise KeyError(name)

    def has_header(self, name: str) -> bool:
        return any(key.lower() == name.lower() for key, _ in self.headers)


def _call(environ: Dict[str, Any], app: Any = files.application) -> Any:
    resp = _Response()
    body_iter = app(environ, resp.start_response)
    body = b"".join(body_iter)
    if hasattr(body_iter, "close"):
        body_iter.close()
    return resp, body


def _environ(raw_uri: str, **extra: Any) -> Dict[str, Any]:
    environ: Dict[str, Any] = {"RAW_URI": raw_uri}
    environ.update(extra)
    return environ


@pytest.fixture(autouse=True)
def fixture_clear_cache() -> Generator[None, None, None]:
    files._source_tree_cache.clear()  # pylint: disable=protected-access  # type: ignore[reportPrivateUsage]
    yield
    files._source_tree_cache.clear()  # pylint: disable=protected-access  # type: ignore[reportPrivateUsage]


@pytest.fixture
def stub_remote(monkeypatch: pytest.MonkeyPatch):
    """
    Replace ``files._build_remote`` with a stub whose ``get_distro`` is a ``MagicMock``, so tests
    can control what metadata is "returned by cobblerd" and assert on call counts, without any
    real XML-RPC traffic.
    """
    mock_remote = MagicMock()
    monkeypatch.setattr(files, "_build_remote", lambda: mock_remote)
    return mock_remote


def _distro_dict(source_tree_path: str = "") -> Dict[str, Any]:
    return {"name": "irrelevant", "source_tree_path": source_tree_path}


# --------------------------------------------------------------------------------------------
# Full-file GET
# --------------------------------------------------------------------------------------------


def test_full_file_get(tmp_path: Path, stub_remote: MagicMock) -> None:
    root = tmp_path / "tree"
    (root / "repodata").mkdir(parents=True)
    content = b"<repomd>hello world</repomd>"
    (root / "repodata" / "repomd.xml").write_bytes(content)
    stub_remote.get_distro.return_value = _distro_dict(str(root))

    resp, body = _call(_environ("/tree/mydistro/repodata/repomd.xml"))

    assert resp.status == "200 OK"
    assert body == content
    assert resp.header("Content-Length") == str(len(content))
    assert "xml" in resp.header("Content-Type")


def test_full_file_get_unknown_extension_falls_back_to_octet_stream(
    tmp_path: Path, stub_remote: MagicMock
) -> None:
    root = tmp_path / "tree"
    root.mkdir()
    (root / "blob.reallyunknownext").write_bytes(b"binary-ish")
    stub_remote.get_distro.return_value = _distro_dict(str(root))

    resp, body = _call(_environ("/tree/mydistro/blob.reallyunknownext"))

    assert resp.status == "200 OK"
    assert body == b"binary-ish"
    assert resp.header("Content-Type") == "application/octet-stream"


def test_gzip_file_is_served_as_octet_stream_not_mislabeled(
    tmp_path: Path, stub_remote: MagicMock
) -> None:
    """
    ``mimetypes.guess_type("primary.xml.gz")`` returns ``("text/xml", "gzip")``. Since this
    server never adds a ``Content-Encoding`` header (no content-encoding negotiation is done),
    serving the un-encoded guessed type ("text/xml") would mislabel the still-gzipped bytes on
    the wire. It must fall back to a generic binary type instead.
    """
    root = tmp_path / "tree"
    (root / "repodata").mkdir(parents=True)
    (root / "repodata" / "primary.xml.gz").write_bytes(b"\x1f\x8b\x08fake-gzip-bytes")
    stub_remote.get_distro.return_value = _distro_dict(str(root))

    resp, _ = _call(_environ("/tree/mydistro/repodata/primary.xml.gz"))

    assert resp.status == "200 OK"
    assert resp.header("Content-Type") == "application/octet-stream"
    assert not resp.has_header("Content-Encoding")


# --------------------------------------------------------------------------------------------
# Range GET
# --------------------------------------------------------------------------------------------


def test_range_get_returns_206_with_exact_bytes(
    tmp_path: Path, stub_remote: MagicMock
) -> None:
    root = tmp_path / "tree"
    root.mkdir()
    content = bytes(range(256)) * 2  # 512 distinct-ish bytes, well over 100
    (root / "Packages" / "pkg.rpm").parent.mkdir()
    (root / "Packages" / "pkg.rpm").write_bytes(content)
    stub_remote.get_distro.return_value = _distro_dict(str(root))

    resp, body = _call(
        _environ("/tree/mydistro/Packages/pkg.rpm", HTTP_RANGE="bytes=0-99")
    )

    assert resp.status == "206 Partial Content"
    assert resp.header("Content-Range") == f"bytes 0-99/{len(content)}"
    assert resp.header("Content-Length") == "100"
    assert body == content[0:100]


def test_range_get_mid_file_open_ended(tmp_path: Path, stub_remote: MagicMock) -> None:
    root = tmp_path / "tree"
    root.mkdir()
    content = bytes(range(256))
    (root / "file.bin").write_bytes(content)
    stub_remote.get_distro.return_value = _distro_dict(str(root))

    resp, body = _call(_environ("/tree/mydistro/file.bin", HTTP_RANGE="bytes=200-"))

    assert resp.status == "206 Partial Content"
    assert resp.header("Content-Range") == f"bytes 200-255/{len(content)}"
    assert body == content[200:]


def test_range_get_out_of_range_is_416(tmp_path: Path, stub_remote: MagicMock) -> None:
    root = tmp_path / "tree"
    root.mkdir()
    content = b"short content"
    (root / "file.bin").write_bytes(content)
    stub_remote.get_distro.return_value = _distro_dict(str(root))

    resp, body = _call(
        _environ("/tree/mydistro/file.bin", HTTP_RANGE=f"bytes={len(content) + 50}-")
    )

    assert resp.status == "416 Range Not Satisfiable"
    assert resp.header("Content-Range") == f"bytes */{len(content)}"
    assert body == b""


# --------------------------------------------------------------------------------------------
# Distro / metadata errors
# --------------------------------------------------------------------------------------------


def test_unknown_distro_is_404(stub_remote: MagicMock) -> None:
    # get_distro on an unknown name returns the string "~" over XML-RPC (remote.py's
    # xmlrpc_hacks None-marker), not a dict.
    stub_remote.get_distro.return_value = "~"

    resp, _ = _call(_environ("/tree/nonexistent/repodata/repomd.xml"))

    assert resp.status == "404 Not Found"


def test_distro_without_source_tree_path_is_404(stub_remote: MagicMock) -> None:
    stub_remote.get_distro.return_value = _distro_dict("")

    resp, _ = _call(_environ("/tree/normaldistro/repodata/repomd.xml"))

    assert resp.status == "404 Not Found"


def test_upstream_protocol_error_fails_closed_as_404(stub_remote: MagicMock) -> None:
    """
    A malformed/unexpected XML-RPC response from cobblerd raises ``xmlrpc.client.ProtocolError``,
    which is a plain ``Exception`` subclass (not an ``OSError``). This must fail closed as a
    clean 404, the same way an ``xmlrpc.client.Fault`` or ``OSError`` already does, rather than
    propagating as an unhandled exception.
    """
    stub_remote.get_distro.side_effect = xmlrpc.client.ProtocolError(
        "http://127.0.0.1:25151", 502, "Bad Gateway", {}
    )

    resp, _ = _call(_environ("/tree/mydistro/repodata/repomd.xml"))

    assert resp.status == "404 Not Found"


def test_missing_file_under_valid_root_is_404(
    tmp_path: Path, stub_remote: MagicMock
) -> None:
    root = tmp_path / "tree"
    root.mkdir()
    stub_remote.get_distro.return_value = _distro_dict(str(root))

    resp, _ = _call(_environ("/tree/mydistro/does/not/exist.rpm"))

    assert resp.status == "404 Not Found"


def test_embedded_nul_byte_in_path_is_404_not_a_crash(
    tmp_path: Path, stub_remote: MagicMock
) -> None:
    """
    A URL-decoded ``%00`` yields an embedded NUL byte, which makes ``os.path.realpath`` raise
    ``ValueError`` rather than return a comparable path. This must fail closed as a plain 404,
    not propagate as an unhandled exception (which could otherwise surface a traceback/500).
    """
    root = tmp_path / "tree"
    root.mkdir()
    stub_remote.get_distro.return_value = _distro_dict(str(root))

    resp, _ = _call(_environ("/tree/mydistro/evil%00.txt"))

    assert resp.status == "404 Not Found"


# --------------------------------------------------------------------------------------------
# Path traversal -- the most important tests in this file.
# --------------------------------------------------------------------------------------------


SECRET_MARKER = "TOP-SECRET-MARKER-CONTENT-DO-NOT-LEAK"


def test_textual_traversal_is_rejected(tmp_path: Path, stub_remote: MagicMock) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text(SECRET_MARKER)
    stub_remote.get_distro.return_value = _distro_dict(str(root))

    # "../outside/secret.txt" lexically escapes root (root's parent is tmp_path).
    resp, body = _call(_environ("/tree/mydistro/../outside/secret.txt"))

    assert resp.status == "403 Forbidden"
    assert SECRET_MARKER.encode() not in body
    assert str(outside) not in body.decode(errors="replace")


def test_symlink_escape_is_rejected(tmp_path: Path, stub_remote: MagicMock) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text(SECRET_MARKER)

    # A symlink *inside* the tree root pointing to a directory outside of it. No ".." appears
    # anywhere in the request path -- this must be caught by realpath resolution, not by
    # textual rejection of "..".
    escape_link = root / "escape"
    escape_link.symlink_to(outside, target_is_directory=True)
    stub_remote.get_distro.return_value = _distro_dict(str(root))

    resp, body = _call(_environ("/tree/mydistro/escape/secret.txt"))

    assert resp.status == "403 Forbidden"
    assert SECRET_MARKER.encode() not in body
    assert (
        "../" not in "/tree/mydistro/escape/secret.txt"
    )  # sanity: no textual ".." used


def test_symlinked_file_escape_is_rejected(
    tmp_path: Path, stub_remote: MagicMock
) -> None:
    """A symlinked *file* (not just a directory) inside the root pointing outside must also be
    rejected, exercised via a direct file request."""
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret.txt"
    secret.write_text(SECRET_MARKER)

    link = root / "innocuous.txt"
    link.symlink_to(secret)
    stub_remote.get_distro.return_value = _distro_dict(str(root))

    resp, body = _call(_environ("/tree/mydistro/innocuous.txt"))

    assert resp.status == "403 Forbidden"
    assert SECRET_MARKER.encode() not in body


def test_traversal_guard_helper_functions_directly(tmp_path: Path) -> None:
    """
    Exercise :func:`resolve_within_root` and :func:`is_safe_path` directly against a real
    filesystem layout (belt-and-suspenders on top of the end-to-end tests above).
    """
    root = tmp_path / "root"
    root.mkdir()
    (root / "child.txt").write_text("ok")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text(SECRET_MARKER)

    # Legitimate access.
    assert files.resolve_within_root(str(root), "child.txt") == str(
        (root / "child.txt").resolve()
    )

    # Textual traversal.
    assert files.resolve_within_root(str(root), "../outside/secret.txt") is None

    # Symlink escape.
    link = root / "escape"
    link.symlink_to(outside, target_is_directory=True)
    assert files.resolve_within_root(str(root), "escape/secret.txt") is None

    # The root itself.
    assert files.resolve_within_root(str(root), "") == str(root.resolve())


def test_is_safe_path_rejects_sibling_with_shared_prefix() -> None:
    """
    A path like ``/tmp/root-evil`` must not be considered "under" ``/tmp/root`` just because it
    textually starts with the same characters -- the check must be prefix-plus-separator, not a
    naive ``str.startswith``.
    """
    assert files.is_safe_path("/tmp/root", "/tmp/root-evil") is False
    assert files.is_safe_path("/tmp/root", "/tmp/root") is True
    assert files.is_safe_path("/tmp/root", "/tmp/root/child") is True
    assert files.is_safe_path("/tmp/root", "/tmp/other") is False


# --------------------------------------------------------------------------------------------
# Directory listing
# --------------------------------------------------------------------------------------------


def test_directory_listing_with_trailing_slash(
    tmp_path: Path, stub_remote: MagicMock
) -> None:
    root = tmp_path / "tree"
    root.mkdir()
    (root / "repodata").mkdir()
    (root / "repodata" / "repomd.xml").write_text("x")
    (root / "Packages").mkdir()
    (root / ".hidden").write_text("secret dotfile")
    stub_remote.get_distro.return_value = _distro_dict(str(root))

    resp, body = _call(_environ("/tree/mydistro/"))

    assert resp.status == "200 OK"
    assert resp.header("Content-Type") == "text/html; charset=utf-8"
    text = body.decode("utf-8")
    assert "repodata/" in text
    assert "Packages/" in text
    assert ".hidden" not in text


def test_directory_without_trailing_slash_redirects(
    tmp_path: Path, stub_remote: MagicMock
) -> None:
    root = tmp_path / "tree"
    (root / "repodata").mkdir(parents=True)
    stub_remote.get_distro.return_value = _distro_dict(str(root))

    resp, body = _call(_environ("/tree/mydistro/repodata"))

    assert resp.status == "301 Moved Permanently"
    assert resp.header("Location") == "/cblr/svc/tree/mydistro/repodata/"
    assert body == b""


def test_distro_root_without_trailing_slash_redirects(
    tmp_path: Path, stub_remote: MagicMock
) -> None:
    root = tmp_path / "tree"
    root.mkdir()
    stub_remote.get_distro.return_value = _distro_dict(str(root))

    resp, _ = _call(_environ("/tree/mydistro"))

    assert resp.status == "301 Moved Permanently"
    assert resp.header("Location") == "/cblr/svc/tree/mydistro/"


# --------------------------------------------------------------------------------------------
# Metadata cache
# --------------------------------------------------------------------------------------------


def test_metadata_cache_reuses_lookup_within_ttl(
    tmp_path: Path, stub_remote: MagicMock
) -> None:
    root_a = tmp_path / "a"
    root_a.mkdir()
    (root_a / "f.txt").write_text("a")
    root_b = tmp_path / "b"
    root_b.mkdir()
    (root_b / "f.txt").write_text("b")

    def fake_get_distro(name: str) -> Dict[str, Any]:
        return _distro_dict(str(root_a) if name == "distro-a" else str(root_b))

    stub_remote.get_distro.side_effect = fake_get_distro

    resp1, body1 = _call(_environ("/tree/distro-a/f.txt"))
    resp2, body2 = _call(_environ("/tree/distro-a/f.txt"))

    assert resp1.status == "200 OK"
    assert resp2.status == "200 OK"
    assert body1 == b"a"
    assert body2 == b"a"
    assert stub_remote.get_distro.call_count == 1

    resp3, body3 = _call(_environ("/tree/distro-b/f.txt"))

    assert resp3.status == "200 OK"
    assert body3 == b"b"
    assert stub_remote.get_distro.call_count == 2


# --------------------------------------------------------------------------------------------
# HTTP method handling
# --------------------------------------------------------------------------------------------


def test_head_request_has_empty_body_but_full_headers(
    tmp_path: Path, stub_remote: MagicMock
) -> None:
    """
    A ``HEAD`` request must run through the same resolution/header-computation logic as ``GET``
    (so ``Content-Length``/``Content-Type`` reflect the full file), but must not return a body.
    """
    root = tmp_path / "tree"
    (root / "repodata").mkdir(parents=True)
    content = b"<repomd>hello world</repomd>"
    (root / "repodata" / "repomd.xml").write_bytes(content)
    stub_remote.get_distro.return_value = _distro_dict(str(root))

    resp, body = _call(
        _environ("/tree/mydistro/repodata/repomd.xml", REQUEST_METHOD="HEAD")
    )

    assert resp.status == "200 OK"
    assert resp.header("Content-Length") == str(len(content))
    assert "xml" in resp.header("Content-Type")
    assert body == b""


def test_head_request_on_directory_listing_has_empty_body(
    tmp_path: Path, stub_remote: MagicMock
) -> None:
    root = tmp_path / "tree"
    root.mkdir()
    (root / "repodata").mkdir()
    stub_remote.get_distro.return_value = _distro_dict(str(root))

    resp, body = _call(_environ("/tree/mydistro/", REQUEST_METHOD="HEAD"))

    assert resp.status == "200 OK"
    assert resp.header("Content-Type") == "text/html; charset=utf-8"
    assert body == b""


def test_head_request_on_missing_file_is_still_404(
    tmp_path: Path, stub_remote: MagicMock
) -> None:
    root = tmp_path / "tree"
    root.mkdir()
    stub_remote.get_distro.return_value = _distro_dict(str(root))

    resp, body = _call(
        _environ("/tree/mydistro/does/not/exist.rpm", REQUEST_METHOD="HEAD")
    )

    assert resp.status == "404 Not Found"
    assert body == b""


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "PATCH"])
def test_unsupported_methods_are_rejected_with_405(
    tmp_path: Path, stub_remote: MagicMock, method: str
) -> None:
    root = tmp_path / "tree"
    (root / "repodata").mkdir(parents=True)
    (root / "repodata" / "repomd.xml").write_bytes(b"content")
    stub_remote.get_distro.return_value = _distro_dict(str(root))

    resp, _ = _call(
        _environ("/tree/mydistro/repodata/repomd.xml", REQUEST_METHOD=method)
    )

    assert resp.status == "405 Method Not Allowed"
    # The upstream metadata lookup must not even be attempted for a rejected method.
    stub_remote.get_distro.assert_not_called()


# --------------------------------------------------------------------------------------------
# Range parsing unit tests
# --------------------------------------------------------------------------------------------


def test_parse_range_basic() -> None:
    assert files.parse_range("bytes=0-99", 1000) == (0, 99)
    assert files.parse_range("bytes=100-", 1000) == (100, 999)
    assert files.parse_range("bytes=900-1200", 1000) == (900, 999)


def test_parse_range_suffix_and_multirange_ignored() -> None:
    # Suffix ranges and multi-range requests are treated as "unsupported, serve in full".
    assert files.parse_range("bytes=-500", 1000) is None
    assert files.parse_range("bytes=0-99,200-299", 1000) is None
    assert files.parse_range("not-bytes-at-all", 1000) is None


def test_parse_range_unsatisfiable() -> None:
    with pytest.raises(files.RangeUnsatisfiable):
        files.parse_range("bytes=1000-", 1000)


# --------------------------------------------------------------------------------------------
# _build_remote() xmlrpc_host resolution (split-container support)
# --------------------------------------------------------------------------------------------


def _write_settings(tmp_path: Path, **extra: Any) -> Path:
    settings_path = tmp_path / "settings.yaml"
    content: Dict[str, Any] = {"xmlrpc_port": 25151}
    content.update(extra)
    settings_path.write_text(
        "\n".join(f"{key}: {value!r}" for key, value in content.items()),
        encoding="UTF-8",
    )
    return settings_path


@pytest.fixture
def capture_server_url(monkeypatch: pytest.MonkeyPatch) -> Dict[str, Any]:
    """
    Replace ``xmlrpc.client.Server`` with a stub that records the URL it was constructed
    with, instead of actually building a ``ServerProxy`` (whose target host is otherwise
    only reachable via a name-mangled private attribute).
    """
    captured: Dict[str, Any] = {}

    def fake_server(url: str, **kwargs: Any) -> MagicMock:
        captured["url"] = url
        captured["kwargs"] = kwargs
        return MagicMock()

    monkeypatch.setattr(xmlrpc.client, "Server", fake_server)
    return captured


def test_build_remote_defaults_to_localhost_when_unset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capture_server_url: Dict[str, Any],
) -> None:
    """
    Neither the settings file nor the environment variable set an xmlrpc_host - the
    default must be "127.0.0.1", i.e. today's exact non-containerized behavior.
    """
    settings_path = _write_settings(tmp_path)
    monkeypatch.setattr(files, "_SETTINGS_PATH", str(settings_path))
    monkeypatch.delenv("COBBLER_XMLRPC_HOST", raising=False)

    files._build_remote()  # pylint: disable=protected-access  # type: ignore[reportPrivateUsage]

    assert capture_server_url["url"] == "http://127.0.0.1:25151"


def test_build_remote_uses_settings_value_when_env_var_unset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capture_server_url: Dict[str, Any],
) -> None:
    settings_path = _write_settings(tmp_path, xmlrpc_host="cobblerd")
    monkeypatch.setattr(files, "_SETTINGS_PATH", str(settings_path))
    monkeypatch.delenv("COBBLER_XMLRPC_HOST", raising=False)

    files._build_remote()  # pylint: disable=protected-access  # type: ignore[reportPrivateUsage]

    assert capture_server_url["url"] == "http://cobblerd:25151"


def test_build_remote_env_var_takes_precedence_over_settings_value(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capture_server_url: Dict[str, Any],
) -> None:
    settings_path = _write_settings(tmp_path, xmlrpc_host="cobblerd")
    monkeypatch.setattr(files, "_SETTINGS_PATH", str(settings_path))
    monkeypatch.setenv("COBBLER_XMLRPC_HOST", "from-env")

    files._build_remote()  # pylint: disable=protected-access  # type: ignore[reportPrivateUsage]

    assert capture_server_url["url"] == "http://from-env:25151"


# --------------------------------------------------------------------------------------------
# /httpboot and /images static routes (Task 2): serve tftproot/grub content directly through
# Gunicorn instead of Apache's ``Alias /httpboot @@tftproot@@/grub`` / ``Alias /images
# @@tftproot@@/grub/images`` (cobbler/data/config/apache/cobbler.conf), which the containerized
# Traefik proxy can't replicate off disk. These reuse the exact same
# resolve_within_root/_serve_file/_list_directory guards as the /tree/... route above -- these
# tests are deliberately shaped like their /tree/... twins.
# --------------------------------------------------------------------------------------------


def _write_tftpboot_settings(tmp_path: Path, tftpboot_location: str) -> Path:
    settings_path = tmp_path / "settings.yaml"
    settings_path.write_text(
        f"tftpboot_location: {tftpboot_location!r}\n",
        encoding="UTF-8",
    )
    return settings_path


def test_httpboot_serves_file_from_grub_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tftpboot_root = tmp_path / "tftpboot"
    grub_dir = tftpboot_root / "grub"
    grub_dir.mkdir(parents=True)
    content = b"grub config content"
    (grub_dir / "grub.cfg").write_bytes(content)
    settings_path = _write_tftpboot_settings(tmp_path, str(tftpboot_root))
    monkeypatch.setattr(files, "_SETTINGS_PATH", str(settings_path))

    resp, body = _call(_environ("/httpboot/grub.cfg"), app=files.httpboot_application)

    assert resp.status == "200 OK"
    assert body == content


def test_images_serves_file_from_grub_images_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tftpboot_root = tmp_path / "tftpboot"
    images_dir = tftpboot_root / "grub" / "images"
    images_dir.mkdir(parents=True)
    content = b"fake iso bytes"
    (images_dir / "boot.img").write_bytes(content)
    settings_path = _write_tftpboot_settings(tmp_path, str(tftpboot_root))
    monkeypatch.setattr(files, "_SETTINGS_PATH", str(settings_path))

    resp, body = _call(_environ("/images/boot.img"), app=files.images_application)

    assert resp.status == "200 OK"
    assert body == content


def test_httpboot_range_get_returns_206(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tftpboot_root = tmp_path / "tftpboot"
    grub_dir = tftpboot_root / "grub"
    grub_dir.mkdir(parents=True)
    content = bytes(range(256))
    (grub_dir / "big.bin").write_bytes(content)
    settings_path = _write_tftpboot_settings(tmp_path, str(tftpboot_root))
    monkeypatch.setattr(files, "_SETTINGS_PATH", str(settings_path))

    resp, body = _call(
        _environ("/httpboot/big.bin", HTTP_RANGE="bytes=0-99"),
        app=files.httpboot_application,
    )

    assert resp.status == "206 Partial Content"
    assert resp.header("Content-Range") == f"bytes 0-99/{len(content)}"
    assert body == content[0:100]


def test_httpboot_textual_traversal_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tftpboot_root = tmp_path / "tftpboot"
    (tftpboot_root / "grub").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text(SECRET_MARKER)
    settings_path = _write_tftpboot_settings(tmp_path, str(tftpboot_root))
    monkeypatch.setattr(files, "_SETTINGS_PATH", str(settings_path))

    resp, body = _call(
        _environ("/httpboot/../../outside/secret.txt"), app=files.httpboot_application
    )

    assert resp.status == "403 Forbidden"
    assert SECRET_MARKER.encode() not in body


def test_images_textual_traversal_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tftpboot_root = tmp_path / "tftpboot"
    (tftpboot_root / "grub" / "images").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text(SECRET_MARKER)
    settings_path = _write_tftpboot_settings(tmp_path, str(tftpboot_root))
    monkeypatch.setattr(files, "_SETTINGS_PATH", str(settings_path))

    resp, body = _call(
        _environ("/images/../../../outside/secret.txt"), app=files.images_application
    )

    assert resp.status == "403 Forbidden"
    assert SECRET_MARKER.encode() not in body


def test_httpboot_symlink_escape_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tftpboot_root = tmp_path / "tftpboot"
    grub_dir = tftpboot_root / "grub"
    grub_dir.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text(SECRET_MARKER)
    (grub_dir / "escape").symlink_to(outside, target_is_directory=True)
    settings_path = _write_tftpboot_settings(tmp_path, str(tftpboot_root))
    monkeypatch.setattr(files, "_SETTINGS_PATH", str(settings_path))

    resp, body = _call(
        _environ("/httpboot/escape/secret.txt"), app=files.httpboot_application
    )

    assert resp.status == "403 Forbidden"
    assert SECRET_MARKER.encode() not in body


def test_httpboot_missing_file_is_404(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tftpboot_root = tmp_path / "tftpboot"
    (tftpboot_root / "grub").mkdir(parents=True)
    settings_path = _write_tftpboot_settings(tmp_path, str(tftpboot_root))
    monkeypatch.setattr(files, "_SETTINGS_PATH", str(settings_path))

    resp, _ = _call(
        _environ("/httpboot/does/not/exist"), app=files.httpboot_application
    )

    assert resp.status == "404 Not Found"


def test_httpboot_directory_listing_with_trailing_slash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tftpboot_root = tmp_path / "tftpboot"
    grub_dir = tftpboot_root / "grub"
    (grub_dir / "themes").mkdir(parents=True)
    settings_path = _write_tftpboot_settings(tmp_path, str(tftpboot_root))
    monkeypatch.setattr(files, "_SETTINGS_PATH", str(settings_path))

    resp, body = _call(_environ("/httpboot/"), app=files.httpboot_application)

    assert resp.status == "200 OK"
    assert "themes/" in body.decode("utf-8")


def test_httpboot_directory_without_trailing_slash_redirects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tftpboot_root = tmp_path / "tftpboot"
    (tftpboot_root / "grub" / "themes").mkdir(parents=True)
    settings_path = _write_tftpboot_settings(tmp_path, str(tftpboot_root))
    monkeypatch.setattr(files, "_SETTINGS_PATH", str(settings_path))

    resp, body = _call(_environ("/httpboot/themes"), app=files.httpboot_application)

    assert resp.status == "301 Moved Permanently"
    assert resp.header("Location") == "/httpboot/themes/"
    assert body == b""


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "PATCH"])
def test_httpboot_unsupported_methods_are_rejected_with_405(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, method: str
) -> None:
    tftpboot_root = tmp_path / "tftpboot"
    (tftpboot_root / "grub").mkdir(parents=True)
    settings_path = _write_tftpboot_settings(tmp_path, str(tftpboot_root))
    monkeypatch.setattr(files, "_SETTINGS_PATH", str(settings_path))

    resp, _ = _call(
        _environ("/httpboot/grub.cfg", REQUEST_METHOD=method),
        app=files.httpboot_application,
    )

    assert resp.status == "405 Method Not Allowed"


def test_httpboot_head_request_has_empty_body(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tftpboot_root = tmp_path / "tftpboot"
    grub_dir = tftpboot_root / "grub"
    grub_dir.mkdir(parents=True)
    content = b"grub config content"
    (grub_dir / "grub.cfg").write_bytes(content)
    settings_path = _write_tftpboot_settings(tmp_path, str(tftpboot_root))
    monkeypatch.setattr(files, "_SETTINGS_PATH", str(settings_path))

    resp, body = _call(
        _environ("/httpboot/grub.cfg", REQUEST_METHOD="HEAD"),
        app=files.httpboot_application,
    )

    assert resp.status == "200 OK"
    assert resp.header("Content-Length") == str(len(content))
    assert body == b""
