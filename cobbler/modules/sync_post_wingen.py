import os
import re
import binascii
import tempfile
from typing import Optional

import cobbler.utils as utils
import cobbler.templar as templar
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

template_dir = "/var/lib/tftpboot/winos/"
sif_template_name = template_dir + "win_sif.template"
post_inst_cmd_template_name = template_dir + "post_inst_cmd.template"
startnet_template_name = template_dir + "startnet.template"
wim7_template_name = template_dir + "winpe7.template"
wim8_template_name = template_dir + "winpe8.template"
wimupdate = "/usr/bin/wimupdate"


def register() -> Optional[str]:
    """
    This pure python trigger acts as if it were a legacy shell-trigger, but is much faster. The return of this method
    indicates the trigger type

    :return: Always ``/var/lib/cobbler/triggers/sync/post/*``
    :rtype: str
    """
    if not HAS_HIVEX:
        logging.info("python3-hivex not found. If you need Automatic Windows Installation support, please install.")
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
    h.node_set_value(e1, {"key": "Element",
                          "t": REG_BINARY,
                          "value": guid + b"\x00\x00\x00\x00\x01\x00\x00\x00"
                                        + winpath_length(wim, 126)
                                        + b"\x00\x00\x00\x00\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                                          b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00 "
                                        + winpath_length(wim, 86)
                                        + b"\x00\x00\x00\x05\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x48\x00\x00"
                                          b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                                          b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                                          b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                                          b"\x00\x00\x00\x00\x00\x00\x00" + wim.encode(encoding="utf_16_le")
                                        + b"\x00\x00"})
    e1 = h.node_add_child(e, "21000001")
    h.node_set_value(e1, {"key": "Element",
                          "t": REG_BINARY,
                          "value": guid + b"\x00\x00\x00\x00\x01\x00\x00\x00" + winpath_length(wim, 126)
                                        + b"\x00\x00\x00\x00\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                                          b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00 "
                                        + winpath_length(wim, 86)
                                        + b"\x00\x00\x00\x05\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x48\x00\x00"
                                          b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                                          b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                                          b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                                          b"\x00\x00\x00\x00\x00\x00\x00" + wim.encode(encoding="utf_16_le")
                                        + b"\x00\x00"})

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


