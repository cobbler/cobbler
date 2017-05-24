#!/usr/bin/env python
"""
Create a KVM guest and install a Linux operating system in it.
Linux installation may be manual or automated.
It must be run on a KVM host.

@IMPROVEMENT: support automated installation of Debian and SUSE based
distributions
"""

import argparse
import os
import platform
import re
import shlex
import shutil
import socket
import subprocess
import urllib2

DEBUG = True
# default number of CPUs
DEFAULT_NUM_CPUS = 1
# default RAM amount in GB
DEFAULT_RAM = 2
# guest's disk default size in GB
DISK_DEFAULT_SIZE = 5
# enable SSH daemon during Linux installation for debugging purposes
ENABLE_SSH_DURING_INSTALLATION = True
# web server root directory
WEB_SERVER_ROOT = "/var/www/html"


def run_cmd(cmd, shell=False):
    '''
    Run a command

    @param str cmd command
    @param bool shell use a Linux shell
    @return str output
    @raise Exception if return code is not 0
    '''

    args = shlex.split(cmd)

    try:
        sp = subprocess.Popen(args, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
    except OSError:
        raise Exception("OS error running command %s" % cmd)

    (output, err) = sp.communicate()
    rc = sp.returncode
    if rc != 0:
        raise Exception("Command return return code %s, error: %s" % (rc, err))

    return output

def is_local_file(file_location):
    """
    Check if file is in the local file system

    @param str file_location file URL/path
    @return bool if file is local
    """

    return not re.match("[a-z]+://", file_location)

def download_file(file_url):
    """
    Download a file

    @param str file_url file URL
    @return str file content
    @raise Exception if unable to download the file
    """

    if not file_url.startswith("http") and not file_url.startswith("ftp"):
        raise Exception("only HTTP and FTP are supported in file URL")

    req = urllib2.urlopen(file_url)
    return req.read()

def create_kvm_guest(guest_name, num_virtual_cpus, virtual_ram, virtual_disk_size,
             os, os_iso_path=None, os_tree_location=None,
             autoinstall_file_location=None, kernel_args=None):
    """
    Create a KVM guest

    @param str guest_name guest name
    @param int num_virtual_cpus number of virtual CPUs in guest
    @param int virtual_ram amount of virtual RAM in MB in guest
    @param int virtual_disk_size virtual disk size in GB in guest
    @param str os name and version of Linux OS to be installed in guest
    @param str os_iso_path ISO path of Linux OS to be installed in guest.
            This parameter and os_tree_location are mutually exclusive.
    @param str os_tree_location path/URL of Linux OS tree
            This parameter and os_iso_path are mutually exclusive.
    @param str autoinstall_file_location path/URL of automatic installation file
            (autoyast / kickstart / preseed). This parameter and os_tree_location
             must be used together
    @param str kernel_args extra kernel command line arguments
    @raise Exception if unable to create the KVM guest
    """

    arch = platform.uname()[4]
    cmd = "virt-install --name=%s --arch=%s --vcpus=%d --ram=%d --os-type=linux --os-variant=%s --hvm --autostart --connect=qemu:///system --disk path=/var/lib/libvirt/images/%s.img,size=%d --network bridge:br0 --graphics vnc --noautoconsole --virt-type=kvm" % (guest_name, arch, num_virtual_cpus, virtual_ram, os, guest_name, virtual_disk_size)
    if os_iso_path and os_tree_location:
        raise Exception("Linux OS' ISO path and tree location are mutually exclusive")
    if os_iso_path:
        cmd += " --cdrom=%s" % os_iso_path
    elif os_tree_location:
        cmd += " --location=%s" % os_tree_location
    else:
        raise Exception("Linux OS' ISO path or tree location must be provided")
    if autoinstall_file_location:
        if not os_tree_location:
            raise Exception("Custom autoinstall may only be provided if a Linux OS tree location is provided")
        ks_kernel_arg = "ks=%s" % autoinstall_file_location
        if kernel_args:
            kernel_args += " %s" % ks_kernel_arg
        else:
            kernel_args = ks_kernel_arg
        if ENABLE_SSH_DURING_INSTALLATION:
            kernel_args += " sshd"
        cmd += " --extra-args=\"%s\"" % kernel_args

    if DEBUG:
        print("virt-install command: %s" % cmd)
    print("creating KVM guest")
    run_cmd(cmd)


def parse_input():
    """
    Parse and validate command line input

    @return dict validated input. Keys are input parameters for KVM guest creation,
            not necessarily equal to command line parameters
    @raise Exception if input validation fails
    """

    # create command line argument parser
    parser = argparse.ArgumentParser(description='Create a KVM guest and install a Linux distribution in it. Installation may be manual or automated')
    parser.add_argument('-n', '--name', metavar='name', nargs=1, action="store", help='Guest name')
    parser.add_argument('-c', '--cpus', metavar='num_cpus', nargs='?', action="store", help='Number of virtual CPUs in guest')
    parser.add_argument('-m', '--ram', metavar='amount_ram', nargs='?', action="store", help='Amount of virtual RAM in guest')
    parser.add_argument('-d', '--disk', metavar='disk_size', nargs='?', action="store", help='Disk size')
    parser.add_argument('-o', '--distro', metavar='distro', nargs='?', action="store", help='Linux distribution name and version. Use virt-install --os-variant list to list possible options')
    parser.add_argument('-i', '--distro-iso-path', metavar='distro_iso_path', nargs='?', action="store", help='Linux distribution ISO path. Provide this parameter if manual installation is desired. --distro-iso-path and --distro-tree are mutually exclusive.')
    parser.add_argument('-t', '--distro-tree', metavar='distro_tree', nargs='?', action="store", help='Linux distribution tree root directory URL. This parameter may be used in manual or automated installation. --distro-iso-path and --distro-tree are mutually exclusive. A distro tree URL with embedded credentials (and therefore a server which requires authentication) is not supported.')
    parser.add_argument('-a', '--autoinstall', metavar='autoinstall', nargs='?', action="store", help="location of autoinstall file which will be used to automate Linux installation. Location may be a local file path (requires a web server enabled in KVM host) or a remote HTTP/FTP URL. Only supports Red Hat based distributions. Must be used together with --distro-tree")
    parser.add_argument('-e', '--network', metavar='network', nargs='?', action="store", help="guest's static network setup to be done in an automated installation. Only supports Red Hat based distributions. Must be used together with --distro-tree and --autoinstall parameters. As original autoinstall file is downloaded and network setup is added/replaced in it, KVM host must have a web server enabled to host the new autoinstall file. Format: <ip>|<netmask>|<gateway>|<dns_server> .")

    # parse input
    args = parser.parse_args()
    if not args.name:
        raise Exception("Provide a guest name")
    name = args.name[0]
    if not args.cpus:
        num_cpus = DEFAULT_NUM_CPUS
    else:
        num_cpus = int(args.cpus)
    if not args.ram:
        amount_ram = DEFAULT_RAM*1024
    else:
        amount_ram = int(args.ram)
    if not args.disk:
        disk_size = DISK_DEFAULT_SIZE
    else:
        disk_size = int(args.disk)
    if not args.distro:
        distro = "virtio26"
    else:
        distro = args.distro

    if not args.distro_iso_path and not args.distro_tree:
        raise Exception("Provide ISO path or tree location of a Linux distribution to be installed")
    if not args.distro_iso_path:
        distro_iso_path = None
    else:
        distro_iso_path = args.distro_iso_path
    if not args.distro_tree:
        distro_tree = None
    else:
        distro_tree = args.distro_tree

    if not args.autoinstall:
        autoinstall_file_location = None
        if args.network:
            raise Exception("Invalid parameters, autoinstall parameter must be provided when network parameters are provided")
    else:
        autoinstall_file_location = args.autoinstall
        if is_local_file(autoinstall_file_location):
            autoinstall_file = open(autoinstall_file_location).read()
        elif args.network:
            autoinstall_file = download_file(autoinstall_file_location)

        # add url autoinstall directive to file
        url_ks = "url --url=%s" % distro_tree
        url_ks = "\n%s" % url_ks
        if re.search("\nurl .*\n", autoinstall_file):
            autoinstall_file = re.sub("\nurl .*\n", url_ks + "\n", autoinstall_file)
        else:
            autoinstall_file += "\n%s" % url_ks

        # if network parameters were defined
        kernel_args = None
        if args.network:
            # create network autoinstall directive
            network_input = args.network.split("|")
            if len(network_input) != 4:
                raise Exception("Invalid format of network parameter")
            network_ks = "network --bootproto=static --ip=%s --netmask=%s --gateway=%s" % (network_input[0], network_input[1], network_input[2])
            if network_input[3] != "":
                network_ks += " --nameserver=%s" % network_input[3]
            network_ks += " --hostname=%s" % name
            network_ks = "\n%s" % network_ks

            # add network autoinstall directive to file
            if re.search("\nnetwork .*\n", autoinstall_file):
                autoinstall_file = re.sub("\nnetwork .*\n", network_ks + "\n", autoinstall_file)
            else:
                autoinstall_file += "\n%s" % network_ks

            # @TODO Fedora 17+ uses different syntax for passing network parameters
            # in kernel command line, fix this
            kernel_args = "ip=%s netmask=%s gateway=%s" % (network_input[0], network_input[1], network_input[2])
            if network_input[3] != "":
                kernel_args += " dns=%s" % network_input[3]

        if args.network or is_local_file(autoinstall_file_location):
            # save it in web server root directory
            base_ai_dir = "%s/autoinstall_files" % WEB_SERVER_ROOT
            if not os.path.exists(base_ai_dir):
                os.makedirs(base_ai_dir)
            autoinstall_file_name = os.path.basename(autoinstall_file_location)
            autoinstall_file_path = "%s/%s" % (base_ai_dir, autoinstall_file_name)
            autoinstall_fh = open(autoinstall_file_path, "w+")
            autoinstall_fh.write(autoinstall_file)
            autoinstall_fh.close()

            autoinstall_file_location = "http://%s/autoinstall_files/%s" % (socket.gethostbyname(socket.getfqdn()), autoinstall_file_name)

    return {"name": name,
            "num_cpus": num_cpus,
            "amount_ram": amount_ram,
            "disk_size": disk_size,
            "distro": distro,
            "distro_iso_path": distro_iso_path,
            "distro_tree_location": distro_tree,
            "autoinstall_file_location": autoinstall_file_location,
            "kernel_args": kernel_args
           }

def main():
    """
    Method called when script is run
    """

    input = parse_input()
    create_kvm_guest(input["name"],
            input["num_cpus"], input["amount_ram"], input["disk_size"],
            input["distro"], input["distro_iso_path"], input["distro_tree_location"],
            input["autoinstall_file_location"], input["kernel_args"])


if __name__ == "__main__":
    main()
