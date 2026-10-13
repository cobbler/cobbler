"""
Module for setting up Cobbler daemon configuration files, directories, and templates.

This module provides functions to copy resource files, template configuration files, and create required directory
structures for Cobbler's operation. It supports setup for Apache, Nginx, systemd, logrotate, manpages, and other
components based on distribution options and installation scope.
"""

import pathlib
from typing import TYPE_CHECKING, List

from libcobblersignatures import Signatures
from libcobblersignatures.enums import ExportTypes, ImportTypes

from cobbler.utils import filesystem_helpers

try:
    from importlib.resources import files  # type: ignore
except ImportError:
    from importlib_resources import files  # type: ignore

if TYPE_CHECKING:
    from cobbler.cobblerd.distro_options import DistroOptions

    try:
        from importlib.abc import Traversable
    except ImportError:
        from importlib_resources.abc import Traversable  # type: ignore


def get_path_no_root(path: pathlib.Path) -> pathlib.Path:
    """
    Strip the leading slash in case one exists.

    :param path: The path to strip a potential leading slash from.
    :return: The path without a leading slash.
    """
    my_path = str(path)
    if my_path.startswith("/"):
        return pathlib.Path(my_path[1:])
    return path


def get_prefixed_path(path: pathlib.Path, prefix: pathlib.Path) -> pathlib.Path:
    """
    Prefix the given path with a prefix.

    :param path: The path to prefix. A leading slash, if present, is stripped before prefixing.
    :param prefix: The base directory to prepend.
    :return: ``prefix`` joined with the root-stripped ``path``.
    """
    return prefix / get_path_no_root(path)


def template_file(path: pathlib.Path, context: "DistroOptions"):
    """
    This method takes a file and templates it with the magic "@@name@@" syntax.

    :param path: The path of the file to template in place.
    :param context: The options whose field values (via :meth:`DistroOptions.to_context`) are substituted for the
                     matching "@@name@@" placeholders in the file.
    """
    file_content = path.read_text(encoding="UTF-8")
    dict_context = context.to_context()
    for key, value in dict_context.items():
        file_content = file_content.replace(f"@@{key}@@", value)
    path.write_text(file_content, encoding="UTF-8")


def copy_file(src: "Traversable", dst: pathlib.Path) -> None:
    """
    Copies a file from the resource files to the destination path.

    :param src: The source file in the resource files.
    :param dst: The destination path where the file should be copied.
    """
    dst.write_text(src.read_text(encoding="UTF-8"), encoding="UTF-8")


def copy_directory(src: "Traversable", dst: pathlib.Path) -> None:
    """
    Copies a directory from the resource files to the destination path.

    :param src: The source directory in the resource files.
    :param dst: The destination path where the directory should be copied.
    """
    for file in src.iterdir():
        if file.is_dir():
            new_dst = dst / file.name
            new_dst.mkdir(parents=True, exist_ok=True)
            copy_directory(file, new_dst)
        else:
            copy_file(file, dst / file.name)


def setup_cobblerd_manpages(
    base_path: pathlib.Path,
    resource_files: "Traversable",
) -> None:
    """
    Use the embedded manpages and install them into the system.

    :param base_path: The directory under which the ``man5`` and ``man8`` subdirectories are created.
    :param resource_files: The root of the embedded data package (``cobbler.data``) that the manpages are copied
                            from.
    """
    man_directory = base_path
    man5_files = resource_files.joinpath("man").joinpath("man5")
    if man5_files.is_dir():
        man5_directory = man_directory / "man5"
        man5_directory.mkdir(parents=True, exist_ok=True)
        copy_directory(man5_files, man5_directory)
    man8_files = resource_files.joinpath("man").joinpath("man8")
    if man8_files.is_dir():
        man8_directory = man_directory / "man8"
        man8_directory.mkdir(parents=True, exist_ok=True)
        copy_directory(man8_files, man8_directory)


