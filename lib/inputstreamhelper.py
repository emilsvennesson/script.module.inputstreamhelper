# -*- coding: utf-8 -*-
''' Implements the main InputStream Helper class '''
from __future__ import absolute_import, division, unicode_literals

import os
import platform
import zipfile
import json
import time
import subprocess
import shutil
import re
from distutils.version import LooseVersion  # pylint: disable=import-error,no-name-in-module
from datetime import datetime, timedelta
import struct

try:  # Python 3
    from urllib.error import HTTPError
    from urllib.request import build_opener, install_opener, ProxyHandler, urlopen
except ImportError:  # Python 2
    from urllib2 import build_opener, HTTPError, install_opener, ProxyHandler, urlopen

import config

from kodi_six import xbmc, xbmcaddon, xbmcgui, xbmcvfs

ADDON = xbmcaddon.Addon('script.module.inputstreamhelper')
ADDON_PROFILE = xbmc.translatePath(ADDON.getAddonInfo('profile'))
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_VERSION = ADDON.getAddonInfo('version')
LANGUAGE = ADDON.getLocalizedString


# NOTE: Work around issue caused by platform still using os.popen()
#       This helps to survive 'IOError: [Errno 10] No child processes'
if hasattr(os, 'popen'):
    del os.popen


class InputStreamException(Exception):
    ''' Stub Exception '''


def has_socks():
    ''' Test if socks is installed, and remember this information '''

    # If it wasn't stored before, check if socks is installed
    if not hasattr(has_socks, 'installed'):
        try:
            import socks  # noqa: F401; pylint: disable=unused-variable,unused-import
            has_socks.installed = True
        except ImportError:
            has_socks.installed = False
            return None  # Detect if this is the first run

    # Return the stored value
    return has_socks.installed


def system_os():
    ''' Get system platform, and remember this information '''

    # If it wasn't stored before, get the correct value
    if not hasattr(system_os, 'name'):
        if xbmc.getCondVisibility('system.platform.android'):
            system_os.name = 'Android'
        else:
            system_os.name = platform.system()

    # Return the stored value
    return system_os.name


