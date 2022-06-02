import os
import re
import binascii
import tempfile
from typing import Optional

import cobbler.utils as utils
import cobbler.templar as templar
import cobbler.tftpgen as tftpgen
import logging

HAS_HIVEX = True
try:
    import pefile
    import hivex
    from hivex.hive_types import REG_DWORD
    from hivex.hive_types import REG_BINARY
    from hivex.hive_types import REG_SZ
    from hivex.hive_types import REG_MULTI_SZ
except Exception:
    HAS_HIVEX = False

answerfile_template_name = "answerfile.template"
post_inst_cmd_template_name = "post_inst_cmd.template"
startnet_template_name = "startnet.template"
wimupdate = "/usr/bin/wimupdate"

logger = logging.getLogger()


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
        return

    return "/var/lib/cobbler/triggers/sync/post/*"


def bcdedit(orig_bcd, new_bcd, wim, sdi, startoptions=None):
    def winpath_length(wp, add):
        wpl = add + 2 * len(wp)
        return wpl.to_bytes((wpl.bit_length() + 7) // 8, 'big')

    def guid2binary(g):
        guid = g[7] + g[8] + g[5] + g[6] + g[3] + g[4] + g[1] + g[2] + g[12] + g[13] + g[10] + g[11] + g[17] + g[18]
        guid += g[15] + g[16] + g[20] + g[21] + g[22] + g[23] + g[25] + g[26] + g[27] + g[28] + g[29] + g[30] + g[31]
        guid += g[32] + g[33] + g[34] + g[35] + g[36]
        return binascii.unhexlify(guid)

    wim = wim.replace('/', '\\')
    sdi = sdi.replace('/', '\\')

    h = hivex.Hivex(orig_bcd, write=True)
    root = h.root()
    objs = h.node_get_child(root, "Objects")

    for n in h.node_children(objs):
        h.node_delete_child(n)

    b = h.node_add_child(objs, "{9dea862c-5cdd-4e70-acc1-f32b344d4795}")
    d = h.node_add_child(b, "Description")
    h.node_set_value(d, {"key": "Type", "t": REG_DWORD, "value": b"\x02\x00\x10\x10"})
    e = h.node_add_child(b, "Elements")
    e1 = h.node_add_child(e, "25000004")
    h.node_set_value(e1, {"key": "Element", "t": REG_BINARY, "value": b"\x1e\x00\x00\x00\x00\x00\x00\x00"})
    e1 = h.node_add_child(e, "12000004")
    h.node_set_value(e1, {"key": "Element", "t": REG_SZ, "value": "Windows Boot Manager\0".encode(encoding="utf-16le")})
    e1 = h.node_add_child(e, "24000001")
    h.node_set_value(e1, {"key": "Element", "t": REG_MULTI_SZ,
                          "value": "{65c31250-afa2-11df-8045-000c29f37d88}\0\0".encode(encoding="utf-16le")})
    e1 = h.node_add_child(e, "16000048")
    h.node_set_value(e1, {"key": "Element", "t": REG_BINARY, "value": b"\x01"})

    b = h.node_add_child(objs, "{65c31250-afa2-11df-8045-000c29f37d88}")
    d = h.node_add_child(b, "Description")
    h.node_set_value(d, {"key": "Type", "t": REG_DWORD, "value": b"\x03\x00\x20\x13"})
    e = h.node_add_child(b, "Elements")
    e1 = h.node_add_child(e, "12000004")
    h.node_set_value(e1, {"key": "Element", "t": REG_SZ, "value": "Windows PE\0".encode(encoding="utf-16le")})
    e1 = h.node_add_child(e, "22000002")
    h.node_set_value(e1, {"key": "Element", "t": REG_SZ, "value": "\\Windows\0".encode(encoding="utf-16le")})
    e1 = h.node_add_child(e, "26000010")
    h.node_set_value(e1, {"key": "Element", "t": REG_BINARY, "value": b"\x01"})
    e1 = h.node_add_child(e, "26000022")
    h.node_set_value(e1, {"key": "Element", "t": REG_BINARY, "value": b"\x01"})
    e1 = h.node_add_child(e, "11000001")
    guid = guid2binary("{ae5534e0-a924-466c-b836-758539a3ee3a}")
    wimval = {"key": "Element",
              "t": REG_BINARY,
              "value": guid + b"\x00\x00\x00\x00\x01\x00\x00\x00" + winpath_length(wim, 126)
                            + b"\x00\x00\x00\x00\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                              b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00"
                            + winpath_length(wim, 86)
                            + b"\x00\x00\x00\x05\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x48\x00\x00"
                              b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                              b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                              b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                              b"\x00\x00\x00\x00\x00\x00\x00" + wim.encode(encoding="utf_16_le")
                            + b"\x00\x00"}
    h.node_set_value(e1, wimval)
    e1 = h.node_add_child(e, "21000001")
    h.node_set_value(e1, wimval)

    if startoptions:
        e1 = h.node_add_child(e, "12000030")
        h.node_set_value(e1,
                         {"key": "Element", "t": REG_SZ, "value": startoptions.join("\0").encode(encoding="utf-16le")})

    b = h.node_add_child(objs, "{ae5534e0-a924-466c-b836-758539a3ee3a}")
    d = h.node_add_child(b, "Description")
    h.node_set_value(d, {"key": "Type", "t": REG_DWORD, "value": b"\x00\x00\x00\x30"})
    e = h.node_add_child(b, "Elements")
    e1 = h.node_add_child(e, "12000004")
    h.node_set_value(e1, {"key": "Element", "t": REG_SZ, "value": "Ramdisk Options\0".encode(encoding="utf-16le")})
    e1 = h.node_add_child(e, "32000004")
    h.node_set_value(e1, {"key": "Element", "t": REG_SZ, "value": sdi.encode(encoding="utf-16le") + b"\x00\x00"})
    e1 = h.node_add_child(e, "31000003")
    h.node_set_value(e1, {"key": "Element",
                          "t": REG_BINARY,
                          "value": b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x05\x00\x00\x00"
                                   b"\x00\x00\x00\x00\x48\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                                   b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                                   b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                                   b"\x00\x00\x00\x00\x00\x00\x00\x00"})
    h.commit(new_bcd)


def run(api, args):
    settings = api.settings()
    if not settings.windows_enabled:
        return 0
    if not HAS_HIVEX:
        logger.info(
            "python3-hivex or python3-pefile not found. If you need Automatic Windows Installation support, "
            "please install."
        )
        return 0

    profiles = api.profiles()
    systems = api.systems()
    templ = templar.Templar(api)
    tgen = tftpgen.TFTPGen(api)

    with open(os.path.join(settings.windows_template_dir, post_inst_cmd_template_name)) as template_win:
        post_tmpl_data = template_win.read()

    with open(os.path.join(settings.windows_template_dir, answerfile_template_name)) as template_win:
        tmpl_data = template_win.read()

    with open(os.path.join(settings.windows_template_dir, startnet_template_name)) as template_start:
        tmplstart_data = template_start.read()

    def gen_win_files(distro, meta):
        (kernel_path, kernel_name) = os.path.split(distro.kernel)
        distro_path = utils.find_distro_path(settings, distro)
        distro_dir = wim_file_name = os.path.join(settings.tftpboot_location, "images", distro.name)
        web_dir = os.path.join(settings.webdir, "images", distro.name)
        is_winpe = "winpe" in meta and meta['winpe'] != ""
        is_bcd = "bcd" in meta and meta['bcd'] != ""

        if "kernel" in meta:
            kernel_name = meta["kernel"]

        kernel_name = os.path.basename(kernel_name)
        is_wimboot = "wimboot" in kernel_name

        if is_wimboot:
            distro_path = os.path.join(settings.webdir, "distro_mirror", distro.name)
            kernel_path = os.path.join(distro_path, "boot")

            if "kernel" in meta and "wimboot" not in distro.kernel:
                tgen.copy_single_distro_file(os.path.join(settings.tftpboot_location, kernel_name), distro_dir, False)
                tgen.copy_single_distro_file(os.path.join(distro_dir, kernel_name), web_dir, True)

        if "post_install_script" in meta:
            post_install_dir = distro_path

            if distro.os_version not in ("XP", "2003"):
                post_install_dir = os.path.join(post_install_dir, "sources")

            post_install_dir = os.path.join(post_install_dir, "$OEM$", "$1")

            if not os.path.exists(post_install_dir):
                utils.mkdir(post_install_dir)

            data = templ.render(post_tmpl_data, meta, None)
            post_install_script = os.path.join(post_install_dir, meta["post_install_script"])
            logger.info("Build post install script: %s", post_install_script)
            with open(post_install_script, "w+") as pi_file:
                pi_file.write(data)

        if "answerfile" in meta:
            data = templ.render(tmpl_data, meta, None)
            answerfile_name = os.path.join(distro_dir, meta["answerfile"])
            logger.info("Build answer file: %s", answerfile_name)
            with open(answerfile_name, "w+") as answerfile:
                answerfile.write(data)
            tgen.copy_single_distro_file(answerfile_name, distro_path, False)
            tgen.copy_single_distro_file(answerfile_name, web_dir, True)

        if "kernel" in meta and "bootmgr" in meta:
            wk_file_name = os.path.join(distro_dir, kernel_name)
            wl_file_name = os.path.join(distro_dir, meta["bootmgr"])
            tl_file_name = os.path.join(kernel_path, "bootmgr.exe")

            if distro.os_version in ("XP", "2003") and not is_winpe:
                tl_file_name = os.path.join(kernel_path, "setupldr.exe")

                if len(meta["bootmgr"]) != 5:
                    logger.error("The loader name should be EXACTLY 5 character")
                    return 1

                pat1 = re.compile(br'NTLDR', re.IGNORECASE)
                pat2 = re.compile(br'winnt\.sif', re.IGNORECASE)
                with open(tl_file_name, 'rb') as file:
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
                    logger.error("File not found: %s", tl_file_name)
                    return 1

                pat1 = re.compile(br'bootmgr\.exe', re.IGNORECASE)
                pat2 = re.compile(br'(\\.B.o.o.t.\\.)(B)(.)(C)(.)(D)', re.IGNORECASE)

                bcd_name = bytes("\\g<1>" + bcd_name[0] + "\\g<3>" + bcd_name[1] + "\\g<5>" + bcd_name[2], 'utf-8')
                with open(tl_file_name, 'rb') as file:
                    out = file.read()

                if not is_wimboot:
                    logger.info("Patching build Loader: %s", wl_file_name)
                    out = pat2.sub(bcd_name, out)

            if tl_file_name != wl_file_name:
                logger.info("Build Loader: %s from %s", wl_file_name, tl_file_name)
                with open(wl_file_name, 'wb+') as file:
                    file.write(out)
                tgen.copy_single_distro_file(wl_file_name, web_dir, True)

            if not is_wimboot:
                if distro.os_version not in ("XP", "2003") or is_winpe:
                    pe = pefile.PE(wl_file_name, fast_load=True)
                    pe.OPTIONAL_HEADER.CheckSum = pe.generate_checksum()
                    pe.write(filename=wl_file_name)

                with open(distro.kernel, 'rb') as file:
                    data = file.read()
                out = pat1.sub(bytes(meta["bootmgr"], 'utf-8'), data)

                if wk_file_name != distro.kernel:
                    logger.info(
                        "Build PXEBoot: %s from %s", wk_file_name, distro.kernel
                    )
                    with open(wk_file_name, 'wb+') as file:
                        file.write(out)
                    tgen.copy_single_distro_file(wk_file_name, web_dir, True)

        if is_bcd:
            obcd_file_name = os.path.join(kernel_path, "bcd")
            bcd_file_name = os.path.join(distro_dir, meta["bcd"])
            wim_file_name = 'winpe.wim'

            if not os.path.isfile(obcd_file_name):
                logger.error("File not found: %s", obcd_file_name)
                return 1

            if is_winpe:
                wim_file_name = meta["winpe"]

            if is_wimboot:
                wim_file_name = '\\Boot\\' + wim_file_name
                sdi_file_name = '\\Boot\\' + 'boot.sdi'
            else:
                wim_file_name = os.path.join("/images", distro.name, wim_file_name)
                sdi_file_name = os.path.join("/images", distro.name, os.path.basename(distro.initrd))

            logger.info(
                "Build BCD: %s from %s for %s",
                bcd_file_name,
                obcd_file_name,
                wim_file_name,
            )
            bcdedit(obcd_file_name, bcd_file_name, wim_file_name, sdi_file_name)
            tgen.copy_single_distro_file(bcd_file_name, web_dir, True)

        if is_winpe:
            ps_file_name = os.path.join(distro_dir, meta["winpe"])
            wim_pl_name = os.path.join(kernel_path, "winpe.wim")

            cmd = ["/usr/bin/cp", "--reflink=auto", wim_pl_name, ps_file_name]
            utils.subprocess_call(cmd, shell=False)
            tgen.copy_single_distro_file(ps_file_name, web_dir, True)

            if os.path.exists(wimupdate):
                data = templ.render(tmplstart_data, meta, None)
                pi_file = tempfile.NamedTemporaryFile()
                pi_file.write(bytes(data, 'utf-8'))
                pi_file.flush()
                cmd = ["/usr/bin/wimdir %s 1 | /usr/bin/grep -i '^/Windows/System32/startnet.cmd$'" % ps_file_name]
                startnet_path = utils.subprocess_get(cmd, shell=True)[0:-1]
                cmd = [wimupdate, ps_file_name, "--command=add %s %s" % (pi_file.name, startnet_path)]
                utils.subprocess_call(cmd, shell=False)
                pi_file.close()

    for profile in profiles:
        distro = profile.get_conceptual_parent()

        if distro and distro.breed == "windows":
            logger.info("Profile: %s", profile.name)
            meta = utils.blender(api, False, profile)
            autoinstall_meta = meta.get("autoinstall_meta", {})
            meta.update(autoinstall_meta)
            gen_win_files(distro, meta)

    for system in systems:
        profile = system.get_conceptual_parent()
        autoinstall_meta = system.autoinstall_meta

        if not profile or not autoinstall_meta or autoinstall_meta == {}:
            continue

        distro = profile.get_conceptual_parent()

        if distro and distro.breed == "windows":
            logger.info("System: %s", system.name)
            meta = utils.blender(api, False, system)
            gen_win_files(distro, autoinstall_meta)
    return 0
