#!/bin/bash

# DISTRO directory overrides. Pass these vars in from outside:
# export SYSLINUX_DIR=/usr/share/...;./mkgrub.sh
[[ -z "$SYSLINUX_DIR" ]] && SYSLINUX_DIR="/usr/share/syslinux"

BOOTLOADERS_DIR="/var/lib/cobbler/loaders"
TARGETS="arm64-efi i386-pc powerpc-ieee1275 x86_64-efi"

rm -rf "${BOOTLOADERS_DIR}/.cobbler_postun_cleanup"

# grub2 internal executable naming
# aarch64 => grubaa64.efi
# x86_64 => grubx64.efi
# i386/i686 => bootia32.efi
# IA64 => bootia64.efi
# arm => bootarm.efi

FS_MODULES="btrfs ext2 xfs jfs reiserfs"
CD_MODULES=" all_video boot cat configfile echo true \
		font gfxmenu gfxterm gzio halt iso9660 \
		jpeg minicmd normal part_apple part_msdos part_gpt \
		password_pbkdf2 png reboot search search_fs_uuid \
		search_fs_file search_label sleep test video fat loadenv"
PXE_MODULES="tftp http"
CRYPTO_MODULES="luks gcry_rijndael gcry_sha1 gcry_sha256"

CD_MODULES="${CD_MODULES} linux"

GRUB_MODULES="${CD_MODULES} ${FS_MODULES} ${PXE_MODULES} ${CRYPTO_MODULES} mdraid09 mdraid1x lvm serial regexp tr"

mkdir -p "${BOOTLOADERS_DIR}/grub/"
for TARGET in $TARGETS;do
    case $TARGET in
	i386-pc)
	    PXE_MODULES="${PXE_MODULES} pxe biosdisk"
	    BINARY="grub.0"
	    CD_MODULES="${CD_MODULES} chain"
	    ;;
	x86_64-efi)
	    PXE_MODULES="${PXE_MODULES} efinet"
	    BINARY="grub2-x86_64.efi"
	    CD_MODULES="${CD_MODULES} chain"
	    ;;
	arm64-efi)
	    PXE_MODULES="${PXE_MODULES} efinet"
	    BINARY="grubaa64.efi"
	    ;;
	powerpc-ieee1275)
	    PXE_MODULES="${PXE_MODULES} net ofnet"
	    BINARY="grub.ppc64le"
	    ;;
    esac
    set -x
    grub2-mkimage -O ${TARGET} -o "${BOOTLOADERS_DIR}/grub/${BINARY}" --prefix= ${GRUB_MODULES}
    set +x
    echo "grub2/${BINARY}" >> "${BOOTLOADERS_DIR}/.cobbler_postun_cleanup"
done

    # ToDo: Use shim_dir and grub_dir variables for other distros to pass them in
    if [[ -e /usr/share/efi/x86_64/shim.efi ]] && [[ ! -e "${BOOTLOADERS_DIR}/grub2/shim.efi" ]];then
        ln -s /usr/share/efi/x86_64/shim.efi "${BOOTLOADERS_DIR}/grub2/shim.efi"
        echo "grub2/shim.efi" >> "${BOOTLOADERS_DIR}/.cobbler_postun_cleanup"
    fi
    if [[ -e /usr/share/efi/grub.efi ]] && [[ ! -e "${BOOTLOADERS_DIR}/grub2/grub.efi" ]];then
	    ln -s /usr/share/efi/grub.efi "${BOOTLOADERS_DIR}/grub2/grub.efi"
	    echo "grub2/grub.efi" >> "${BOOTLOADERS_DIR}/.cobbler_postun_cleanup"
    fi
    if [[ -e "$SYSLINUX_DIR"/pxelinux.0 ]] && [[ ! -e "${BOOTLOADERS_DIR}/pxelinux.0" ]];then
        ln -s "$SYSLINUX_DIR"/pxelinux.0 "${BOOTLOADERS_DIR}/pxelinux.0"
        echo "grub2/${BINARY}" >> "${BOOTLOADERS_DIR}/.cobbler_postun_cleanup"
    fi
    if [[ -e "$SYSLINUX_DIR"/pxelinux.0 ]] && [[ ! -e "${BOOTLOADERS_DIR}/pxelinux.0" ]];then
        ln -s "$SYSLINUX_DIR"/pxelinux.0 "${BOOTLOADERS_DIR}/pxelinux.0"
        echo "pxelinux.0" >> "${BOOTLOADERS_DIR}/.cobbler_postun_cleanup"
    fi
    if [[ -e "$SYSLINUX_DIR"/menu.c32 ]] && [[ ! -e "${BOOTLOADERS_DIR}/menu.c32" ]];then
        ln -s "$SYSLINUX_DIR"/menu.c32 "${BOOTLOADERS_DIR}/menu.c32"
        echo "menu.c32" >> "${BOOTLOADERS_DIR}/.cobbler_postun_cleanup"
    fi
    if [[ -e "$SYSLINUX_DIR"/ldlinux.c32 ]] && [[ ! -e "${BOOTLOADERS_DIR}/ldlinux.c32" ]];then
        ln -s "$SYSLINUX_DIR"/ldlinux.c32 "${BOOTLOADERS_DIR}/ldlinux.c32"
        echo "ldlinux.c32" >> "${BOOTLOADERS_DIR}/.cobbler_postun_cleanup"
    fi
    if [[ -e "$SYSLINUX_DIR"/memdisk ]] && [[ ! -e "${BOOTLOADERS_DIR}/memdisk" ]];then
        ln -s "$SYSLINUX_DIR"/memdisk "${BOOTLOADERS_DIR}/memdisk"
        echo "memdisk" >> "${BOOTLOADERS_DIR}/.cobbler_postun_cleanup"
    fi
    if [[ -e "/usr/share/*pxe/undionly.kpxe" ]] && [[ ! -e "${BOOTLOADERS_DIR}/undionly.kpxe" ]];then
        ln -s "/usr/share/*pxe/undionly.kpxe" "${BOOTLOADERS_DIR}/undionly.kpxe"
        echo "undionly.kpxe" >> "${BOOTLOADERS_DIR}/.cobbler_postun_cleanup"
    fi