def run(api, args, logger):
    if not HAS_HIVEX:
        logger.info("python3-hivex or python3-pefile not found. If you need Automatic Windows Installation support, "
                    "please install.")
        return 0

    distros = api.distros()
    profiles = api.profiles()
    templ = templar.Templar(api._collection_mgr)
    template_win = open(post_inst_cmd_template_name)
    tmpl_data = template_win.read()
    template_win.close()

    for distro in distros:
        if distro.breed == "windows":
            meta = utils.blender(api, False, distro)

            if "post_install" in distro.kernel_options:
                data = templ.render(tmpl_data, meta, None)
                pi_file = open(distro.kernel_options["post_install"], "w+")
                pi_file.write(data)
                pi_file.close()

    template_win = open(sif_template_name)
    tmpl_data = template_win.read()
    template_win.close()

    template_start = open(startnet_template_name)
    tmplstart_data = template_start.read()
    template_start.close()

    logger.info("\nWindows profiles:")

    for profile in profiles:
        distro = profile.get_conceptual_parent()

        if distro.breed == "windows":
            logger.info('Profile: ' + profile.name)
            meta = utils.blender(api, False, profile)
            (distro_path, pxeboot_name) = os.path.split(distro.kernel)

            if "sif" in profile.kernel_options:
                data = templ.render(tmpl_data, meta, None)

                if distro.os_version in ("7", "2008", "8", "2012", "2016", "2019", "10"):
                    sif_file_name = os.path.join(distro_path, 'sources', profile.kernel_options["sif"])
                else:
                    sif_file_name = os.path.join(distro_path, profile.kernel_options["sif"])

                sif_file = open(sif_file_name, "w+")
                sif_file.write(data)
                sif_file.close()
                logger.info('Build answer file: ' + sif_file_name)

            if "pxeboot" in profile.kernel_options and "bootmgr" in profile.kernel_options:
                wk_file_name = os.path.join(distro_path, profile.kernel_options["pxeboot"])
                wl_file_name = os.path.join(distro_path, profile.kernel_options["bootmgr"])
                logger.info("Build PXEBoot: " + wk_file_name)

                if distro.os_version in ("7", "2008", "8", "2012", "2016", "2019", "10"):
                    if len(profile.kernel_options["bootmgr"]) != 11:
                        logger.error("The loader  name should be EXACTLY 11 character")
                        return 1

                    if "bcd" in profile.kernel_options:
                        if len(profile.kernel_options["bcd"]) != 3:
                            logger.error("The BCD name should be EXACTLY 5 character")
                            return 1

                    tl_file_name = os.path.join(distro_path, 'bootmgr.exe')
                    pat1 = re.compile(br'bootmgr\.exe', re.IGNORECASE)
                    pat2 = re.compile(br'(\\.B.o.o.t.\\.)(B)(.)(C)(.)(D)', re.IGNORECASE)
                    bcd_name = 'BCD'

                    if "bcd" in profile.kernel_options:
                        bcd_name = profile.kernel_options["bcd"]

                    bcd_name = bytes("\\g<1>" + bcd_name[0] + "\\g<3>" + bcd_name[1] + "\\g<5>" + bcd_name[2], 'utf-8')
                    data = open(tl_file_name, 'rb').read()
                    out = pat2.sub(bcd_name, data)
                else:
                    if len(profile.kernel_options["bootmgr"]) != 5:
                        logger.error("The loader name should be EXACTLY 5 character")
                        return 1

                    if len(profile.kernel_options["sif"]) != 9:
                        logger.error("The response should be EXACTLY 9 character")
                        return 1

                    tl_file_name = os.path.join(distro_path, 'setupldr.exe')
                    pat1 = re.compile(br'NTLDR', re.IGNORECASE)
                    pat2 = re.compile(br'winnt\.sif', re.IGNORECASE)

                    data = open(tl_file_name, 'rb').read()
                    out = pat2.sub(bytes(profile.kernel_options["sif"], 'utf-8'), data)

                logger.info('Build Loader: ' + wl_file_name)

                if out != data:
                    open(wl_file_name, 'wb+').write(out)

                if distro.os_version in ("7", "2008", "8", "2012", "2016", "2019", "10"):
                    pe = pefile.PE(wl_file_name, fast_load=True)
                    pe.OPTIONAL_HEADER.CheckSum = pe.generate_checksum()
                    pe.write(filename=wl_file_name)

                data = open(distro.kernel, 'rb').read()
                out = pat1.sub(bytes(profile.kernel_options["bootmgr"], 'utf-8'), data)

                if out != data:
                    open(wk_file_name, 'wb+').write(out)

            if "bcd" in profile.kernel_options:
                obcd_file_name = os.path.join(distro_path, 'boot', 'BCD')
                bcd_file_name = os.path.join(distro_path, 'boot', profile.kernel_options["bcd"])
                wim_file_name = 'winpe.wim'

                if "winpe" in profile.kernel_options:
                    wim_file_name = profile.kernel_options["winpe"]

                if distro.boot_loader == "ipxe":
                    wim_file_name = '\\Boot\\' + wim_file_name
                    sdi_file_name = '\\Boot\\' + 'boot.sdi'
                else:
                    wim_file_name = os.path.join('/winos', distro.name, 'boot', wim_file_name)
                    sdi_file_name = os.path.join('/winos', distro.name, 'boot', 'boot.sdi')

                logger.info('Build BCD: ' + bcd_file_name + ' for ' + wim_file_name)
                bcdedit(obcd_file_name, bcd_file_name, wim_file_name, sdi_file_name)

            if "winpe" in profile.kernel_options:
                ps_file_name = os.path.join(distro_path, "boot", profile.kernel_options["winpe"])

                if distro.os_version in ("7", "2008"):
                    wim_pl_name = wim7_template_name
                elif distro.os_version in ("8", "2012", "2016", "2019", "10"):
                    wim_pl_name = wim8_template_name
                else:
                    raise ValueError("You are trying to use an unsupported distro!")

                cmd = "/usr/bin/cp --reflink=auto " + wim_pl_name + " " + ps_file_name
                utils.subprocess_call(logger, cmd, shell=True)

                if os.path.exists(wimupdate):
                    data = templ.render(tmplstart_data, meta, None)
                    pi_file = tempfile.NamedTemporaryFile()
                    pi_file.write(bytes(data, 'utf-8'))
                    pi_file.flush()
                    cmd = wimupdate + ' ' + ps_file_name + ' --command="add ' + pi_file.name
                    cmd += ' /Windows/System32/startnet.cmd"'
                    utils.subprocess_call(logger, cmd, shell=True)
                    pi_file.close()
    return 0
