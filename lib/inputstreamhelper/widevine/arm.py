# -*- coding: utf-8 -*-
# MIT License (see LICENSE.txt or https://opensource.org/licenses/MIT)
"""Implements ARM specific widevine functions"""

from __future__ import absolute_import, division, unicode_literals
import os
from contextlib import contextmanager

from .. import config
from ..kodiutils import browsesingle, copy, exists, localize, log, mkdir, ok_dialog, progress_dialog, yesno_dialog
from ..utils import cmd_exists, diskspace, http_download, http_get, p7unzip, run_cmd, sizeof_fmt, store, system_os, temp_path, unzip, update_temp_path


def mnt_path():
    """Return mount path, usually ~/.kodi/userdata/addon_data/script.module.inputstreamhelper/temp/mnt"""
    mount_path = os.path.join(temp_path(), 'mnt')
    if not exists(mount_path):
        mkdir(mount_path)

    return mount_path


def chromeos_offset(bin_path):
    """Calculate the Chrome OS losetup start offset using fdisk/parted."""
    if cmd_exists('fdisk'):
        cmd = ['fdisk', bin_path, '-l']
    else:  # parted
        cmd = ['parted', '-s', bin_path, 'unit s print']

    output = run_cmd(cmd, sudo=False)
    if output['success']:
        import re
        for line in output['output'].splitlines():
            partition_data = re.match(r'^\s?(3|.+bin3)\s+(\d+)s?\s+\d+', line)
            if partition_data:
                if partition_data.group(1) == '3' or partition_data.group(1).endswith('.bin3'):
                    offset = int(partition_data.group(2))
                    return str(offset * config.CHROMEOS_BLOCK_SIZE)

    log(4, 'Failed to calculate losetup offset.')
    return '0'


def check_loop():
    """Check if loop module needs to be loaded into system."""
    if not run_cmd(['modinfo', 'loop'])['success']:
        log(0, 'loop is built in the kernel.')
        return True  # assume loop is built in the kernel

    store('modprobe_loop', True)
    cmd = ['modprobe', '-q', 'loop']
    output = run_cmd(cmd, sudo=True)
    return output['success']


def set_loop_dev():
    """Set an unused loop device that's available for use."""
    if not check_loop():
        return False

    cmd = ['losetup', '-f']
    output = run_cmd(cmd, sudo=False)
    if output['success']:
        loop_dev = output['output'].strip()
        log(0, 'Found free loop device: {device}', device=loop_dev)
        return loop_dev

    log(4, 'Failed to find free loop device.')
    return False


@contextmanager
def losetup(bin_path):
    """Setup Chrome OS loop device, tear down afterwards."""
    loop_dev = set_loop_dev()
    if not loop_dev:
        yield False
    else:
        cmd = ['losetup', '-o', chromeos_offset(bin_path), loop_dev, bin_path]
        output = run_cmd(cmd, sudo=True)
        if not output['success']:
            yield False
        else:
            yield loop_dev

            run_cmd(['losetup', '-d', loop_dev], sudo=True)


@contextmanager
def mnt_loop_dev(loop_dev):
    """Mount loop device to mnt_path(), unmount afterwards"""
    mount_path = mnt_path()
    cmd = ['mount', '-t', 'ext2', '-o', 'ro', loop_dev, mount_path]
    output = run_cmd(cmd, sudo=True)
    if not output['success']:
        yield False
    else:
        yield mount_path

        unmount(mount_path)


@contextmanager
def udisks_prep_image(bin_path):
    """Setup Chrome OS loop device and mount it, tear down afterwards."""
    loop_cmd = ['udisksctl', 'loop-setup', '-o', chromeos_offset(bin_path), '-f', bin_path]
    loop_output = run_cmd(loop_cmd)
    if not loop_output['success']:
        yield False
    else:
        loop_dev = loop_output['output'].split()[-1].rstrip('.')
        mount_cmd = ['udisksctl', 'mount', '-t', 'ext2', '-o', 'ro', '-b', loop_dev]
        mount_output = run_cmd(mount_cmd)
        if not mount_output['success']:
            yield False
        else:
            mount_path = mount_output['output'].split()[-1].rstrip('.')
            yield mount_path

            unmount(mount_path)

        run_cmd(['udisksctl', 'loop-delete', '-b', loop_dev])