class Helper:
    ''' The main InputStream Helper class '''

    def __init__(self, protocol, drm=None):
        ''' Initialize InputStream Helper class '''
        self._url = None
        self._download_path = None
        self._loop_dev = None
        self._modprobe_loop = False
        self._attached_loop_dev = False
        self._mounted = False

        self.protocol = protocol
        self.drm = drm

        self._log('Platform information: {0}'.format(platform.uname()))

        if self.protocol not in config.INPUTSTREAM_PROTOCOLS:
            raise InputStreamException('UnsupportedProtocol')

        self.inputstream_addon = config.INPUTSTREAM_PROTOCOLS[self.protocol]

        if self.drm:
            if self.drm not in config.DRM_SCHEMES:
                raise InputStreamException('UnsupportedDRMScheme')

            self.drm = config.DRM_SCHEMES[drm]

        # Add proxy support to HTTP requests
        install_opener(build_opener(ProxyHandler(self._get_proxies())))

    def __repr__(self):
        return 'Helper({0}, drm={1})'.format(self.protocol, self.drm)

    @classmethod
    def _diskspace(cls):
        """Return the free disk space available (in bytes) in temp_path."""
        statvfs = os.statvfs(cls._temp_path())
        return statvfs.f_frsize * statvfs.f_bavail

    @classmethod
    def _temp_path(cls):
        temp_path = os.path.join(ADDON_PROFILE, 'tmp')
        if not xbmcvfs.exists(temp_path):
            xbmcvfs.mkdir(temp_path)

        return temp_path

    @classmethod
    def _mnt_path(cls):
        mnt_path = os.path.join(cls._temp_path(), 'mnt')
        if not xbmcvfs.exists(mnt_path):
            xbmcvfs.mkdir(mnt_path)

        return mnt_path

    @classmethod
    def _addon_cdm_path(cls):
        cdm_path = os.path.join(ADDON_PROFILE, 'cdm')
        if not xbmcvfs.exists(cdm_path):
            xbmcvfs.mkdir(cdm_path)

        return cdm_path

    @classmethod
    def _ia_cdm_path(cls):
        """Return the specified CDM path for inputstream.adaptive."""
        addon = xbmcaddon.Addon('inputstream.adaptive')
        cdm_path = xbmc.translatePath(addon.getSetting('DECRYPTERPATH'))
        if not xbmcvfs.exists(cdm_path):
            xbmcvfs.mkdir(cdm_path)

        return cdm_path

    @classmethod
    def _widevine_config_path(cls):
        return os.path.join(cls._addon_cdm_path(), config.WIDEVINE_CONFIG_NAME)

    @classmethod
    def _load_widevine_config(cls):
        with open(cls._widevine_config_path(), 'r') as config_file:
            return json.loads(config_file.read())

    @classmethod
    def _widevine_path(cls):
        for filename in os.listdir(cls._ia_cdm_path()):
            if 'widevine' in filename and filename.endswith(config.CDM_EXTENSIONS):
                return os.path.join(cls._ia_cdm_path(), filename)

        return False

    @classmethod
    def _kodi_version(cls):
        version = xbmc.getInfoLabel('System.BuildVersion')
        return version.split(' ')[0]

    @classmethod
    def _arch(cls):
        """Map together and return the system architecture."""
        arch = platform.machine()
        if arch == 'aarch64' and (struct.calcsize('P') * 8) == 32:
            # Detected 64-bit kernel in 32-bit userspace, use 32-bit arm widevine
            arch = 'arm'
        if arch == 'AMD64':
            arch_bit = platform.architecture()[0]
            if arch_bit == '32bit':
                arch = 'x86'  # else, arch = AMD64
        elif 'armv' in arch:
            arm_version = re.search(r'\d+', arch.split('v')[1])
            if arm_version:
                arch = 'armv' + arm_version.group()
        if arch in config.ARCH_MAP:
            return config.ARCH_MAP[arch]

        return arch

    @staticmethod
    def _sizeof_fmt(num, suffix='B'):
        """Return size of file in a human readable string."""
        # https://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size
        for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
            if abs(num) < 1024.0:
                return "%3.1f%s%s" % (num, unit, suffix)
            num /= 1024.0
        return "%.1f%s%s" % (num, 'Yi', suffix)

    @staticmethod
    def _cmd_exists(cmd):
        """Check whether cmd exists on system."""
        # https://stackoverflow.com/questions/377017/test-if-executable-exists-in-python
        return subprocess.call('type ' + cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0

    def _helper_disabled(self):
        """Return if inputstreamhelper has been disabled in settings.xml."""
        disabled = ADDON.getSetting('disabled')
        if not disabled:
            ADDON.setSetting('disabled', 'false')  # create default entry
            disabled = 'false'

        if disabled == 'true':
            self._log('inputstreamhelper is disabled in settings.xml.')
            return True

        self._log('inputstreamhelper is enabled. You can disable inputstreamhelper by setting \"disabled\" to \"true\" in settings.xml \
        (Note: only recommended for developers knowing what they\'re doing!)')
        return False

    def _inputstream_version(self):
        addon = xbmcaddon.Addon(self.inputstream_addon)
        return addon.getAddonInfo('version')

    @staticmethod
    def _log(string):
        ''' InputStream Helper log method '''
        xbmc.log(msg='[{0}-{1}]: {2}'.format(ADDON_ID, ADDON_VERSION, string), level=xbmc.LOGDEBUG)

    def _chromeos_offset(self, bin_path):
        """Calculate the Chrome OS losetup start offset using fdisk/parted."""
        if self._cmd_exists('fdisk'):
            cmd = ['fdisk', bin_path, '-l']
        else:  # parted
            cmd = ['parted', '-s', bin_path, 'unit s print']

        output = self._run_cmd(cmd, sudo=False)
        if output['success']:
            for line in output['output'].splitlines():
                partition_data = line.split()
                if partition_data:
                    if partition_data[0] == '3' or '.bin3' in partition_data[0]:
                        offset = int(partition_data[1].replace('s', ''))
                        return str(offset * config.CHROMEOS_BLOCK_SIZE)

        self._log('Failed to calculate losetup offset.')
        return False

    def _run_cmd(self, cmd, sudo=False, shell=False):
        """Run subprocess command and return if it succeeds as a bool."""
        if sudo and os.getuid() != 0 and self._cmd_exists('sudo'):
            cmd.insert(0, 'sudo')
        try:
            output = subprocess.check_output(cmd, shell=shell, stderr=subprocess.STDOUT)
            success = True
            self._log('{0} cmd executed successfully.'.format(cmd))
        except subprocess.CalledProcessError as error:
            output = error.output
            success = False
            self._log('{0} cmd failed.'.format(cmd))
        except OSError as error:
            output = ''
            success = False
            self._log('{0} cmd doesn\'t exist. {1}'.format(cmd, error))
        if output.rstrip():
            self._log('{0} cmd output: \n{1}'.format(cmd, output))
        if 'sudo' in cmd:
            subprocess.call(['sudo', '-k'])  # reset timestamp

        return {
            'output': output,
            'success': success
        }

    def _check_loop(self):
        """Check if loop module needs to be loaded into system."""
        if not self._run_cmd(['modinfo', 'loop'])['success']:
            self._log('loop is built in the kernel.')
            return True  # assume loop is built in the kernel

        self._modprobe_loop = True
        cmd = ['modprobe', '-q', 'loop']
        output = self._run_cmd(cmd, sudo=True, shell=True)
        return output['success']

    def _set_loop_dev(self):
        """Set an unused loop device that's available for use."""
        cmd = ['losetup', '-f']
        output = self._run_cmd(cmd, sudo=False)
        if output['success']:
            self._loop_dev = output['output'].strip()
            self._log('Found free loop device: {0}'.format(self._loop_dev))
            return True

        self._log('Failed to find free loop device.')
        return False

    def _losetup(self, bin_path):
        """Setup Chrome OS loop device."""
        cmd = ['losetup', self._loop_dev, bin_path, '-o', self._chromeos_offset(bin_path)]
        output = self._run_cmd(cmd, sudo=True)
        if output['success']:
            self._attached_loop_dev = True
            return True

        return False

    def _mnt_loop_dev(self):
        """Mount loop device to self._mnt_path()"""
        cmd = ['mount', '-t', 'ext2', self._loop_dev, '-o', 'ro', self._mnt_path()]
        output = self._run_cmd(cmd, sudo=True)
        if output['success']:
            self._mounted = True
            return True

        return False

    def _has_widevine(self):
        """Checks if Widevine CDM is installed on system."""
        if system_os() == 'Android':  # widevine is built in on android
            return True

        if self._widevine_path():
            self._log('Found Widevine binary at {0}'.format(self._widevine_path().encode('utf-8')))
            return True

        self._log('Widevine is not installed.')
        return False

    def _json_rpc_request(self, payload):
        """Kodi JSON-RPC request. Return the response in a dictionary."""
        self._log('jsonrpc payload: {0}'.format(payload))
        response = xbmc.executeJSONRPC(json.dumps(payload))
        self._log('jsonrpc response: {0}'.format(response))

        return json.loads(response)

    def _http_get(self):
        ''' Perform an HTTP GET request and return content '''
        self._log('Request URL: {0}'.format(self._url))
        try:
            req = urlopen(self._url)
            self._log('Response code: {0}'.format(req.getcode()))
            if 400 <= req.getcode() < 600:
                raise HTTPError('HTTP %s Error for url: %s' % (req.getcode(), self._url), response=req)
        except HTTPError:
            xbmcgui.Dialog().ok(LANGUAGE(30004), LANGUAGE(30013).format(self._url.split('/')[-1]))  # Failed to retrieve file
            return None
        content = req.read()
        self._log('Response: {0}'.format(content))
        return content

    def _http_download(self, message=None):
        """Makes HTTP request and displays a progress dialog on download."""
        self._log('Request URL: {0}'.format(self._url))
        filename = self._url.split('/')[-1]
        try:
            req = urlopen(self._url)
            self._log('Response code: {0}'.format(req.getcode()))
            if 400 <= req.getcode() < 600:
                raise HTTPError('HTTP %s Error for url: %s' % (req.getcode(), self._url), response=req)
        except HTTPError:
            xbmcgui.Dialog().ok(LANGUAGE(30004), LANGUAGE(30013).format(filename))  # Failed to retrieve file
            return False

        if not message:  # display "downloading [filename]"
            message = LANGUAGE(30015).format(filename)  # Downloading file

        self._download_path = os.path.join(self._temp_path(), filename)
        total_length = float(req.info().get('content-length'))
        progress_dialog = xbmcgui.DialogProgress()
        progress_dialog.create(LANGUAGE(30014), message)  # Download in progress

        chunk_size = 32 * 1024
        with open(self._download_path, 'wb') as f:
            dl = 0
            while True:
                chunk = req.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                dl += len(chunk)
                percent = int(dl * 100 / total_length)
                if progress_dialog.iscanceled():
                    progress_dialog.close()
                    req.close()
                    return False
                progress_dialog.update(percent)

        progress_dialog.close()
        return True

    def _has_inputstream(self):
        """Checks if selected InputStream add-on is installed."""
        payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'Addons.GetAddonDetails',
            'params': {
                'addonid': self.inputstream_addon
            }
        }
        data = self._json_rpc_request(payload)
        if 'error' in data:
            self._log('{0} is not installed.'.format(self.inputstream_addon))
            return False

        self._log('{0} is installed.'.format(self.inputstream_addon))
        return True

    def _inputstream_enabled(self):
        """Returns whether selected InputStream add-on is enabled.."""
        payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'Addons.GetAddonDetails',
            'params': {
                'addonid': self.inputstream_addon,
                'properties': ['enabled']
            }
        }
        data = self._json_rpc_request(payload)
        if data['result']['addon']['enabled']:
            self._log('{0} {1} is enabled.'.format(self.inputstream_addon, self._inputstream_version()))
            return True

        self._log('{0} is disabled.'.format(self.inputstream_addon))
        return False

    def _enable_inputstream(self):
        """Enables selected InputStream add-on."""
        payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'Addons.SetAddonEnabled',
            'params': {
                'addonid': self.inputstream_addon,
                'enabled': True
            }
        }
        data = self._json_rpc_request(payload)
        if 'error' in data:
            return False

        return True

    def _supports_widevine(self):
        """Checks if Widevine is supported on the architecture/operating system/Kodi version."""
        if self._arch() not in config.WIDEVINE_SUPPORTED_ARCHS:
            self._log('Unsupported Widevine architecture found: {0}'.format(self._arch()))
            xbmcgui.Dialog().ok(LANGUAGE(30004), LANGUAGE(30007))  # Widevine not available on this architecture
            return False

        if system_os() not in config.WIDEVINE_SUPPORTED_OS:
            self._log('Unsupported Widevine OS found: {0}'.format(system_os()))
            xbmcgui.Dialog().ok(LANGUAGE(30004), LANGUAGE(30011).format(system_os()))  # Operating system not supported by Widevine
            return False

        if LooseVersion(config.WIDEVINE_MINIMUM_KODI_VERSION[system_os()]) > LooseVersion(self._kodi_version()):
            self._log('Unsupported Kodi version for Widevine: {0}'.format(self._kodi_version()))
            xbmcgui.Dialog().ok(LANGUAGE(30004), LANGUAGE(30010).format(config.WIDEVINE_MINIMUM_KODI_VERSION[system_os()]))  # Kodi too old
            return False

        if 'WindowsApps' in xbmc.translatePath('special://xbmcbin/'):  # uwp is not supported
            self._log('Unsupported UWP Kodi version detected.')
            xbmcgui.Dialog().ok(LANGUAGE(30004), LANGUAGE(30012))  # Windows Store Kodi falls short
            return False

        return True

    def _select_best_chromeos_image(self, devices):
        self._log('Find best ARM image to use from recovery.conf')

        best = None
        for device in devices:
            # Select ARM hardware only
            for arm_hwid in config.CHROMEOS_RECOVERY_ARM_HWIDS:
                if arm_hwid in device['hwidmatch']:
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
            if LooseVersion(device['version']) > LooseVersion(best['version']):
                self._log('{device[hwid]} ({device[version]}) is newer than {best[hwid]} ({best[version]})'.format(device=device, best=best))  # pylint: disable=invalid-format-index
                best = device

            # Select the smallest image (disk space requirement)
            elif LooseVersion(device['version']) == LooseVersion(best['version']):
                if int(device['filesize']) + int(device['zipfilesize']) < int(best['filesize']) + int(best['zipfilesize']):
                    self._log('{device[hwid]} ({device_size}) is smaller than {best[hwid]} ({best_size})'.format(device=device, best=best, device_size=int(device['filesize']) + int(device['zipfilesize']), best_size=int(best['filesize']) + int(best['zipfilesize'])))  # pylint: disable=invalid-format-index
                    best = device

        return best

    def _latest_widevine_version(self, eula=False):
        """Returns the latest available version of Widevine CDM/Chrome OS."""
        if eula:
            self._url = config.WIDEVINE_VERSIONS_URL
            versions = self._http_get().decode()
            return versions.split()[-1]

        ADDON.setSetting('last_update', str(time.mktime(datetime.utcnow().timetuple())))
        if 'x86' in self._arch():
            self._url = config.WIDEVINE_VERSIONS_URL
            versions = self._http_get().decode()
            return versions.split()[-1]

        devices = self._chromeos_config()
        arm_device = self._select_best_chromeos_image(devices)
        if arm_device is None:
            self._log('We could not find an ARM device in recovery.conf')
            xbmcgui.Dialog().ok(LANGUAGE(30004), LANGUAGE(30005))
            return ''
        return arm_device['version']

    def _chromeos_config(self):
        """Parses the Chrome OS recovery configuration and put it in a dictionary."""
        self._url = config.CHROMEOS_RECOVERY_URL
        conf = [x for x in self._http_get().decode().split('\n\n') if 'hwidmatch=' in x]

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

        return devices

    def _install_widevine_x86(self):
        """Install Widevine CDM on x86 based architectures."""
        cdm_version = self._latest_widevine_version()
        cdm_os = config.WIDEVINE_OS_MAP[system_os()]
        cdm_arch = config.WIDEVINE_ARCH_MAP_X86[self._arch()]
        self._url = config.WIDEVINE_DOWNLOAD_URL.format(version=cdm_version, os=cdm_os, arch=cdm_arch)

        downloaded = self._http_download()
        if downloaded:
            progress_dialog = xbmcgui.DialogProgress()
            progress_dialog.create(heading=LANGUAGE(30043), line1=LANGUAGE(30044))  # Extracting Widevine CDM
            self._unzip(self._addon_cdm_path())

            if not self._widevine_eula():
                self._cleanup()
                return False

            self._install_cdm()
            self._cleanup()

            if self._has_widevine():
                if os.path.lexists(self._widevine_config_path()):
                    os.remove(self._widevine_config_path())
                os.rename(os.path.join(self._addon_cdm_path(), config.WIDEVINE_MANIFEST_FILE), self._widevine_config_path())
                wv_check = self._check_widevine()
                if wv_check:
                    xbmcgui.Dialog().notification(LANGUAGE(30037), LANGUAGE(30003))  # Widevine successfully installed
                progress_dialog.close()
                return wv_check

            progress_dialog.close()
            xbmcgui.Dialog().ok(LANGUAGE(30004), LANGUAGE(30005))  # An error occurred

        return False

    def _install_widevine_arm(self):
        """Installs Widevine CDM on ARM-based architectures."""
        root_cmds = ['mount', 'umount', 'losetup', 'modprobe']
        devices = self._chromeos_config()
        arm_device = self._select_best_chromeos_image(devices)
        if arm_device is None:
            self._log('We could not find an ARM device in recovery.conf')
            xbmcgui.Dialog().ok(LANGUAGE(30004), LANGUAGE(30005))
            return ''
        required_diskspace = int(arm_device['filesize']) + int(arm_device['zipfilesize'])
        if xbmcgui.Dialog().yesno(LANGUAGE(30001),  # Due to distributing issues, this takes a long time
                                  LANGUAGE(30006).format(self._sizeof_fmt(required_diskspace))) and self._widevine_eula():
            if system_os() != 'Linux':
                xbmcgui.Dialog().ok(LANGUAGE(30004), LANGUAGE(30019).format(system_os()))
                return False

            if required_diskspace >= self._diskspace():
                xbmcgui.Dialog().ok(LANGUAGE(30004),  # Not enough free disk space
                                    LANGUAGE(30018).format(self._sizeof_fmt(required_diskspace)))
                return False

            if not self._cmd_exists('fdisk') and not self._cmd_exists('parted'):
                xbmcgui.Dialog().ok(LANGUAGE(30004), LANGUAGE(30020).format('fdisk', 'parted'))  # Commands are missing
                return False

            if not self._cmd_exists('mount'):
                xbmcgui.Dialog().ok(LANGUAGE(30004), LANGUAGE(30021).format('mount'))  # Mount command is missing
                return False

            if not self._cmd_exists('losetup'):
                xbmcgui.Dialog().ok(LANGUAGE(30004), LANGUAGE(30021).format('losetup'))  # Losetup command is missing
                return False

            if os.getuid() != 0:  # ask for permissions to run cmds as root
                if not xbmcgui.Dialog().yesno(LANGUAGE(30001), LANGUAGE(30030).format(', '.join(root_cmds)), yeslabel=LANGUAGE(30027), nolabel=LANGUAGE(30028)):
                    return False

            self._url = arm_device['url']
            downloaded = self._http_download(message=LANGUAGE(30022))  # Downloading the recovery image
            if downloaded:
                progress_dialog = xbmcgui.DialogProgress()
                progress_dialog.create(heading=LANGUAGE(30043), line1=LANGUAGE(30044))  # Extracting Widevine CDM
                bin_filename = self._url.split('/')[-1].replace('.zip', '')
                bin_path = os.path.join(self._temp_path(), bin_filename)

                progress_dialog.update(5, line1=LANGUAGE(30045), line2=LANGUAGE(30046), line3=LANGUAGE(30047))  # Uncompressing image
                success = [
                    self._unzip(self._temp_path(), bin_filename),
                    self._check_loop(), self._set_loop_dev(),
                    self._losetup(bin_path), self._mnt_loop_dev()
                ]
                if all(success):
                    progress_dialog.update(91, line1=LANGUAGE(30048))  # Extracting Widevine CDM
                    self._extract_widevine_from_img()
                    progress_dialog.update(94, line1=LANGUAGE(30049))  # Installing Widevine CDM
                    self._install_cdm()
                    progress_dialog.update(97, line1=LANGUAGE(30050))  # Finishing
                    self._cleanup()
                    if self._has_widevine():
                        with open(self._widevine_config_path(), 'w') as config_file:
                            config_file.write(json.dumps(devices, indent=4))
                        wv_check = self._check_widevine()
                        if wv_check:
                            progress_dialog.update(100, line1=LANGUAGE(30003))  # Widevine installation was successful
                            xbmcgui.Dialog().notification(LANGUAGE(30037), LANGUAGE(30003))  # Widevine installation was successful
                        progress_dialog.close()
                        return wv_check
                else:
                    progress_dialog.update(100, line1=LANGUAGE(30050))  # Finishing
                    self._cleanup()

                progress_dialog.close()
                xbmcgui.Dialog().ok(LANGUAGE(30004), LANGUAGE(30005))  # An error occurred

        return False

    def _install_widevine(self):
        """Wrapper function that calls Widevine installer method depending on architecture."""
        if self._supports_widevine():
            if 'x86' in self._arch():
                return self._install_widevine_x86()

            return self._install_widevine_arm()

        return False

    def _first_run(self):
        """Check if this add-on version is running for the first time"""

        # Get versions
        settings_version = ADDON.getSetting('version')
        if settings_version == '':
            settings_version = '0.3.4'  # settings_version didn't exist in version 0.3.4 and older
        addon_version = ADDON.getAddonInfo('version')

        # Compare versions
        if LooseVersion(addon_version) > LooseVersion(settings_version):
            # New version found, save addon_version to settings
            ADDON.setSetting('version', addon_version)
            self._log('inputstreamhelper version %s is running for the first time' % addon_version)
            return True
        return False

    def _update_widevine(self):
        """Prompts user to upgrade Widevine CDM when a newer version is available."""
        last_update = ADDON.getSetting('last_update')
        if last_update and not self._first_run():
            last_update_dt = datetime.fromtimestamp(float(ADDON.getSetting('last_update')))
            if last_update_dt + timedelta(days=config.WIDEVINE_UPDATE_INTERVAL_DAYS) >= datetime.utcnow():
                self._log('Widevine update check was made on {0}'.format(last_update_dt.isoformat()))
                return

        wv_config = self._load_widevine_config()
        latest_version = self._latest_widevine_version()
        if 'x86' in self._arch():
            component = 'Widevine CDM'
            current_version = wv_config['version']
        else:
            component = 'Chrome OS'
            current_version = self._select_best_chromeos_image(wv_config)['version']
        self._log('Latest {0} version is {1}'.format(component, latest_version))
        self._log('Current {0} version installed is {1}'.format(component, current_version))

        if LooseVersion(latest_version) > LooseVersion(current_version):
            self._log('There is an update available for {0}'.format(component))
            if xbmcgui.Dialog().yesno(LANGUAGE(30040), LANGUAGE(30033), yeslabel=LANGUAGE(30034), nolabel=LANGUAGE(30028)):
                self._install_widevine()
            else:
                self._log('User declined to update {0}.'.format(component))
        else:
            self._log('User is on the latest available {0} version.'.format(component))

    def _widevine_eula(self):
        """Displays the Widevine EULA and prompts user to accept it."""
        if os.path.exists(os.path.join(self._addon_cdm_path(), config.WIDEVINE_LICENSE_FILE)):
            license_file = os.path.join(self._addon_cdm_path(), config.WIDEVINE_LICENSE_FILE)
            with open(license_file, 'r') as f:
                eula = f.read().strip().replace('\n', ' ')
        else:  # grab the license from the x86 files
            self._log('Acquiring Widevine EULA from x86 files.')
            self._url = config.WIDEVINE_DOWNLOAD_URL.format(version=self._latest_widevine_version(eula=True), os='mac', arch='x64')
            downloaded = self._http_download(message=LANGUAGE(30025))  # Acquiring EULA
            if not downloaded:
                return False

            with zipfile.ZipFile(self._download_path) as z:
                with z.open(config.WIDEVINE_LICENSE_FILE) as f:
                    eula = f.read().strip().replace('\n', ' ')

        return xbmcgui.Dialog().yesno(LANGUAGE(30026), eula, yeslabel=LANGUAGE(30027), nolabel=LANGUAGE(30028))  # Widevine CDM EULA

    def _extract_widevine_from_img(self):
        """Extracts the Widevine CDM binary from the mounted Chrome OS image."""
        for root, dirs, files in os.walk(str(self._mnt_path())):  # pylint: disable=unused-variable
            for filename in files:
                if filename == 'libwidevinecdm.so':
                    cdm_path = os.path.join(root, filename)
                    self._log('Found libwidevinecdm.so in {0}'.format(cdm_path))
                    shutil.copyfile(cdm_path, os.path.join(self._addon_cdm_path(), filename))
                    return True

        self._log('Failed to find Widevine CDM binary in Chrome OS image.')
        return False

    def _missing_widevine_libs(self):
        """Parses ldd output of libwidevinecdm.so and displays dialog if any depending libraries are missing."""
        if system_os() != 'Linux':  # this should only be needed for linux
            return None

        if self._cmd_exists('ldd'):
            if not os.access(self._widevine_path(), os.X_OK):
                self._log('Changing {0} permissions to 744.'.format(self._widevine_path()))
                os.chmod(self._widevine_path(), 0o744)

            missing_libs = []
            cmd = ['ldd', self._widevine_path()]
            output = self._run_cmd(cmd, sudo=False)
            if output['success']:
                for line in output['output'].splitlines():
                    if '=>' not in str(line):
                        continue
                    lib_path = str(line).strip().split('=>')
                    lib = lib_path[0].strip()
                    path = lib_path[1].strip()
                    if path == 'not found':
                        missing_libs.append(lib)

                if missing_libs:
                    self._log('Widevine is missing the following libraries: {0}'.format(missing_libs))
                    return missing_libs

                self._log('There are no missing Widevine libraries! :-)')
                return None

        if self._arch() == 'arm64' and (struct.calcsize('P') * 8) == 64:
            self._log('ARM64 ldd check failed. User needs 32-bit userspace.')
            xbmcgui.Dialog().ok(LANGUAGE(30004), LANGUAGE(30039))  # Widevine not available on ARM64

        self._log('Failed to check for missing Widevine libraries.')
        return None

    def _check_widevine(self):
        """Checks that all Widevine components are installed and available."""
        if system_os() == 'Android':  # no checks needed for Android
            return True

        if not os.path.exists(self._widevine_config_path()):
            self._log('Widevine config is missing. Reinstall is required.')
            xbmcgui.Dialog().ok(LANGUAGE(30001), LANGUAGE(30031))  # An update of Widevine is required
            return self._install_widevine()

        if 'x86' in self._arch():  # check that widevine arch matches system arch
            wv_config = self._load_widevine_config()
            if config.WIDEVINE_ARCH_MAP_X86[self._arch()] != wv_config['arch']:
                self._log('Widevine/system arch mismatch. Reinstall is required.')
                xbmcgui.Dialog().ok(LANGUAGE(30001), LANGUAGE(30031))  # An update of Widevine is required
                return self._install_widevine()

        if self._missing_widevine_libs():
            xbmcgui.Dialog().ok(LANGUAGE(30004), LANGUAGE(30032).format(', '.join(self._missing_widevine_libs())))  # Missing libraries
            return False

        self._update_widevine()
        return True

    def _install_cdm(self):
        """Loops through local cdm folder and symlinks/copies binaries to inputstream cdm_path."""
        for cdm_file in os.listdir(self._addon_cdm_path()):
            if cdm_file.endswith(config.CDM_EXTENSIONS):
                self._log('[install_cdm] found file: {0}'.format(cdm_file))
                cdm_path_addon = os.path.join(self._addon_cdm_path(), cdm_file)
                cdm_path_inputstream = os.path.join(self._ia_cdm_path(), cdm_file)
                if system_os() == 'Windows':  # copy on windows
                    shutil.copyfile(cdm_path_addon, cdm_path_inputstream)
                else:
                    if os.path.lexists(cdm_path_inputstream):
                        os.remove(cdm_path_inputstream)  # it's ok to overwrite
                    os.symlink(cdm_path_addon, cdm_path_inputstream)

        return True

    def _unzip(self, unzip_dir, file_to_unzip=None):
        """Unzips files to specified path."""
        zip_obj = zipfile.ZipFile(self._download_path)
        if file_to_unzip:
            for filename in zip_obj.namelist():
                if filename == file_to_unzip:
                    zip_obj.extract(filename, unzip_dir)
                    return True
            return False

        # extract all files
        zip_obj.extractall(unzip_dir)
        return True

    def _cleanup(self):
        """Clean up function after Widevine CDM installation."""
        if self._mounted:
            cmd = ['umount', self._mnt_path()]
            umount_output = self._run_cmd(cmd, sudo=True)
            if umount_output['success']:
                self._mounted = False
        if self._attached_loop_dev:
            cmd = ['losetup', '-d', self._loop_dev]
            unattach_output = self._run_cmd(cmd, sudo=True)
            if unattach_output['success']:
                self._loop_dev = False
        if self._modprobe_loop:
            xbmcgui.Dialog().notification(LANGUAGE(30035), LANGUAGE(30036))  # Unload by hand in CLI
        if not self._has_widevine():
            shutil.rmtree(self._addon_cdm_path())

        shutil.rmtree(self._temp_path())
        return True

    def _supports_hls(self):
        """Return if HLS support is available in inputstream.adaptive."""
        if LooseVersion(self._inputstream_version()) >= LooseVersion(config.HLS_MINIMUM_IA_VERSION):
            return True

        self._log('HLS is unsupported on {0} version {1}'.format(self.inputstream_addon, self._inputstream_version()))
        return False

    def _check_drm(self):
        """Main function for ensuring that specified DRM system is installed and available."""
        if not self.drm or self.inputstream_addon != 'inputstream.adaptive':
            return True

        if self.drm == 'widevine':
            if not self._has_widevine():
                if xbmcgui.Dialog().yesno(LANGUAGE(30041), LANGUAGE(30002), yeslabel=LANGUAGE(30038), nolabel=LANGUAGE(30028)):  # Widevine required
                    return self._install_widevine()

                return False

            return self._check_widevine()

        return True

    def _install_inputstream(self):
        """Install inputstream addon."""
        try:
            # See if there's an installed repo that has it
            xbmc.executebuiltin('InstallAddon({})'.format(self.inputstream_addon))

            # Check if InputStream add-on exists!
            xbmcaddon.Addon('{}'.format(self.inputstream_addon))

            self._log('inputstream addon installed from repo')
            return True
        except RuntimeError:
            self._log('inputstream addon not installed')
            return False

    def check_inputstream(self):
        """Main function. Ensures that all components are available for InputStream add-on playback."""
        if self._helper_disabled():  # blindly return True if helper has been disabled
            return True
        if self.drm == 'widevine' and not self._supports_widevine():
            return False
        if not self._has_inputstream():
            # Try to install InputStream add-on
            if not self._install_inputstream():
                xbmcgui.Dialog().ok(LANGUAGE(30004), LANGUAGE(30008).format(self.inputstream_addon))  # inputstream is missing on system
                return False
        elif not self._inputstream_enabled():
            ok = xbmcgui.Dialog().yesno(LANGUAGE(30001), LANGUAGE(30009).format(self.inputstream_addon, self.inputstream_addon))  # inputstream is disabled
            if ok:
                self._enable_inputstream()
            return False
        self._log('{0} {1} is installed and enabled.'.format(self.inputstream_addon, self._inputstream_version()))

        if self.protocol == 'hls' and not self._supports_hls():
            xbmcgui.Dialog().ok(LANGUAGE(30004),  # HLS Minimum version is needed
                                LANGUAGE(30017).format(self.inputstream_addon, config.HLS_MINIMUM_IA_VERSION))
            return False

        return self._check_drm()

    @staticmethod
    def _get_global_setting(setting):
        json_result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Settings.GetSettingValue", "params": {"setting": "%s"}, "id": 1}' % setting)
        return json.loads(json_result)['result']['value']

    def _get_proxies(self):
        usehttpproxy = self._get_global_setting('network.usehttpproxy')
        if usehttpproxy is False:
            return None

        httpproxytype = self._get_global_setting('network.httpproxytype')

        socks_supported = has_socks()
        if httpproxytype != 0 and not socks_supported:
            # Only open the dialog the first time (to avoid multiple popups)
            if socks_supported is None:
                xbmcgui.Dialog().ok('', LANGUAGE(30042))  # Requires PySocks
            return None

        proxy_types = ['http', 'socks4', 'socks4a', 'socks5', 'socks5h']
        if 0 <= httpproxytype <= 5:
            httpproxyscheme = proxy_types[httpproxytype]
        else:
            httpproxyscheme = 'http'

        httpproxyserver = self._get_global_setting('network.httpproxyserver')
        httpproxyport = self._get_global_setting('network.httpproxyport')
        httpproxyusername = self._get_global_setting('network.httpproxyusername')
        httpproxypassword = self._get_global_setting('network.httpproxypassword')

        if httpproxyserver and httpproxyport and httpproxyusername and httpproxypassword:
            proxy_address = '%s://%s:%s@%s:%s' % (httpproxyscheme, httpproxyusername, httpproxypassword, httpproxyserver, httpproxyport)
        elif httpproxyserver and httpproxyport and httpproxyusername:
            proxy_address = '%s://%s@%s:%s' % (httpproxyscheme, httpproxyusername, httpproxyserver, httpproxyport)
        elif httpproxyserver and httpproxyport:
            proxy_address = '%s://%s:%s' % (httpproxyscheme, httpproxyserver, httpproxyport)
        elif httpproxyserver:
            proxy_address = '%s://%s' % (httpproxyscheme, httpproxyserver)
        else:
            return None

        return dict(http=proxy_address, https=proxy_address)
