"""
Create Windows boot files

To create Windows boot files, files are used that must be extracted from the distro. The ``cobbler import``"
command extracts the required files and places them where the given trigger expects them to be found.

To create boot files per profile/system, the trigger uses the following metadata from ``--autoinstall-meta``:
    * ``kernel`` - the name of the bootstrap file for profile/system, can be:
        * any filename, in the case of PXE boot without using ``wimboot`` which is not the same as the filename
          for other profiles/systems of that distro. The trigger creates it from a copy of ``pxeboot.n12``
          by replacing the ``bootmgr.exe`` string in the binary copy with the ``bootmgr`` metadata value.
          In the case of Windows XP/2003, it replaces the ``NTLDR`` string.
        * in case of PXE boot using ``wimboot``, specify the path to ``wimboot`` in the file system,
          e.g ``/var/lib/tftpboot/wimboot``
        * in case of iPXE boot using ``wimboot``, specify the path to ``wimboot`` in the file system or any
          url that supports iPXE, e.g ``http://@@http_server@@/cobbler/images/@@distro_name@@/wimboot``
    * ``bootmgr`` - filename of the Boot Manager for the profile/system. The trigger creates it by copying
      ``bootmgr.exe`` and replacing the ``BCD`` string in the binary copy with the string specified in the
      ``bcd`` metadata parameter. The filename must be exactly 11 characters long, e.g. ``bootmg1.exe``,
      ``bootmg2.exe, ..`` and not match the names for other profiles/systems of the same distro.
      For Windows XP/2003, ``setupldr.exe`` is used as the Boot Manager and the string ``winnt.sif`` is
      replaced in its copy.
    * ``bcd`` - The name of the Windows Boot Configuration Data (BCD) file for the profile/system.
      Must be exactly 3 characters and not the same as names for other profiles/systems on the same
      distro, e.g. ``000``, ``001``, etc.
    * ``winpe`` - The name of the Windows PE image file for the profile/system. The trigger copies it
      from the distro and replaces the ``/Windows/System32/startnet.cmd`` file in it with the one
      created from the ``startnet.template`` template. Filenames must be unique per the distro.
    * ``answerfile`` - the name of the answer file for the Windows installation, e.g. ``autounattend01.xml``
      or`` win01.sif`` for Windows XP/2003. The trigger creates the answerfile from the ``answerfile.template``.
      Filenames must be unique per the distro.
    * ``post_install_script`` - The name of the post-installation script file that will be run after Windows is
      installed. To run a script, its filename is substituted into the answerfile template. Any valid Windows
      commands can be used in the script, but its usual purpose is to download and run the script for the profile
      from ``http://@@http_server@@/cblr/svc/op/autoinstall/profile/@@profile_name@@``, for this the script is
      passed profile name as parameter . The post-installation script is created by a trigger from the
      ``post_inst_cmd.template`` template  in the ``sources/$OEM$/$1`` distro directory only if it exists.
      The Windows Installer copies the contents of  this directory to the target host during installation.
    * any other key/value pairs that can be used in ``startnet.template``, ``answerfile.template``,
      ``post_inst_cmd.template`` templates
"""

import binascii
import logging
import os
import re
import tempfile
from typing import TYPE_CHECKING, Any, Dict, Optional

from cobbler import templar, utils

try:
    import hivex  # type: ignore
    from hivex.hive_types import REG_BINARY  # type: ignore
    from hivex.hive_types import REG_DWORD  # type: ignore
    from hivex.hive_types import REG_MULTI_SZ  # type: ignore
    from hivex.hive_types import REG_SZ  # type: ignore

    HAS_HIVEX = True
except Exception:
    # This is only defined once in each case.
    HAS_HIVEX = False  # type: ignore

try:
    import pefile  # type: ignore

    HAS_PEFILE = True
except Exception:
    # This is only defined once in each case.
    HAS_PEFILE = False  # type: ignore

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.items.distro import Distro


ANSWERFILE_TEMPLATE_NAME = "answerfile.template"
POST_INST_CMD_TEMPLATE_NAME = "post_inst_cmd.template"
STARTNET_TEMPLATE_NAME = "startnet.template"
WIMUPDATE = "/usr/bin/wimupdate"


