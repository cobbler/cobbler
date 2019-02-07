#!/bin/bash

# DISTRO directory overrides. Pass these vars in from outside:
# export SYSLINUX_DIR=/usr/share/...;./mkgrub.sh
[[ -z "$SYSLINUX_DIR" ]] && SYSLINUX_DIR="/usr/share/syslinux"
[[ -z "$GRUB2_MOD_DIR" ]] && GRUB2_MOD_DIR="/usr/share/grub2"

BOOTLOADERS_DIR="/var/lib/cobbler/loaders"
TARGETS="arm64-efi i386-pc-pxe powerpc-ieee1275 x86_64-efi"

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
		search_fs_file search_label sleep test video fat loadenv linux"
PXE_MODULES="tftp http"
CRYPTO_MODULES="luks gcry_rijndael gcry_sha1 gcry_sha256"
MISC_MODULES="mdraid09 mdraid1x lvm serial regexp tr"

TARGET_EXTRA_MODULES=""

function link_loader
{
    local T="$1"
    local L="$2"

    if [[ -e "$T" ]] && [[ ! -e "${BOOTLOADERS_DIR}/$L" ]];then
	set -x
        ln -s "$T" "${BOOTLOADERS_DIR}/$L"
	set +x
	# Remember links for later deletion/cleanups
        echo "$L" >> "${BOOTLOADERS_DIR}/.cobbler_postun_cleanup"
    fi
}


mkdir -p "${BOOTLOADERS_DIR}/grub"
for TARGET in $TARGETS;do
    TARGET_MOD_DIR="$TARGET"
    case $TARGET in
	i386-pc-pxe)
	    # Name the x86 PXE executble with .0 in the end
	    # pxelinux.0 only wants to chainload bootloaders ending with .0
	    BINARY="grub.0"
	    TARGET_EXTRA_MODULES="chain pxe biosdisk"
	    # For i386-pc-pxe target the modules dir still is i386-pc
	    TARGET_MOD_DIR="i386-pc"
	    ;;
	x86_64-efi)
	    TARGET_EXTRA_MODULES="chain efinet"
	    BINARY="grubx64.efi"
	    ;;
	arm64-efi)
	    TARGET_EXTRA_MODULES="efinet"
	    BINARY="grubaa64.efi"
	    ;;
	powerpc-ieee1275)
	    TARGET_EXTRA_MODULES="net ofnet"
	    BINARY="grub.ppc64le"
	    ;;
    esac
    GRUB_MODULES="${CD_MODULES} ${FS_MODULES} ${PXE_MODULES} ${CRYPTO_MODULES} ${MISC_MODULES} ${TARGET_EXTRA_MODULES}"
    MODULE_DIR="${GRUB2_MOD_DIR}/${TARGET_MOD_DIR}"
    set -x
    grub2-mkimage -O ${TARGET} -o "${BOOTLOADERS_DIR}/grub/${BINARY}" --prefix= ${GRUB_MODULES}
    set +x
    echo "grub2/${BINARY}" >> "${BOOTLOADERS_DIR}/.cobbler_postun_cleanup"
    if [[ -e "$MODULE_DIR" ]] && [[ ! -e "${BOOTLOADERS_DIR}/grub/$TARGET_MOD_DIR" ]];then
	set -x
        ln -s "$MODULE_DIR" "${BOOTLOADERS_DIR}/grub/$TARGET_MOD_DIR"
	set +x
        echo "$TARGET_MOD_DIR" >> "${BOOTLOADERS_DIR}/.cobbler_postun_cleanup"
    fi

done

link_loader "/usr/share/efi/x86_64/shim.efi" "grub/shim.efi"
link_loader "/usr/share/efi/x86_64/grub.efi" "grub/grub.efi"
link_loader "${SYSLINUX_DIR}/pxelinux.0" "pxelinux.0"
link_loader "${SYSLINUX_DIR}/menu.c32" "menu.c32"
link_loader "${SYSLINUX_DIR}/ldlinux.c32" "ldlinux.c32"
link_loader "$SYSLINUX_DIR}/memdisk" "memdisk"
# ToDo: Do this properly if still used
link_loader "/usr/share/*pxe/undionly.kpxe" "undionly.pxe"