def setup_cobblerd_logrotate(
    base_path: pathlib.Path, resource_files: "Traversable"
) -> None:
    """
    Use the embedded logrotate configuration and install it into the system.

    :param base_path: The root directory under which the ``etc/logrotate.d`` directory is created.
    :param resource_files: The root of the embedded data package (``cobbler.data``) that the logrotate configuration
                            is copied from.
    """
    logrotate_config_file = (
        resource_files.joinpath("config").joinpath("rotate").joinpath("cobblerd_rotate")
    )
    logrotate_config_directory = base_path / "etc" / "logrotate.d"
    logrotate_config_directory.mkdir(parents=True, exist_ok=True)
    copy_file(logrotate_config_file, logrotate_config_directory / "cobblerd")


def setup_cobblerd_systemd(
    base_path: pathlib.Path, resource_files: "Traversable"
) -> None:
    """
    Use the embedded systemd service file and install it into the system.

    :param base_path: The directory the systemd service file(s) are installed into directly.
    :param resource_files: The root of the embedded data package (``cobbler.data``) that the service file(s) are
                            copied from.
    """
    systemd_service_files = resource_files.joinpath("config").joinpath("service")
    systemd_service_directory = base_path
    systemd_service_directory.mkdir(parents=True, exist_ok=True)
    copy_directory(systemd_service_files, systemd_service_directory)


def setup_cobblerd_apache(
    base_path: pathlib.Path, resource_files: "Traversable"
) -> None:
    """
    Use the embedded Apache configuration and install it into the system.

    :param base_path: The directory the Apache configuration is installed into directly.
    :param resource_files: The root of the embedded data package (``cobbler.data``) that the Apache configuration is
                            copied from.
    """
    apache_config_files = resource_files.joinpath("config").joinpath("apache")
    apache_config_directory = base_path
    apache_config_directory.mkdir(parents=True, exist_ok=True)
    copy_directory(apache_config_files, apache_config_directory)


def setup_cobblerd_nginx(
    base_path: pathlib.Path, resource_files: "Traversable"
) -> None:
    """
    Use the embedded Nginx configuration and install it into the system.

    :param base_path: The root directory under which the ``etc/nginx/cobbler`` directory is created.
    :param resource_files: The root of the embedded data package (``cobbler.data``) that the Nginx configuration is
                            copied from.
    """
    nginx_config_files = resource_files.joinpath("config").joinpath("nginx")
    nginx_config_directory = base_path / "etc" / "nginx" / "cobbler"
    nginx_config_directory.mkdir(parents=True, exist_ok=True)
    copy_directory(nginx_config_files, nginx_config_directory)


def setup_cobblerd_log_directories(base_path: pathlib.Path, apache_user: str) -> None:
    """
    Create all the directories needed for logging in the Cobbler daemon.

    :param base_path: The root log directory under which the ``cobbler`` log subdirectories (``kicklog``,
                       ``sysyslog``, ``anamon``, ``tasks``) and the web server user's own log directory are created.
    :param apache_user: The user name of the web server process; used to name its per-user log directory.
    """
    log_path = base_path / "cobbler"
    log_path.mkdir(parents=True, exist_ok=True)
    (log_path / "kicklog").mkdir(parents=True, exist_ok=True)
    (log_path / "sysyslog").mkdir(parents=True, exist_ok=True)
    (log_path / "anamon").mkdir(parents=True, exist_ok=True)
    (log_path / "tasks").mkdir(parents=True, exist_ok=True)
    (base_path / apache_user / "cobbler").mkdir(parents=True, exist_ok=True)


