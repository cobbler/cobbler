"""
TODO
"""

import pathlib
from typing import TYPE_CHECKING, List

try:
    from importlib.resources import files
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
    """
    my_path = str(path)
    if my_path.startswith("/"):
        return pathlib.Path(my_path[1:])
    return path


def get_prefixed_path(path: pathlib.Path, prefix: pathlib.Path) -> pathlib.Path:
    """
    Prefix the given path with a prefix.
    """
    return prefix / get_path_no_root(path)


def template_file(path: pathlib.Path, context: "DistroOptions"):
    """
    This method takes a file and templates it with the magic "@@name@@" syntax.
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
    """
    man_directory = base_path
    man1_files = resource_files.joinpath("man").joinpath("man1")
    man1_directory = man_directory / "man1"
    man1_directory.mkdir(parents=True, exist_ok=True)
    copy_directory(man1_files, man1_directory)
    man5_files = resource_files.joinpath("man").joinpath("man5")
    man5_directory = man_directory / "man5"
    man5_directory.mkdir(parents=True, exist_ok=True)
    copy_directory(man5_files, man5_directory)
    man8_files = resource_files.joinpath("man").joinpath("man8")
    man8_directory = man_directory / "man8"
    man8_directory.mkdir(parents=True, exist_ok=True)
    copy_directory(man8_files, man8_directory)


def setup_cobblerd_logrotate(
    base_path: pathlib.Path, resource_files: "Traversable"
) -> None:
    """
    Use the embedded logrotate configuration and install it into the system.
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
    """
    nginx_config_files = resource_files.joinpath("config").joinpath("nginx")
    nginx_config_directory = base_path / "etc" / "nginx" / "cobbler"
    nginx_config_directory.mkdir(parents=True, exist_ok=True)
    copy_directory(nginx_config_files, nginx_config_directory)


def setup_cobblerd_bash_completion(
    base_path: pathlib.Path, resource_files: "Traversable"
) -> None:
    """
    Use the embedded Bash completion file and install it into the system.
    """
    bash_completion_file = (
        resource_files.joinpath("config")
        .joinpath("bash")
        .joinpath("completion")
        .joinpath("cobbler")
    )
    bash_completion_directory = (
        base_path / "usr" / "share" / "bash-completion" / "completions"
    )
    bash_completion_directory.mkdir(parents=True, exist_ok=True)
    copy_file(bash_completion_file, bash_completion_directory / "cobbler")


def setup_cobblerd_log_directories(base_path: pathlib.Path, apache_user: str) -> None:
    """
    Create all the directories needed for logging in the Cobbler daemon.
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
    resource_files = files("cobbler.data")
    # Core
    copy_file(
        resource_files.joinpath("config").joinpath("version"), etc_path / "version"
    )
    cobbler_config = resource_files.joinpath("config").joinpath("cobbler")
    copy_directory(cobbler_config, etc_path)
    # Autoinstall Content
    autoinstall_template_files = resource_files.joinpath("autoinstall_templates")
    autoinstall_snippets_files = resource_files.joinpath("autoinstall_snippets")
    autoinstall_scripts_files = resource_files.joinpath("autoinstall_scripts")
    autoinstall_templates_path = var_path / "templates"
    autoinstall_snippets_path = var_path / "snippets"
    autoinstall_scripts_path = var_path / "scripts"
    autoinstall_templates_path.mkdir(parents=True, exist_ok=True)
    autoinstall_snippets_path.mkdir(parents=True, exist_ok=True)
    autoinstall_scripts_path.mkdir(parents=True, exist_ok=True)
    copy_directory(autoinstall_template_files, var_path / "templates")
    copy_directory(autoinstall_snippets_files, var_path / "snippets")
    copy_directory(autoinstall_scripts_files, var_path / "scripts")
    # Move distro_signatures.json to /var/lib/cobbler
    signatures_filename = "distro_signatures.json"
    (etc_path / signatures_filename).rename((var_path / signatures_filename))
    # Create GRUB configs
    bootloader_config_files = resource_files.joinpath("templates").joinpath(
        "boot_loader_conf"
    )
    boot_loader_config_directory = etc_path / "boot_loader_conf"
    boot_loader_config_directory.mkdir(parents=True, exist_ok=True)
    copy_directory(bootloader_config_files, boot_loader_config_directory)
    template_files = resource_files.joinpath("templates").joinpath("etc")
    copy_directory(template_files, etc_path)
    reporting_config_files = resource_files.joinpath("templates").joinpath("reporting")
    reporting_config_directory = etc_path / "reporting"
    reporting_config_directory.mkdir(parents=True, exist_ok=True)
    copy_directory(reporting_config_files, reporting_config_directory)
    windows_config_files = resource_files.joinpath("templates").joinpath("windows")
    windows_config_directory = etc_path / "windows"
    windows_config_directory.mkdir(parents=True, exist_ok=True)
    copy_directory(windows_config_files, windows_config_directory)
    zone_template_files = resource_files.joinpath("templates").joinpath(
        "zone_templates"
    )
    zone_template_directory = etc_path / "zone_templates"
    zone_template_directory.mkdir(parents=True, exist_ok=True)
    copy_directory(zone_template_files, zone_template_directory)
    iso_config_files = resource_files.joinpath("templates").joinpath("iso")
    iso_config_directory = etc_path / "iso"
    iso_config_directory.mkdir(parents=True, exist_ok=True)
    copy_directory(iso_config_files, iso_config_directory)
    # Create Apache & Nginx config
    webconfigpath = get_prefixed_path(distro_options.webconfig, base_path)
    if "apache" in scope or "full" in scope:
        setup_cobblerd_apache(webconfigpath, resource_files)
    if "nginx" in scope or "full" in scope:
        setup_cobblerd_nginx(base_path, resource_files)
    # Create Bash completion
    if "bashcompletion" in scope or "full" in scope:
        setup_cobblerd_bash_completion(base_path, resource_files)
    # Create Cheetah Macros
    cheetah_macros_file = (
        resource_files.joinpath("config").joinpath("cheetah").joinpath("cheetah_macros")
    )
    copy_file(cheetah_macros_file, etc_path / "cheetah_macros")
    # Create logrotate config
    setup_cobblerd_logrotate(base_path, resource_files)
    # Create rsync config
    rsync_config_files = resource_files.joinpath("config").joinpath("rsync")
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
    web_root_misc_files = resource_files.joinpath("misc")
    web_root_misc_directory = var_path / "misc"
    web_root_misc_directory.mkdir(parents=True, exist_ok=True)
    copy_directory(web_root_misc_files, web_root_misc_directory)

    # Now template all files that need it
    configure_files = [
        (etc_path / "settings.yaml"),
        (webconfigpath / "cobbler.conf"),
        base_path / pathlib.Path("etc/nginx/cobbler.conf"),
        base_path / pathlib.Path("etc/systemd/system/cobbler.service"),
    ]
    for file in configure_files:
        if file.exists():
            template_file(file, distro_options)
