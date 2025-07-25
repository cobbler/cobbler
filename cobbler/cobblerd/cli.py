"""
Module for the CLI logic of the Cobbler backend.
"""

import argparse
import pathlib

from cobbler.cobblerd.distro_options import get_distro_options

SETUP_SCOPES = ["full", "core", "systemd", "nginx", "apache", "bashcompletion", "man"]
DISTRO_OPTIONS = get_distro_options()


def cli_generate_main_parser() -> argparse.ArgumentParser:
    """
    Generates the main CLI parser for the Cobbler daemon.
    """
    op = argparse.ArgumentParser()
    subparsers = op.add_subparsers(dest="subparser_name")
    cli_generate_setup_parser(subparsers)
    op.set_defaults(daemonize=True, log_level=None)
    op.add_argument(
        "-B",
        "--daemonize",
        dest="daemonize",
        action="store_true",
        help="run in background (default)",
    )
    op.add_argument(
        "-F",
        "--no-daemonize",
        dest="daemonize",
        action="store_false",
        help="run in foreground (do not daemonize)",
    )
    op.add_argument(
        "-f", "--log-file", dest="log_file", metavar="NAME", help="file to log to"
    )
    op.add_argument(
        "-l",
        "--log-level",
        dest="log_level",
        metavar="LEVEL",
        help="log level (ie. INFO, WARNING, ERROR, CRITICAL)",
    )
    op.add_argument(
        "--config",
        "-c",
        help="The location of the Cobbler configuration file.",
        default="/etc/cobbler/settings.yaml",
    )
    op.add_argument(
        "--enable-automigration",
        help='If given, overrule setting from "settings.yaml" and execute automigration.',
        dest="automigration",
        action="store_true",
    )
    op.add_argument(
        "--disable-automigration",
        help='If given, overrule setting from "settings.yaml" and do not execute automigration.',
        dest="automigration",
        action="store_false",
    )
    op.set_defaults(automigration=None)
    return op


def cli_generate_setup_parser(
    parent_parser: "argparse._SubParsersAction[argparse.ArgumentParser]",  # type: ignore[reportPrivateUsage]
) -> None:
    """
    Generates the setup parser.
    """
    setup_parser = parent_parser.add_parser(
        "setup",
        help="Setup the cobbler daemon. All paths are being prefix with the '--base-dir' path.",
    )
    setup_parser.add_argument(
        "--base-dir",
        help="Base directory for installing files.",
        type=pathlib.Path,
        default=pathlib.Path("/"),
    )
    setup_parser.add_argument(
        "--mode",
        choices=SETUP_SCOPES,
        default="full",
    )
    setup_parser.add_argument(
        "--exlude-modes",
        nargs="*",
        default=[],
        choices=SETUP_SCOPES,
    )
    setup_parser.add_argument(
        "--cobbler-config-directory",
        type=pathlib.Path,
        default=DISTRO_OPTIONS.etcpath,
    )
    setup_parser.add_argument(
        "--cobbler-data-directory",
        type=pathlib.Path,
        default=DISTRO_OPTIONS.libpath,
    )
    setup_parser.add_argument(
        "--cobbler-log-directory",
        type=pathlib.Path,
        default=(DISTRO_OPTIONS.logpath / "cobbler"),
    )
    setup_parser.add_argument(
        "--man-directory",
        type=pathlib.Path,
        default=DISTRO_OPTIONS.docpath,
    )
    setup_parser.add_argument(
        "--systemd-directory",
        type=pathlib.Path,
        default=pathlib.Path("/etc/systemd/system"),
    )
    setup_parser.add_argument(
        "--nginx-directory",
        type=pathlib.Path,
        default=pathlib.Path("/etc/nginx"),
    )
    setup_parser.add_argument(
        "--apache-directory",
        type=pathlib.Path,
        default=DISTRO_OPTIONS.webrootconfig,
    )
    setup_parser.add_argument(
        "--bash-completion-directory",
        type=pathlib.Path,
        default=DISTRO_OPTIONS.completion_path,
    )
    setup_parser.add_argument(
        "--logrotate-directory",
        type=pathlib.Path,
        default=pathlib.Path("/etc/logrotate.d/"),
    )
    setup_parser.add_argument(
        "--tftp-directory",
        type=pathlib.Path,
        default=DISTRO_OPTIONS.tftproot,
    )
    setup_parser.add_argument(
        "--web-directory",
        type=pathlib.Path,
        default=(DISTRO_OPTIONS.webroot / "cobbler"),
    )