def select_best_chromeos_image(devices):
    """Finds the newest and smallest of the ChromeOS images given"""
    log(0, 'Find best ARM image to use from the Chrome OS recovery.conf')

    best = None
    for device in devices:
        # Select ARM hardware only
        for arm_hwid in config.CHROMEOS_RECOVERY_ARM_HWIDS:
            if '^{0} '.format(arm_hwid) in device['hwidmatch']:
                hwid = arm_hwid
                break  # We found an ARM device, rejoice !
        else:
            continue  # Not ARM, skip this device

        device['hwid'] = hwid

        # Select the first ARM device
        if best is None:
            best = device
            continue  # Go to the next device

        # Skip identical hwid
        if hwid == best['hwid']:
            continue

        # Select the newest version
        from distutils.version import LooseVersion  # pylint: disable=import-error,no-name-in-module,useless-suppression
        if LooseVersion(device['version']) > LooseVersion(best['version']):
            log(0, '{device[hwid]} ({device[version]}) is newer than {best[hwid]} ({best[version]})',
                device=device,
                best=best)
            best = device

        # Select the smallest image (disk space requirement)
        elif LooseVersion(device['version']) == LooseVersion(best['version']):
            if int(device['filesize']) + int(device['zipfilesize']) < int(best['filesize']) + int(best['zipfilesize']):
                log(0, '{device[hwid]} ({device_size}) is smaller than {best[hwid]} ({best_size})',
                    device=device,
                    best=best,
                    device_size=int(device['filesize']) + int(device['zipfilesize']),
                    best_size=int(best['filesize']) + int(best['zipfilesize']))
                best = device

    if best is None:
        log(4, 'We could not find an ARM device in the Chrome OS recovery.conf')

    log(0, 'Best ARM device is {best}', best=best)
    return best


def chromeos_config():
    """Parse the Chrome OS recovery configuration and put it in a dictionary"""
    if hasattr(chromeos_config, 'cached'):
        return getattr(chromeos_config, 'cached')

    url = config.CHROMEOS_RECOVERY_URL
    conf = [line for line in http_get(url).split('\n\n') if 'hwidmatch=' in line]

    devices = []
    for device in conf:
        device_dict = dict()
        for device_info in device.splitlines():
            if not device_info:
                continue
            try:
                key, value = device_info.split('=')
                device_dict[key] = value
            except ValueError:
                continue
        devices.append(device_dict)

    chromeos_config.cached = devices
    return devices


def check_diskspace(required_diskspace):
    """Informs about diskspace needed, checks if enough diskspace is available"""
    if not yesno_dialog(localize(30001),  # Due to distributing issues, this takes a long time
                        localize(30006, diskspace=sizeof_fmt(required_diskspace))):
        raise KeyboardInterrupt

    while required_diskspace >= diskspace():
        if yesno_dialog(localize(30004), localize(30055)):  # Not enough space, alternative path?
            update_temp_path(browsesingle(3, localize(30909), 'files'))  # Temporary path
            continue

        ok_dialog(localize(30004),  # Not enough free disk space
                  localize(30018, diskspace=sizeof_fmt(required_diskspace)))
        raise KeyboardInterrupt


