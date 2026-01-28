#!/usr/bin/python3

"""
Script to download an ISO, import it into Cobbler and then create a System with a single network interface. Primary
use-case is testing Cobbler inside a virtulized environment.
"""

import argparse
import logging
import os
import subprocess
import time
from typing import TYPE_CHECKING
from xmlrpc.client import ServerProxy

import requests

if TYPE_CHECKING:
    from cobbler.remote import CobblerXMLRPCInterface

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def wait_task_end(tid: str, remote: "CobblerXMLRPCInterface") -> None:
    """
    Wait that a given Cobbler Task has finished.
    """
    timeout = 0
    # "complete" is the constant: EVENT_COMPLETE from cobbler.remote
    while remote.get_task_status(tid)[2] != "complete":
        if remote.get_task_status(tid)[2] == "failed":
            logger.warning("Task %s failed", tid)
            return
        print(f"task {tid} status: {remote.get_task_status(tid)}")
        time.sleep(5)
        timeout += 5
        if timeout == 60:
            logger.warning('Task "%s" failed to complete!', tid)
            return


def download_iso(url: str, path: str) -> str:
    """
    Download an ISO from a given HTTP URL.

    :returns: The local filename or an empty string in case of an error.
    """
    # Taken from: https://stackoverflow.com/a/16696317/4730773
    local_filename = os.path.join(path, url.split("/")[-1])
    if os.path.exists(local_filename):
        logger.info("ISO already downlaoded already exists!")
        return ""
    # NOTE the stream=True parameter below
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(local_filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                # If you have chunk encoded response uncomment if and set chunk_size parameter to None.
                # if chunk:
                f.write(chunk)
    return local_filename


def mount_iso(path: str, target_folder: str) -> None:
    """
    Mount an ISO to a given empty target folder.
    """
    if not os.path.isdir(target_folder):
        logger.error("target_folder must be an existing folder!")
        return

    if len(os.listdir(target_folder)) > 0:
        logger.error("target_folder must be empty!")
        return

    subprocess.call(["mount", "-o", "loop,ro", path, target_folder])


def verify_iso_mounted(path: str) -> bool:
    """
    Verify that a given path is a mounted ISO.
    """
    rc = subprocess.call(["mountpoint", "-q", path])
    if rc == 0:
        return True
    if rc == -1:
        logger.error("Failure when calling mountpoint!")
    if rc == 32:
        logger.info("ISO wasn't mounted!")
    return False


def cobbler_import_iso(
    cobbler_api: "CobblerXMLRPCInterface", token: str, name: str, path: str
) -> None:
    """
    Import ISO into Cobbler.
    """
    tid = cobbler_api.background_import(
        {
            "name": name,
            "path": path,
        },
        token,
    )
    wait_task_end(tid, cobbler_api)


def cobbler_system_create(
    cobbler_api: "CobblerXMLRPCInterface",
    token: str,
    system_name: str,
    profile_uid: str,
) -> str:
    """
    Create System inside Cobbler.
    """
    sid = cobbler_api.new_system(token)
    cobbler_api.modify_system(sid, ["name"], system_name, token)
    cobbler_api.modify_system(sid, ["profile"], profile_uid, token)
    cobbler_api.save_system(sid, token, "new")
    return sid


def cobbler_system_modify(
    cobbler_api: "CobblerXMLRPCInterface",
    token: str,
    sid: str,
    property_name: str,
    value: str,
) -> None:
    """
    Modify a System inside Cobbler.
    """
    cobbler_api.modify_system(sid, property_name.split("."), value, token)


def cobbler_network_interface_create(
    cobbler_api: "CobblerXMLRPCInterface",
    token: str,
    interface_name: str,
    system_uid: str,
    mac_address: str,
) -> str:
    """
    Create Network Interface in Cobbler for a System.
    """
    nid = cobbler_api.new_network_interface(system_uid, token)
    cobbler_api.modify_network_interface(nid, ["name"], interface_name, token)
    cobbler_api.modify_network_interface(nid, ["mac_address"], mac_address, token)
    cobbler_api.save_network_interface(nid, token, "new")
    return nid


def cobbler_network_interface_modify(
    cobbler_api: "CobblerXMLRPCInterface",
    token: str,
    nid: str,
    property_name: str,
    value: str,
) -> None:
    """
    Modify a Network Interface in Cobbler for a System.
    """
    cobbler_api.modify_network_interface(nid, property_name.split("."), value, token)


def cobbler_mkloaders(cobbler_api: "CobblerXMLRPCInterface", token: str) -> None:
    """
    Call Cobbler mkloaders
    """
    tid = cobbler_api.background_mkloaders({}, token)
    wait_task_end(tid, cobbler_api)


def cobbler_sync_full(cobbler_api: "CobblerXMLRPCInterface", token: str) -> None:
    """
    Call Cobbler Sync
    """
    tid = cobbler_api.background_sync({}, token)
    wait_task_end(tid, cobbler_api)


def main() -> None:
    """
    Main entrypoint for script
    """
    cobbler_api: "CobblerXMLRPCInterface" = ServerProxy("http://127.0.0.1/cobbler_api")  # type: ignore
    token = cobbler_api.login("cobbler", "cobbler")

    parser = argparse.ArgumentParser(description="Cobbler Bootstrap Script")
    subparsers = parser.add_subparsers(dest="subparser_name")
    parser_download_iso = subparsers.add_parser("download_iso")
    parser_download_iso.add_argument("--url", required=True)
    parser_download_iso.add_argument("--path", required=True)
    parser_mount_iso = subparsers.add_parser("mount_iso")
    parser_mount_iso.add_argument("--path", required=True)
    parser_mount_iso.add_argument("--target-folder", required=True)
    parser_create_system = subparsers.add_parser("create_system")
    parser_create_system.add_argument("--system-name", required=True)
    parser_create_system.add_argument("--profile-uid", required=True)
    parser_modify_system = subparsers.add_parser("modify_system")
    parser_modify_system.add_argument("--system-uid", required=True)
    parser_modify_system.add_argument("--key", required=True)
    parser_modify_system.add_argument("--value", required=True)
    parser_create_network_interface = subparsers.add_parser("create_network_interface")
    parser_create_network_interface.add_argument(
        "--network-interface-name", required=True
    )
    parser_create_network_interface.add_argument("--system-uid", required=True)
    parser_create_network_interface.add_argument("--mac-address", required=True)
    parser_modify_network_interface = subparsers.add_parser("modify_network_interface")
    parser_modify_network_interface.add_argument(
        "--network-interface-uid", required=True
    )
    parser_modify_network_interface.add_argument("--key", required=True)
    parser_modify_network_interface.add_argument("--value", required=True)
    subparsers.add_parser("sync")
    subparsers.add_parser("mkloaders")
    parser_bootstrap = subparsers.add_parser("bootstrap")
    parser_bootstrap.add_argument("--iso-url", action="append")
    parser_bootstrap.add_argument("--iso-name", action="append")
    parser_bootstrap.add_argument("--download-folder")
    parser_bootstrap.add_argument("--mount-folder")
    parser_bootstrap.add_argument("--system-name", action="append")
    parser_bootstrap.add_argument("--profile-name", action="append")
    parser_bootstrap.add_argument("--mac-address", action="append")
    parser_bootstrap.add_argument("--ipv4-address", action="append")
    parser_autoinstall = subparsers.add_parser("generate_autoinstall")
    parser_autoinstall.add_argument("--obj-type", required=True)
    parser_autoinstall.add_argument("--obj-name", required=True)
    parser_autoinstall.add_argument("--obj-attribute", required=True)
    parser_autoinstall.add_argument("--file-name", required=True)
    parser_autoinstall.add_argument("--subfile-name", required=True)

    namespace = parser.parse_args()
    if namespace.subparser_name == "download_iso":
        download_iso(namespace.url, namespace.path)
    elif namespace.subparser_name == "mount_iso":
        if verify_iso_mounted(namespace.target_folder):
            logger.warning("ISO already mounted!")
            return
        mount_iso(namespace.path, namespace.target_folder)
    elif namespace.subparser_name == "create_system":
        cobbler_system_create(
            cobbler_api,
            token,
            namespace.system_name,
            namespace.profile_uid,
        )
    elif namespace.subparser_name == "modify_system":
        cobbler_system_modify(
            cobbler_api,
            token,
            namespace.system_uid,
            namespace.key,
            namespace.value,
        )
        cobbler_api.save_system(namespace.system_uid, token)
    elif namespace.subparser_name == "create_network_interface":
        cobbler_network_interface_create(
            cobbler_api,
            token,
            namespace.network_interface_name,
            namespace.system_uid,
            namespace.mac_address,
        )
    elif namespace.subparser_name == "modify_network_interface":
        cobbler_network_interface_modify(
            cobbler_api,
            token,
            namespace.network_interface_uid,
            namespace.key,
            namespace.value,
        )
        cobbler_api.save_network_interface(namespace.network_interface_uid, token)
    elif namespace.subparser_name == "sync":
        cobbler_sync_full(cobbler_api, token)
    elif namespace.subparser_name == "mkloaders":
        cobbler_mkloaders(cobbler_api, token)
    elif namespace.subparser_name == "bootstrap":
        # 0. Verify Args
        logger.info("Verifying args")
        system_len = len(namespace.system_name)
        if not any(
            [
                bool(len(namespace.profile_name) == system_len),
                bool(len(namespace.mac_address) == system_len),
            ]
        ):
            logger.warning(
                "Number of System Names, Profile Names and MAC Addresses must match!"
            )
            return
        iso_url_len = len(namespace.iso_url)
        if not any(
            [
                bool(iso_url_len == len(namespace.iso_name)),
                bool(iso_url_len == len(namespace.ipv4_address)),
            ]
        ):
            logger.warning("Number of ISO URLs and ISO Names must match!")
            return
        # 1. Download ISOs
        logger.info("Downloading ISOs")
        for iso in namespace.iso_url:
            download_iso(iso, namespace.download_folder)
        # 2. Mount ISOs
        logger.info("Mounting ISOs")
        for idx, iso in enumerate(os.listdir(str(namespace.download_folder))):
            full_iso_path = os.path.join(namespace.download_folder, iso)
            iso_mountpoint = os.path.join(
                str(namespace.mount_folder),
                namespace.iso_name[idx],
            )
            if verify_iso_mounted(iso_mountpoint):
                logger.warning("ISO already mounted!")
                continue
            mount_iso(full_iso_path, iso_mountpoint)
        # 3. Import ISO
        for idx, iso in enumerate(os.listdir(str(namespace.mount_folder))):
            full_iso_path = os.path.join(namespace.mount_folder, iso)
            cobbler_import_iso(
                cobbler_api,
                token,
                namespace.iso_name[idx],
                full_iso_path,
            )
        # 4. Create Systems
        logger.info("Creating systems")
        for idx, system_name in enumerate(namespace.system_name):
            cobbler_system_create(
                cobbler_api,
                token,
                system_name,
                namespace.profile_name[idx],
            )
        # 5. Create Network Interfaces
        logger.info("Creating network interfaces")
        for idx, system_name in enumerate(namespace.system_name):
            sys_id = cobbler_api.get_system_handle(system_name)
            cobbler_network_interface_create(
                cobbler_api,
                token,
                "default",
                sys_id,
                namespace.mac_address[idx],
            )
        # 6. Create Template for DHCP
        logger.info("Creating DHCP template record")
        tid = cobbler_api.new_template(token)
        cobbler_api.modify_template(tid, ["name"], "dhcpv4", token)
        cobbler_api.modify_template(tid, ["template_type"], "cheetah", token)
        cobbler_api.modify_template(tid, ["uri", "schema"], "file", token)
        cobbler_api.modify_template(
            tid,
            ["uri", "path"],
            "/var/lib/cobbler/templates/dhcp4.template",
            token,
        )
        cobbler_api.modify_template(tid, ["tags"], ["dhcpv4"], token)
        cobbler_api.save_template(tid, token, "new")
        # 7. Mkloaders
        logger.info("Generating bootloaders")
        cobbler_mkloaders(cobbler_api, token)
        # 8. Sync
        logger.info("Creating TFTP-Tree")
        cobbler_sync_full(cobbler_api, token)
    elif namespace.subparser_name == "generate_autoinstall":
        autoinstall = cobbler_api.generate_autoinstall(
            namespace.obj_name,
            namespace.obj_type,
            namespace.obj_attribute,
            namespace.file_name,
            namespace.subfile_name,
        )
        print("------------")
        print(autoinstall)
        print("------------")
    else:
        logger.info("Unkown subparser!")
        return


if __name__ == "__main__":
    main()