def register() -> Optional[str]:
    """
    This pure python trigger acts as if it were a legacy shell-trigger, but is much faster. The return of this method
    indicates the trigger type
    :return: Always ``/var/lib/cobbler/triggers/sync/post/*``
    """
    if not HAS_HIVEX:
        logging.info(
            "python3-hivex not found. If you need Automatic Windows Installation support, please install."
        )
        return None

    if not HAS_PEFILE:
        logging.info(
            "python3-pefile not found. If you need Automatic Windows Installation support, please install."
        )
        return None

    return "/var/lib/cobbler/triggers/sync/post/*"


def bcdedit(
    orig_bcd: str, new_bcd: str, wim: str, sdi: str, startoptions: Optional[str] = None
):
    """
    Create new Windows Boot Configuration Data (BCD) based on Microsoft BCD extracted from a WIM image.

    :param orig_bcd: Path to the original BCD
    :param new_bcd: Path to the new customized BCD
    :param wim: Path to the WIM image
    :param sdi: Path to the System Deployment Image (SDI)
    :param startoptions: Other BCD options
    :return:
    """

    def winpath_length(wp: str, add: int):
        wpl = add + 2 * len(wp)
        return wpl.to_bytes((wpl.bit_length() + 7) // 8, "big")

    def guid2binary(g: str):
        guid = (
            g[7]
            + g[8]
            + g[5]
            + g[6]
            + g[3]
            + g[4]
            + g[1]
            + g[2]
            + g[12]
            + g[13]
            + g[10]
            + g[11]
            + g[17]
            + g[18]
        )
        guid += (
            g[15]
            + g[16]
            + g[20]
            + g[21]
            + g[22]
            + g[23]
            + g[25]
            + g[26]
            + g[27]
            + g[28]
            + g[29]
            + g[30]
            + g[31]
        )
        guid += g[32] + g[33] + g[34] + g[35] + g[36]
        return binascii.unhexlify(guid)

    wim = wim.replace("/", "\\")
    sdi = sdi.replace("/", "\\")

    h = hivex.Hivex(orig_bcd, write=True)  # type: ignore
    root = h.root()  # type: ignore
    objs = h.node_get_child(root, "Objects")  # type: ignore

    for n in h.node_children(objs):  # type: ignore
        h.node_delete_child(n)  # type: ignore

    b = h.node_add_child(objs, "{9dea862c-5cdd-4e70-acc1-f32b344d4795}")  # type: ignore
    d = h.node_add_child(b, "Description")  # type: ignore
    h.node_set_value(d, {"key": "Type", "t": REG_DWORD, "value": b"\x02\x00\x10\x10"})  # type: ignore
    e = h.node_add_child(b, "Elements")  # type: ignore
    e1 = h.node_add_child(e, "25000004")  # type: ignore
    h.node_set_value(  # type: ignore
        e1,
        {
            "key": "Element",
            "t": REG_BINARY,
            "value": b"\x00\x00\x00\x00\x00\x00\x00\x00",
        },
    )
    e1 = h.node_add_child(e, "12000004")  # type: ignore
    h.node_set_value(  # type: ignore
        e1,
        {
            "key": "Element",
            "t": REG_SZ,
            "value": "Windows Boot Manager\0".encode(encoding="utf-16le"),
        },
    )
    e1 = h.node_add_child(e, "24000001")  # type: ignore
    h.node_set_value(  # type: ignore
        e1,
        {
            "key": "Element",
            "t": REG_MULTI_SZ,
            "value": "{65c31250-afa2-11df-8045-000c29f37d88}\0\0".encode(
                encoding="utf-16le"
            ),
        },
    )
    e1 = h.node_add_child(e, "16000048")  # type: ignore
    h.node_set_value(e1, {"key": "Element", "t": REG_BINARY, "value": b"\x01"})  # type: ignore

    b = h.node_add_child(objs, "{65c31250-afa2-11df-8045-000c29f37d88}")  # type: ignore
    d = h.node_add_child(b, "Description")  # type: ignore
    h.node_set_value(d, {"key": "Type", "t": REG_DWORD, "value": b"\x03\x00\x20\x10"})  # type: ignore
    e = h.node_add_child(b, "Elements")  # type: ignore
    e1 = h.node_add_child(e, "12000002")  # type: ignore
    h.node_set_value(  # type: ignore
        e1,
        {
            "key": "Element",
            "t": REG_SZ,
            "value": "\\windows\\system32\\winload.exe\0".encode(encoding="utf-16le"),
        },
    )
    e1 = h.node_add_child(e, "12000004")  # type: ignore
    h.node_set_value(  # type: ignore
        e1,
        {
            "key": "Element",
            "t": REG_SZ,
            "value": "Windows PE\0".encode(encoding="utf-16le"),
        },
    )
    e1 = h.node_add_child(e, "22000002")  # type: ignore
    h.node_set_value(  # type: ignore
        e1,
        {
            "key": "Element",
            "t": REG_SZ,
            "value": "\\Windows\0".encode(encoding="utf-16le"),
        },
    )
    e1 = h.node_add_child(e, "26000010")  # type: ignore
    h.node_set_value(e1, {"key": "Element", "t": REG_BINARY, "value": b"\x01"})  # type: ignore
    e1 = h.node_add_child(e, "26000022")  # type: ignore
    h.node_set_value(e1, {"key": "Element", "t": REG_BINARY, "value": b"\x01"})  # type: ignore
    e1 = h.node_add_child(e, "11000001")  # type: ignore
    guid = guid2binary("{ae5534e0-a924-466c-b836-758539a3ee3a}")
    wimval = {  # type: ignore
        "key": "Element",
        "t": REG_BINARY,
        "value": guid
        + b"\x00\x00\x00\x00\x01\x00\x00\x00"
        + winpath_length(wim, 126)
        + b"\x00\x00\x00\x00\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00"
        + winpath_length(wim, 86)
        + b"\x00\x00\x00\x05\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x48\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00"
        + wim.encode(encoding="utf_16_le")
        + b"\x00\x00",
    }
    h.node_set_value(e1, wimval)  # type: ignore
    e1 = h.node_add_child(e, "21000001")  # type: ignore
    h.node_set_value(e1, wimval)  # type: ignore

    if startoptions:
        e1 = h.node_add_child(e, "12000030")  # type: ignore
        h.node_set_value(  # type: ignore
            e1,
            {
                "key": "Element",
                "t": REG_SZ,
                "value": startoptions.join("\0").encode(encoding="utf-16le"),
            },
        )

    b = h.node_add_child(objs, "{ae5534e0-a924-466c-b836-758539a3ee3a}")  # type: ignore
    d = h.node_add_child(b, "Description")  # type: ignore
    h.node_set_value(d, {"key": "Type", "t": REG_DWORD, "value": b"\x00\x00\x00\x30"})  # type: ignore
    e = h.node_add_child(b, "Elements")  # type: ignore
    e1 = h.node_add_child(e, "12000004")  # type: ignore
    h.node_set_value(  # type: ignore
        e1,
        {
            "key": "Element",
            "t": REG_SZ,
            "value": "Ramdisk Options\0".encode(encoding="utf-16le"),
        },
    )
    e1 = h.node_add_child(e, "32000004")  # type: ignore
    h.node_set_value(  # type: ignore
        e1,
        {
            "key": "Element",
            "t": REG_SZ,
            "value": sdi.encode(encoding="utf-16le") + b"\x00\x00",
        },
    )
    e1 = h.node_add_child(e, "31000003")  # type: ignore
    h.node_set_value(  # type: ignore
        e1,
        {
            "key": "Element",
            "t": REG_BINARY,
            "value": b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x05\x00\x00\x00"
            b"\x00\x00\x00\x00\x48\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            b"\x00\x00\x00\x00\x00\x00\x00\x00",
        },
    )
    h.commit(new_bcd)  # type: ignore


def run(api: "CobblerAPI", args: Any, logger):
    """
    Runs the trigger, meaning in this case creates Windows boot files.

    :param api: The api instance of the Cobbler server. Used to look up if windows_enabled is true.
    :param args: The parameter is currently unused for this trigger.
    :return: 0 on success, otherwise an exception is risen.
    """
    settings = api.settings()
    if not settings.windows_enabled:
        return 0
    if not HAS_HIVEX:
        logger.info(
            "python3-hivex not found. If you need Automatic Windows Installation support, "
            "please install."
        )
        return 0
    if not HAS_PEFILE:
        logger.info(
            "python3-pefile not found. If you need Automatic Windows Installation support, "
            "please install."
        )
        return 0

    profiles = api.profiles()
    systems = api.systems()
    templ = templar.Templar(api)
    tgen = api.tftpgen

    with open(
        os.path.join(settings.windows_template_dir, POST_INST_CMD_TEMPLATE_NAME),
        encoding="UTF-8",
    ) as template_win:
        post_tmpl_data = template_win.read()

    with open(
        os.path.join(settings.windows_template_dir, ANSWERFILE_TEMPLATE_NAME),
        encoding="UTF-8",
    ) as template_win:
        tmpl_data = template_win.read()

    with open(
        os.path.join(settings.windows_template_dir, STARTNET_TEMPLATE_NAME),
        encoding="UTF-8",
    ) as template_start:
        tmplstart_data = template_start.read()

    def gen_win_files(distro: "Distro", meta: Dict[str, Any]):
        boot_path = os.path.join(settings.webdir, "links", distro.name, "boot")
        distro_path = distro.find_distro_path()
        distro_dir = wim_file_name = os.path.join(
            settings.tftpboot_location, "images", distro.name
        )
        web_dir = os.path.join(settings.webdir, "images", distro.name)
        is_winpe = "winpe" in meta and meta["winpe"] != ""
        is_bcd = "bcd" in meta and meta["bcd"] != ""

        kernel_name = distro.kernel
        if "kernel" in meta:
            kernel_name = meta["kernel"]

        kernel_name = os.path.basename(kernel_name)
        is_wimboot = "wimboot" in kernel_name

        if is_wimboot and "kernel" in meta and "wimboot" not in distro.kernel:
            tgen.copy_single_distro_file(
                os.path.join(settings.tftpboot_location, kernel_name), distro_dir, False
            )
            tgen.copy_single_distro_file(
                os.path.join(distro_dir, kernel_name), web_dir, True
            )

        if "post_install_script" in meta:
            post_install_dir = distro_path

            if distro.os_version not in ("xp", "2003"):
                post_install_dir = os.path.join(post_install_dir, "sources")

            post_install_dir = os.path.join(post_install_dir, "$OEM$", "$1")

            if not os.path.exists(post_install_dir):
                utils.mkdir(post_install_dir)

            data = templ.render(post_tmpl_data, meta, None)
            post_install_script = os.path.join(
                post_install_dir, meta["post_install_script"]
            )
            logger.info(f"Build post install script: {post_install_script}")
            with open(post_install_script, "w", encoding="UTF-8") as pi_file:
                pi_file.write(data)

        if "answerfile" in meta:
            data = templ.render(tmpl_data, meta, None)
            answerfile_name = os.path.join(distro_dir, meta["answerfile"])
            logger.info(f"Build answer file: {answerfile_name}")
            with open(answerfile_name, "w", encoding="UTF-8") as answerfile:
                answerfile.write(data)
            tgen.copy_single_distro_file(answerfile_name, web_dir, False)

        if "kernel" in meta and "bootmgr" in meta:
            wk_file_name = os.path.join(distro_dir, kernel_name)
            bootmgr = "bootmgr.exe"
            if ".efi" in meta["bootmgr"]:
                bootmgr = "bootmgr.efi"
            wl_file_name = os.path.join(distro_dir, meta["bootmgr"])
            tl_file_name = os.path.join(boot_path, bootmgr)

            if distro.os_version in ("xp", "2003") and not is_winpe:
                tl_file_name = os.path.join(boot_path, "setupldr.exe")

                if len(meta["bootmgr"]) != 5:
                    logger.error("The loader name should be EXACTLY 5 character")
                    return 1

                pat1 = re.compile(rb"NTLDR", re.IGNORECASE)
                pat2 = re.compile(rb"winnt\.sif", re.IGNORECASE)
                with open(tl_file_name, "rb") as file:
                    out = data = file.read()

                if "answerfile" in meta:
                    if len(meta["answerfile"]) != 9:
                        logger.error(
                            "The response file name should be EXACTLY 9 character"
                        )
                        return 1

                    out = pat2.sub(bytes(meta["answerfile"], "utf-8"), data)
            else:
                if len(meta["bootmgr"]) != 11:
                    logger.error(
                        "The Boot manager file name should be EXACTLY 11 character"
                    )
                    return 1

                bcd_name = "bcd"
                if is_bcd:
                    bcd_name = meta["bcd"]
                    if len(bcd_name) != 3:
                        logger.error("The BCD file name should be EXACTLY 3 character")
                        return 1

                if not os.path.isfile(tl_file_name):
                    logger.error(f"File not found: {tl_file_name}")
                    return 1

                pat1 = re.compile(rb"bootmgr\.exe", re.IGNORECASE)
                pat2 = re.compile(rb"(\\.B.o.o.t.\\.)(B)(.)(C)(.)(D)", re.IGNORECASE)

                bcd_name = bytes(
                    "\\g<1>"
                    + bcd_name[0]
                    + "\\g<3>"
                    + bcd_name[1]
                    + "\\g<5>"
                    + bcd_name[2],
                    "utf-8",
                )
                with open(tl_file_name, "rb") as file:
                    out = file.read()

                if not is_wimboot:
                    logger.info(f"Patching build Loader: {wl_file_name}")
                    out = pat2.sub(bcd_name, out)

            if tl_file_name != wl_file_name:
                logger.info(f"Build Loader: {wl_file_name} from {tl_file_name}")
                with open(wl_file_name, "wb+") as file:
                    file.write(out)
                tgen.copy_single_distro_file(wl_file_name, web_dir, True)

            if not is_wimboot:
                if distro.os_version not in ("xp", "2003") or is_winpe:
                    pe = pefile.PE(wl_file_name, fast_load=True)  # type: ignore
                    pe.OPTIONAL_HEADER.CheckSum = pe.generate_checksum()  # type: ignore
                    pe.write(filename=wl_file_name)  # type: ignore

                with open(distro.kernel, "rb") as file:
                    data = file.read()
                out = pat1.sub(bytes(meta["bootmgr"], "utf-8"), data)

                if wk_file_name != distro.kernel:
                    logger.info(
                        f"Build PXEBoot: {wk_file_name} from {distro.kernel}"
                    )
                    with open(wk_file_name, "wb+") as file:
                        file.write(out)
                    tgen.copy_single_distro_file(wk_file_name, web_dir, True)

        if is_bcd:
            obcd_file_name = os.path.join(boot_path, "bcd")
            bcd_file_name = os.path.join(distro_dir, meta["bcd"])
            wim_file_name = "winpe.wim"

            if not os.path.isfile(obcd_file_name):
                logger.error(f"File not found: {obcd_file_name}")
                return 1

            if is_winpe:
                wim_file_name = meta["winpe"]

            tftp_image = os.path.join("/images", distro.name)
            if is_wimboot:
                tftp_image = "/Boot"
            wim_file_name = os.path.join(tftp_image, wim_file_name)
            sdi_file_name = os.path.join(tftp_image, os.path.basename(distro.initrd))

            logger.info(
                f"Build BCD: {bcd_file_name} from {obcd_file_name} for {wim_file_name}"
            )
            bcdedit(obcd_file_name, bcd_file_name, wim_file_name, sdi_file_name)
            tgen.copy_single_distro_file(bcd_file_name, web_dir, True)

        if is_winpe:
            ps_file_name = os.path.join(distro_dir, meta["winpe"])
            wim_pl_name = os.path.join(boot_path, "winpe.wim")

            cmd = ["/usr/bin/cp", "--reflink=auto", wim_pl_name, ps_file_name]
            utils.subprocess_call(logger, cmd, shell=False)

            if os.path.exists(WIMUPDATE):
                data = templ.render(tmplstart_data, meta, None)
                with tempfile.NamedTemporaryFile() as pi_file:
                    pi_file.write(bytes(data, "utf-8"))
                    pi_file.flush()
                    cmd = ["/usr/bin/wimdir", ps_file_name, "1"]
                    wimdir_result = utils.subprocess_get(None, cmd, shell=False)
                    wimdir_file_list = wimdir_result.split("\n")
                    # grep -i for /Windows/System32/startnet.cmd
                    startnet_path = "/Windows/System32/startnet.cmd"

                    for file in wimdir_file_list:
                        if file.lower() == startnet_path.lower():
                            startnet_path = file

                    cmd = [
                        WIMUPDATE,
                        ps_file_name,
                        f"--command=add {pi_file.name} {startnet_path}",
                    ]
                    utils.subprocess_call(logger, cmd, shell=False)
            tgen.copy_single_distro_file(ps_file_name, web_dir, True)

    for profile in profiles:
        distro: Optional["Distro"] = profile.get_conceptual_parent()  # type: ignore

        if distro is None:
            raise ValueError("Distro not found!")

        if distro.breed == "windows":
            logger.info(f"Profile: {profile.name}")
            meta = utils.blender(api, False, profile)
            autoinstall_meta = meta.get("autoinstall_meta", {})
            meta.update(autoinstall_meta)
            gen_win_files(distro, meta)

    for system in systems:
        profile = system.get_conceptual_parent()
        autoinstall_meta = system.autoinstall_meta

        if not profile or not autoinstall_meta or autoinstall_meta == {}:
            continue

        distro = profile.get_conceptual_parent()  # type: ignore

        if distro and distro.breed == "windows":
            logger.info(f"System: {system.name}")
            meta = utils.blender(api, False, system)
            gen_win_files(distro, autoinstall_meta)
    return 0