def setup_cobblerd(
    base_path: pathlib.Path, distro_options: "DistroOptions", scope: List[str]
) -> None:
    """
    Setup all required directories and files for the Cobbler daemon.

    :param base_path: The root directory under which all files and directories are installed (e.g. ``/`` for a
                       normal install, or a staging directory for packaging).
    :param distro_options: The distribution-specific paths and settings used to resolve destination directories and
                            to fill in templated configuration files.
    :param scope: The list of setup scopes to install (see ``SETUP_SCOPES`` in :mod:`cobbler.cobblerd.cli`, e.g.
                  ``"apache"``, ``"nginx"``, ``"systemd"``, ``"man"``); core directories and files are always
                  installed, and ``"full"`` additionally installs every optional scope.
    """
    # Directories
    # Create /etc/cobbler
    etc_path = get_prefixed_path(distro_options.etcpath, base_path)
    etc_path.mkdir(parents=True, exist_ok=True)
    # Create /var/lib/cobbler
    var_path = get_prefixed_path(distro_options.libpath, base_path)
    var_path.mkdir(parents=True, exist_ok=True)
    (var_path / "loaders").mkdir(parents=True, exist_ok=True)
    # Create /var/log/cobbler
    logpath = get_prefixed_path(distro_options.logpath, base_path)
    setup_cobblerd_log_directories(logpath, distro_options.httpd_user)

    # Files
    resource_files: "Traversable" = files("cobbler.data")  # type: ignore[reportAssignmentType]
    # Core
    cobbler_config: "Traversable" = resource_files.joinpath("config").joinpath(
        "cobbler"
    )
    copy_directory(cobbler_config, etc_path)
    # Autoinstall Content
    autoinstall_templates_path = var_path / "templates"
    autoinstall_templates_path.mkdir(parents=True, exist_ok=True)
    # Seed distro_signatures.json in /var/lib/cobbler from libcobblersignatures' built-in data, unless an admin
    # already has one (e.g. a customized file surviving an upgrade)
    signatures_filename = "distro_signatures.json"
    new_signatures_path = var_path / signatures_filename
    if not new_signatures_path.exists():
        built_in_signatures = Signatures()
        built_in_signatures.importsignatures(ImportTypes.BUILT_IN, "")
        built_in_signatures.jsontomodels()
        built_in_signatures.exportsignatures(
            ExportTypes.FILE, target=str(new_signatures_path)
        )
    # Create Apache & Nginx config
    webconfigpath = get_prefixed_path(distro_options.webconfig, base_path)
    if "apache" in scope or "full" in scope:
        setup_cobblerd_apache(webconfigpath, resource_files)
    if "nginx" in scope or "full" in scope:
        setup_cobblerd_nginx(base_path, resource_files)
    # Create logrotate config
    setup_cobblerd_logrotate(base_path, resource_files)
    # Create rsync config
    rsync_config_files: "Traversable" = resource_files.joinpath("config").joinpath(
        "rsync"
    )
    copy_directory(rsync_config_files, etc_path)
    # Create systemd service file
    systemdpath = get_prefixed_path(distro_options.systemd_dir, base_path)
    if "systemd" in scope or "full" in scope:
        setup_cobblerd_systemd(systemdpath, resource_files)
    # Create Man Pages
    if "man" in scope or "full" in scope:
        manpath = get_prefixed_path(distro_options.docpath, base_path)
        setup_cobblerd_manpages(manpath, resource_files)
    # Web Root Files
    web_root_misc_files: "Traversable" = resource_files.joinpath("misc")
    web_root_misc_directory = var_path / "misc"
    web_root_misc_directory.mkdir(parents=True, exist_ok=True)
    copy_directory(web_root_misc_files, web_root_misc_directory)
    # Trigger & collection database directories (so packages own these standard, empty directories too)
    filesystem_helpers.create_trigger_dirs(var_path)
    filesystem_helpers.create_json_database_dirs(var_path)
    # TFTP Root Files
    # TODO: Copy GRUB files into TFTP-root

    # Now template all files that need it
    configure_files = [
        (etc_path / "settings.yaml"),
        (webconfigpath / "cobbler.conf"),
        base_path / pathlib.Path("etc/nginx/cobbler/cobbler.conf"),
        systemdpath / "cobblerd.service",
    ]
    for file in configure_files:
        if file.exists():
            template_file(file, distro_options)
