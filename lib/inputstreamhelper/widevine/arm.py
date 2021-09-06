# -*- coding: utf-8 -*-
# MIT License (see LICENSE.txt or https://opensource.org/licenses/MIT)
"""Implements ARM specific widevine functions"""

from __future__ import absolute_import, division, unicode_literals
import os
import json

from .. import config
from ..kodiutils import browsesingle, kodi_os, localize, log, ok_dialog, open_file, progress_dialog, yesno_dialog
from ..utils import diskspace, http_download, http_get, http_head, run_cmd, sizeof_fmt, store, system_os, update_temp_path
from .arm_chromeos import ChromeOSImage


def select_best_chromeos_image(devices):
    """Finds the newest and smallest of the ChromeOS images given"""
    log(0, 'Find best ARM image to use from the Chrome OS recovery.json')

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

    return best


def chromeos_config():
    """Reads the Chrome OS recovery configuration"""
    return json.loads(http_get(config.CHROMEOS_RECOVERY_URL))


def hardcoded_chromeos_image():
    """Gets a hardcoded ChromeOS image"""
    arm_device = config.HARDCODED_CHROMEOS_IMAGE
    http_status = http_head(arm_device['url'])
    if http_status == 200:
        return arm_device
    return None


def supports_widevine_arm64tls():
    """Whether the system supports newer Widevine CDM's that use TLS with 64-byte alignment"""
    # With the release of Widevine CDM 4.10.2252.0, Google uses a newer dynamic library that uses TLS with 64-byte alignment and needs a patched glibc to work
    # Google will remove support for older ARM Widevine CDM's at some point
    # More info at https://github.com/xbmc/inputstream.adaptive/issues/678 and https://www.widevine.com/news

    # LibreELEC 9.2.7: Check if TCMalloc library is preloaded or linked
    libtcmalloc = 'libtcmalloc'
    with open('/proc/self/maps', 'r') as maps:  # pylint: disable=unspecified-encoding
        process_maps = maps.read()
    is_tcmalloc_preloaded = bool(libtcmalloc in process_maps)

    # Experimental: detect TLS 64-byte alignment support, searching for 'arm64tls' string in ldd version
    cmd = ['ldd', '--version']
    ldd_version = run_cmd(cmd).get('output').split('\n')[0].split(' ')[-1]
    has_tls64bytes_support = bool('arm64tls' in ldd_version)

    # Experimental: detect TLS 64-byte alignment support, checking environment variable
    if not has_tls64bytes_support:
        try:
            libc_patchlevel = int(os.environ['LIBC_WIDEVINE_PATCHLEVEL'])
            has_tls64bytes_support = libc_patchlevel >= 1
        except KeyError:
            has_tls64bytes_support = False

    return is_tcmalloc_preloaded or has_tls64bytes_support


def install_widevine_arm(backup_path):
    """Installs Widevine CDM on ARM-based architectures."""
    arm_device = None
    if not supports_widevine_arm64tls():
        # Propose user to install older version
        if yesno_dialog(localize(30066), localize(30067, os=kodi_os())):  # Your os probably doesn't support the newest Widevine CDM. Try older one?
            # Install hardcoded ChromeOS image
            ok_dialog(localize(30066), localize(30068))  # Please note that Google will remove support for older Widevine CDM's at some point
            arm_device = hardcoded_chromeos_image()
            devices = arm_device

    # Select newest and smallest ChromeOS image
    if arm_device is None:
        devices = chromeos_config()
        arm_device = select_best_chromeos_image(devices)

    if arm_device is None:
        log(4, 'We could not find an ARM device in the Chrome OS recovery.json')
        ok_dialog(localize(30004), localize(30005))
        return False

    # Estimated required disk space: takes into account an extra 20 MiB buffer
    required_diskspace = 20971520 + int(arm_device['zipfilesize'])
    if yesno_dialog(localize(30001),  # Due to distributing issues, this takes a long time
                    localize(30006, diskspace=sizeof_fmt(required_diskspace))):
        if system_os() != 'Linux':
            ok_dialog(localize(30004), localize(30019, os=system_os()))
            return False

        while required_diskspace >= diskspace():
            if yesno_dialog(localize(30004), localize(30055)):  # Not enough space, alternative path?
                update_temp_path(browsesingle(3, localize(30909), 'files'))  # Temporary path
                continue

            ok_dialog(localize(30004),  # Not enough free disk space
                      localize(30018, diskspace=sizeof_fmt(required_diskspace)))
            return False

        log(2, 'Downloading ChromeOS image for Widevine: {hwid} ({version})'.format(**arm_device))
        url = arm_device['url']
        downloaded = http_download(url, message=localize(30022), checksum=arm_device['sha1'], hash_alg='sha1',
                                   dl_size=int(arm_device['zipfilesize']))  # Downloading the recovery image
        if downloaded:
            progress = progress_dialog()
            progress.create(heading=localize(30043), message=localize(30044))  # Extracting Widevine CDM

            extracted = ChromeOSImage(store('download_path')).extract_file(
                filename=config.WIDEVINE_CDM_FILENAME[system_os()],
                extract_path=os.path.join(backup_path, arm_device['version']),
                progress=progress)

            if not extracted:
                log(4, 'Extracting widevine from the zip failed!')
                progress.close()
                return False

            recovery_file = os.path.join(backup_path, arm_device['version'], os.path.basename(config.CHROMEOS_RECOVERY_URL))
            config_file = os.path.join(backup_path, arm_device['version'], 'config.json')
            with open_file(recovery_file, 'w') as reco_file:  # pylint: disable=unspecified-encoding
                reco_file.write(json.dumps(devices, indent=4))
            with open_file(config_file, 'w') as conf_file:
                conf_file.write(json.dumps(arm_device))

            return (progress, arm_device['version'])

    return False
