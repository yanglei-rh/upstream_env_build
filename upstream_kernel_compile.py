"setup kernel upstream test env by this script"""

import os
import re
import json
import subprocess
import argparse
import time

QUIET = False
LOG_LVL = 4
##Replace JIRA_ACCESS_TOKEN with your own jira token before the tests. ####
#for gmail

def _log(lvl, msg):
    """Print a message with level 'lvl' to Console"""
    if not QUIET and lvl <= LOG_LVL:
        print(msg)


def _log_debug(msg):
    """Print a message with level DEBUG to Console"""
    msg = "\033[96mDEBUG: " + msg + "\033[00m"
    _log(4, msg)


def _log_info(msg):
    """Print a message with level INFO to Console"""
    msg = "\033[92mINFO: " + msg + "\033[00m"
    _log(3, msg)


def _log_warn(msg):
    """Print a message with level WARN to Console"""
    msg = "\033[93mWARN: " + msg + "\033[00m"
    _log(2, msg)


def _log_error(msg):
    """Print a message with level ERROR to Console"""
    msg = "\033[91mERROR: " + msg + "\033[00m"
    _log(1, msg)

def linux_next_value(patch_title):
    if "next" in patch_title.lower():
        linux_next = True
    else:
        linux_next = False
    return linux_next

def add_ca_certificates():
    _log_info("Install Red Hat CA certificates:")
    install_ca = "curl -L -k 'https://certs.corp.redhat.com/certs/Current-IT-Root-CAs.pem' -o /etc/pki/ca-trust/source/anchors/Current-IT-Root-CAs.pem && "
    install_ca += "update-ca-trust"
    if os.system(install_ca) != 0:
        _log_error("Failed to install Red Hat CA certificates.")


def apply_patch(label=None, tag=None, msg_id=None, patch_title=None):
    if linux_next_value(patch_title):
        os.chdir(os.getcwd() + "/linux-next")
    else:
        os.chdir(os.getcwd() + "/linux")
    cmd = "b4 am %s" % msg_id
    result = subprocess.getoutput(cmd)
    mbox = result.split("\n")[-1].strip()
    os.system(mbox)

def build_kernel_pkg(patch_title=None):
    if linux_next_value(patch_title):
        if "/linux-next" not in os.getcwd():
            os.chdir(os.getcwd() + "/linux-next")
    else:
        if "/linux" not in os.getcwd():
            os.chdir(os.getcwd() + "/linux")
    _log_info("Build upstream kernel package...")
    _log_info("copy host config file")
    build_cmd = "cp /boot/config-* .config"
    download_pkg = ""
    if download_pkg:
        os.system("yum install -y %s" % download_pkg)
    os.system(build_cmd)
    _log_info("Make and install kernel package...")
    os.system("make olddefconfig")
    os.system("make -j8 binrpm-pkg")

def get_os_release():
    res = subprocess.getoutput("cat /etc/os-release")
    match = re.search(r'\d+', res).group()
    if match:
        return match

def pkg_in_pip_lists(pkg):
    output = subprocess.getoutput("pip list")
    if pkg in output:
        return True

def install_deps():
    if os.system("rpm -q epel-release") != 0:
        _log_info("Installing epel-release")
        os_release = get_os_release()
        epel_pkg = "https://dl.fedoraproject.org/pub/epel/epel-release-latest-%s.noarch.rpm" % os_release
        os.system("dnf install -y %s" % epel_pkg)
    RPM_REQS=(
    "gcc",
    "gcc-c++",
    "glibc-headers",
    "python3-devel",
    "net-tools",
    "openssl",
    "openssl-devel",
    "make",
    "b4",
    "bc",
    "bison",
    "git",
    "python3",
    "rpm-build",
    "flex",
    "ncurses-devel",
    "elfutils-libelf-devel",
    "perl",
    "dwarves",
    "rsync"
    )
    for rpm in RPM_REQS:
        if os.system("rpm -q %s" % rpm)!= 0:
            os.system("dnf install -y %s" % rpm)

def clone_upstream_kernel(label=None, tag=None, patch_id=None, patch_title=None):
    if os.system("rpm -q git") !=0:
        if os.system("yum install -y git") != 0:
            _log_error("Failed to install git related packages.")
    _log_info("Clone upstream kernel repo.")
    if linux_next_value(patch_title):
        download_kernel = "git clone https://git.kernel.org/pub/scm/linux/kernel/git/next/linux-next.git"
    else:
        download_kernel = "git clone https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git"
    if os.system(download_kernel) != 0:
        _log_error("Failed to clone kernel repo.")
    if patch_id:
        apply_patch(label, tag, patch_id, patch_title)
    build_kernel_pkg(patch_title)

def install_kernel():
    cmd = "uname -m"
    result = subprocess.getoutput(cmd)
    os.chdir(os.getcwd() + "/rpmbuild/RPMS/%s" % result)
    os.system("dnf install -y *.rpm")

def main(argv):
    try:
        label = argv.get("label", None)
        tag = argv.get("tag", "linux-kernel@vger.kernel.org")
        patch_id = argv.get("patch_id", None)
        patch_title = argv.get("patch_title", None)
        add_ca_certificates()
        install_deps()
        clone_upstream_kernel(label, tag, patch_id, patch_title)
        install_kernel()
    except Exception as e:
        _log_error(str(e))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default=None, help="gmail label where you want to get the patch")
    parser.add_argument("--tag", default="linux-kernel@vger.kernel.org", help="gmail tag where you want to get the patch")
    parser.add_argument("--patch_id", default=None, help="patch messages id that needed to apply")
    parser.add_argument("--patch_title", default=None, help="to help confirm which repo need to be clone")
    config_args = vars(parser.parse_args())
    main(config_args)