def unzip_progress(source, destination=temp_path(), file_to_unzip=None, method=unzip, progress_dict=None):
    """
    Extracts the ChromeOS image (specified in args) to destination (specified in args), and shows a progress.


    If a progress is specified, it should be a dictionary, looking like this:

    progress_dict = {'progress': progress_dialog().create(), 'time': 0, 'percent': 0}
    """
    from threading import Thread
    from xbmc import sleep

    if progress_dict:
        progress = progress_dict['progress']
        time = progress_dict['time']
        percent = progress_dict['percent']
        remaining = 95 - percent
    else:
        progress = progress_dialog()
        progress.create(heading=localize(30043), message=localize(30044))  # Extracting Widevine CDM

        progress.update(
            0,
            message='{line1}\n{line2}\n{line3}'.format(
                line1=localize(30045),  # Uncompressing image
                line2=localize(30046, mins=0, secs=0),  # This may take several minutes
                line3=localize(30047))  # Please do not interrupt this process
        )
        time = 0
        percent = 0
        remaining = 95

    unzip_result = []
    args = (source, destination, file_to_unzip, unzip_result)
    unzip_thread = Thread(target=method, args=args, name='ImageExtraction')
    unzip_thread.start()

    while unzip_thread.is_alive():
        offset = remaining * 0.6 / 100
        percent += offset
        remaining -= offset
        time += 1
        sleep(1000)
        progress.update(
            int(percent),
            message='{line1}\n{line2}\n{line3}'.format(
                line1=localize(30045),  # Uncompressing image
                line2=localize(30046, mins=time // 60, secs=time % 60),  # This may take several minutes
                line3=localize(30047))  # Please do not interrupt this process
        )

    return (progress, bool(unzip_result), (time, percent))


def write_config(backup_path, arm_device):
    """Writes the chromeos_config"""
    import json

    json_file = os.path.join(backup_path, arm_device['version'], os.path.basename(config.CHROMEOS_RECOVERY_URL) + '.json')
    with open(json_file, 'w') as config_file:
        config_file.write(json.dumps(chromeos_config(), indent=4))


def install_widevine_arm(backup_path):
    """Installs Widevine CDM on ARM-based architectures."""
    arm_device = select_best_chromeos_image(chromeos_config())
    if arm_device is None:
        ok_dialog(localize(30004), localize(30005))
        return ''

    if system_os() != 'Linux':
        ok_dialog(localize(30004), localize(30019, os=system_os()))
        return False

    options = {'udisksctl': install_wv_udisks, '7z': install_wv_p7zip}
    try:
        for cmd in list(options):
            if cmd_exists(cmd):
                result = options[cmd](arm_device, backup_path)

                if result:
                    return result
                log(3, '{cmd} is available but failed, trying next option', cmd=cmd)

        return install_wv_legacy(arm_device, backup_path)
    except KeyboardInterrupt:
        return False


def install_wv_udisks(arm_device, backup_path):
    """Install widevine with the help of udisks"""
    # Estimated required disk space: takes into account an extra 20 MiB buffer
    required_diskspace = 20971520 + int(arm_device['zipfilesize']) + int(arm_device['filesize'])
    check_diskspace(required_diskspace)

    if not cmd_exists('fdisk') and not cmd_exists('parted'):
        ok_dialog(localize(30004), localize(30020, command1='fdisk', command2='parted'))  # Commands are missing
        return False

    url = arm_device['url']
    downloaded = http_download(url, message=localize(30022), checksum=arm_device['sha1'], hash_alg='sha1', dl_size=int(arm_device['zipfilesize']))  # Downloading the recovery image
    if not downloaded:
        return False

    bin_filename = url.split('/')[-1].replace('.zip', '')
    bin_path = os.path.join(temp_path(), bin_filename)
    progress, unzip_result, _ = unzip_progress(store('download_path'), temp_path(), file_to_unzip=bin_filename)
    if not unzip_result:
        return False
    with udisks_prep_image(bin_path) as mount_path:
        if not mount_path:
            return False

        progress.update(96, message=localize(30048))  # Extracting Widevine CDM
        extract_widevine_from_img(os.path.join(backup_path, arm_device['version']), mount_path)
        write_config(backup_path, arm_device)

        return (progress, arm_device['version'])
    progress.close()

    return False


def install_wv_p7zip(arm_device, backup_path):
    """Install widevine with the help of p7zip"""
    # Estimated required disk space: takes into account an extra 20 MiB buffer and a guessed size of the ROOT-A.img
    required_diskspace = 20971520 + int(arm_device['filesize']) + int(arm_device['zipfilesize']) + 2*1024**3
    check_diskspace(required_diskspace)

    url = arm_device['url']
    downloaded = http_download(url, message=localize(30022), checksum=arm_device['sha1'], hash_alg='sha1', dl_size=int(arm_device['zipfilesize']))  # Downloading the recovery image
    if not downloaded:
        return False

    bin_filename = url.split('/')[-1].replace('.zip', '')
    progress, unzip_result, time_per = unzip_progress(store('download_path'), temp_path(), file_to_unzip=bin_filename, method=p7unzip)
    if not unzip_result:
        progress.close()
        return False

    part_filename = 'ROOT-A.img'
    progress, unzip_result, _ = unzip_progress(os.path.join(temp_path(), bin_filename), destination=temp_path(), file_to_unzip=part_filename, method=p7unzip, progress_dict={'progress': progress, 'time': time_per[0], 'percent': time_per[1]})
    if not unzip_result:
        progress.close()
        return False

    progress.update(96, message=localize(30048))  # Extracting Widevine CDM
    lib_path = 'opt/google/chrome/libwidevinecdm.so'
    if not p7unzip(os.path.join(temp_path(), part_filename), destination=os.path.join(backup_path, arm_device['version']), file_to_unzip=lib_path):
        progress.close()
        return False

    write_config(backup_path, arm_device)
    return (progress, arm_device['version'])


def install_wv_legacy(arm_device, backup_path):
    """Fallback method to install widevine if the others fail"""
    # Estimated required disk space: takes into account an extra 20 MiB buffer
    required_diskspace = 20971520 + int(arm_device['zipfilesize']) + int(arm_device['filesize'])
    check_diskspace(required_diskspace)

    if not cmd_exists('fdisk') and not cmd_exists('parted'):
        ok_dialog(localize(30004), localize(30020, command1='fdisk', command2='parted'))  # Commands are missing
        return False

    if not cmd_exists('mount'):
        ok_dialog(localize(30004), localize(30021, command='mount'))  # Mount command is missing
        return False

    if not cmd_exists('losetup'):
        ok_dialog(localize(30004), localize(30021, command='losetup'))  # Losetup command is missing
        return False

    root_cmds = ['mount', 'umount', 'losetup', 'modprobe']
    if os.getuid() != 0 and not yesno_dialog(localize(30001),  # Ask for permission to run cmds as root
                                             localize(30030, cmds=', '.join(root_cmds)),
                                             nolabel=localize(30028), yeslabel=localize(30027)):
        raise KeyboardInterrupt

    url = arm_device['url']
    downloaded = http_download(url, message=localize(30022), checksum=arm_device['sha1'], hash_alg='sha1', dl_size=int(arm_device['zipfilesize']))  # Downloading the recovery image
    if not downloaded:
        return False

    bin_filename = url.split('/')[-1].replace('.zip', '')
    bin_path = os.path.join(temp_path(), bin_filename)
    progress, unzip_result, _ = unzip_progress(store('download_path'), temp_path(), file_to_unzip=bin_filename)
    if not unzip_result:
        return False
    with losetup(bin_path) as loop_dev:
        if not loop_dev:
            return False

        with mnt_loop_dev(loop_dev) as mount_path:
            if not mount_path:
                return False

            progress.update(96, message=localize(30048))  # Extracting Widevine CDM
            extract_widevine_from_img(os.path.join(backup_path, arm_device['version']), mount_path)
            write_config(backup_path, arm_device)

            return (progress, arm_device['version'])
    progress.close()

    return False


def extract_widevine_from_img(backup_path, mount_path):
    """Extract the Widevine CDM binary from the mounted Chrome OS image"""
    for root, _, files in os.walk(mount_path):
        if str('libwidevinecdm.so') not in files:
            continue
        cdm_path = os.path.join(root, 'libwidevinecdm.so')
        log(0, 'Found libwidevinecdm.so in {path}', path=cdm_path)
        if not exists(backup_path):
            mkdir(backup_path)
        copy(cdm_path, os.path.join(backup_path, 'libwidevinecdm.so'))
        return True

    log(4, 'Failed to find Widevine CDM binary in Chrome OS image.')
    return False


def unmount(mount_path):
    """Unmount mountpoint if mounted"""
    while os.path.ismount(mount_path):
        log(0, 'Unmount {mountpoint}', mountpoint=mount_path)
        umount_output = run_cmd(['umount', mount_path], sudo=True)
        if not umount_output['success']:
            break
