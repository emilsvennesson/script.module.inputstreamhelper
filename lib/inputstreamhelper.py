import os
import platform
import zipfile
import json
import subprocess
import shutil
from distutils.version import LooseVersion

import requests

import config
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs


class Helper(object):
    def __init__(self, protocol, drm=None):
        self._addon = xbmcaddon.Addon('script.module.inputstreamhelper')
        self._addon_profile = xbmc.translatePath(self._addon.getAddonInfo('profile'))
        self._logging_prefix = '[{0}-{1}]'.format(self._addon.getAddonInfo('id'), self._addon.getAddonInfo('version'))
        self._language = self._addon.getLocalizedString
        self._arch = self._get_arch(platform.machine())
        self._os = platform.system()
        self._log('Platform information: {0}'.format(platform.uname()))

        self._url = None
        self._download_path = None
        self._bin_path = None
        self._mounted = False
        self._losetup = False

        self.protocol = protocol
        self.drm = drm

        if self.protocol not in config.INPUTSTREAM_PROTOCOLS:
            raise self.InputStreamException('UnsupportedProtocol')
        else:
            self._inputstream_addon = config.INPUTSTREAM_PROTOCOLS[self.protocol]

        if self.drm:
            if self.drm not in config.DRM_SCHEMES:
                raise self.InputStreamException('UnsupportedDRMScheme')
            else:
                self.drm = config.DRM_SCHEMES[drm]

    class InputStreamException(Exception):
        pass

    @staticmethod
    def sizeof_fmt(num, suffix='B'):
        # https://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size
        for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
            if abs(num) < 1024.0:
                return "%3.1f%s%s" % (num, unit, suffix)
            num /= 1024.0
        return "%.1f%s%s" % (num, 'Yi', suffix)

    @staticmethod
    def _cmd_exists(cmd):
        # https://stackoverflow.com/questions/377017/test-if-executable-exists-in-python
        return subprocess.call('type ' + cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0

    def _get_arch(self, arch):
        if arch in config.X86_MAP:
            return config.X86_MAP[arch]
        elif 'armv' in arch:
            arm_arch = 'armv' + arch.split('v')[1][:-1]
            return arm_arch

        return arch

    def _log(self, string):
        msg = '{0}: {1}'.format(self._logging_prefix, string)
        xbmc.log(msg=msg, level=xbmc.LOGDEBUG)

    def _diskspace(self):
        statvfs = os.statvfs(self._cdm_path())
        return statvfs.f_frsize * statvfs.f_bavail

    def _temp_path(self):
        temp_path = os.path.join(self._addon_profile, 'tmp')
        if not xbmcvfs.exists(temp_path):
            xbmcvfs.mkdir(temp_path)

        return temp_path

    def _mnt_path(self):
        mnt_path = os.path.join(self._temp_path(), 'mnt')
        if not xbmcvfs.exists(mnt_path):
            xbmcvfs.mkdir(mnt_path)

        return mnt_path

    def _cdm_path(self):
        cdm_path = os.path.join(self._addon_profile, 'cdm')
        if not xbmcvfs.exists(cdm_path):
            xbmcvfs.mkdir(cdm_path)

        return cdm_path

    def _inputstream_cdm_path(self):
        addon = xbmcaddon.Addon('inputstream.adaptive')
        cdm_path = xbmc.translatePath(addon.getSetting('DECRYPTERPATH'))
        if not xbmcvfs.exists(cdm_path):
            xbmcvfs.mkdir(cdm_path)

        return cdm_path

    def _kodi_version(self):
        version = xbmc.getInfoLabel('System.BuildVersion')
        return version.split(' ')[0]

    def _inputstream_version(self):
        addon = xbmcaddon.Addon(self._inputstream_addon)
        return addon.getAddonInfo('version')

    def _parse_chromeos_offset(self):
        """Calculate the Chrome OS losetup start offset using fdisk/parted."""
        if self._cmd_exists('fdisk'):
            cmd = ['fdisk', self._bin_path, '-l']
        else:  # parted
            cmd = ['parted', '-s', self._bin_path, 'unit s print']
        self._log('losetup calculation cmd: {0}'.format(cmd))

        output = subprocess.check_output(cmd)
        self._log('losetup calculation output: {0}'.format(output))
        for line in output.splitlines():
            partition_data = line.split()
            if partition_data:
                if partition_data[0] == '3' or '.bin3' in partition_data[0]:
                    offset = int(partition_data[1].replace('s', ''))
                    return str(offset * config.CHROMEOS_BLOCK_SIZE)

        self._log('Failed to calculate losetup offset.')
        return False

    def _losetup(self):
        """Setup Chrome OS loop device."""
        cmd = ['losetup', config.LOOP_DEV, self._bin_path, '-o', self._parse_chromeos_offset()]
        subprocess.check_output(cmd)
        self._losetup = True
        return True

    def _mnt_loop_dev(self):
        """Mount loop device to self._mnt_path()"""
        cmd = ['mount', '-t', 'ext2', config.LOOP_DEV, '-o', 'ro', self._mnt_path()]
        subprocess.check_output(cmd)
        self._mounted = True
        return True

    def _has_widevine_cdm(self):
        if xbmc.getCondVisibility('system.platform.android'):  # widevine is built in on android
            return True
        else:
            for filename in os.listdir(self._inputstream_cdm_path()):
                if 'widevine' in filename and filename.endswith(config.CDM_EXTENSIONS):
                    self._log('Found Widevine binary at {0}'.format(os.path.join(self._inputstream_cdm_path(), filename)))
                    return True

            self._log('Widevine is not installed.')
            return False

    def _json_rpc_request(self, payload):
        self._log('jsonrpc payload: {0}'.format(payload))
        response = xbmc.executeJSONRPC(json.dumps(payload))
        self._log('jsonrpc response: {0}'.format(response))

        return json.loads(response)

    def _http_request(self, download=False):
        """Makes HTTP request and displays a progress dialog on download."""
        self._log('Request URL: {0}'.format(self._url))
        filename = self._url.split('/')[-1]
        busy_dialog = xbmcgui.DialogBusy()
        dialog = xbmcgui.Dialog()

        try:
            busy_dialog.create()
            req = requests.get(self._url, stream=download, verify=False)
            self._log('Response code: {0}'.format(req.status_code))
            if not download:
                self._log('Response: {0}'.format(req.content))
            req.raise_for_status()
        except requests.exceptions.HTTPError:
            busy_dialog.close()
            dialog.ok(self._language(30004), self._language(30013).format(filename))
            return False

        busy_dialog.close()
        if download:
            self._download_path = os.path.join(self._temp_path(), filename)
            total_length = float(req.headers.get('content-length'))
            progress_dialog = xbmcgui.DialogProgress()
            progress_dialog.create(self._language(30014), self._language(30015).format(filename))

            with open(self._download_path, 'wb') as f:
                dl = 0
                for chunk in req.iter_content(chunk_size=1024):
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
        else:
            return req.content

    def _has_inputstream(self):
        """Checks if selected InputStream add-on is installed."""
        payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'Addons.GetAddonDetails',
            'params': {
                'addonid': self._inputstream_addon
            }
        }
        data = self._json_rpc_request(payload)
        if 'error' in data:
            return False
        else:
            return True

    def _inputstream_enabled(self):
        """Returns whether selected InputStream add-on is enabled.."""
        payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'Addons.GetAddonDetails',
            'params': {
                'addonid': self._inputstream_addon,
                'properties': ['enabled']
            }
        }
        data = self._json_rpc_request(payload)
        return data['result']['addon']['enabled']

    def _enable_inputstream(self):
        """Enable selected InputStream add-on."""
        payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'Addons.SetAddonEnabled',
            'params': {
                'addonid': self._inputstream_addon,
                'enabled': True
            }
        }
        data = self._json_rpc_request(payload)
        if 'error' in data:
            return False
        else:
            return True

    def _supports_widevine(self):
        dialog = xbmcgui.Dialog()
        if xbmc.getCondVisibility('system.platform.android'):
            min_version = config.WIDEVINE_ANDROID_MINIMUM_KODI_VERSION
        else:
            min_version = config.WIDEVINE_MINIMUM_KODI_VERSION

        if self._arch not in config.WIDEVINE_SUPPORTED_ARCHS:
            self._log('Unsupported Widevine architecture found: {0}'.format(self._arch))
            dialog.ok(self._language(30004), self._language(30007))
            return False
        if self._os not in config.WIDEVINE_SUPPORTED_OS:
            self._log('Unsupported Widevine OS found: {0}'.format(self._os))
            dialog.ok(self._language(30004), self._language(30011).format(self._os))
            return False
        if LooseVersion(min_version) > LooseVersion(self._kodi_version()):
            self._log('Unsupported Kodi version for Widevine: {0}'.format(self._kodi_version()))
            dialog.ok(self._language(30004), self._language(30010).format(min_version))
            return False
        if 'WindowsApps' in xbmc.translatePath('special://xbmcbin/'):  # uwp is not supported
            self._log('Unsupported UWP Kodi version detected.')
            dialog.ok(self._language(30004), self._language(30012))
            return False

        return True

    def _current_widevine_cdm_version(self):
        """Return the latest available version of Widevine CDM."""
        self._url = config.WIDEVINE_CURRENT_VERSION_URL
        return self._http_request()

    def _parse_chromeos_recovery_conf(self):
        """Parse the download URL and required disk space from the Chrome OS recovery configuration."""
        download_dict = {}
        self._url = config.CHROMEOS_RECOVERY_CONF
        conf = self._http_request().split('\n\n')
        for device in conf:
            if config.CHROMEOS_ARM_HWID in device:
                for line in device.splitlines():
                    if 'url' in line:
                        download_dict['url'] = line.split('url=')[1]
                    if 'zipfilesize' in line:
                        zip_filesize = int(line.split('filesize=')[1])
                    if 'zip' not in line and 'filesize' in line:
                        bin_filesize = int(line.split('filesize=')[1])

                download_dict['required_diskspace'] = zip_filesize + bin_filesize
                return download_dict

        self._log('Failed to parse Chrome OS recovery.conf')
        return False

    def _install_widevine_cdm_x86(self):
        dialog = xbmcgui.Dialog()
        if dialog.yesno(self._language(30001), self._language(30002)):
            cdm_version = self._current_widevine_cdm_version()
            cdm_os = config.WIDEVINE_OS_MAP[self._os]
            cdm_arch = config.WIDEVINE_ARCH_MAP_X86[self._arch][self._os]
            self._url = config.WIDEVINE_DOWNLOAD_URL.format(cdm_version, cdm_os, cdm_arch)

            downloaded = self._http_request(download=True)
            if downloaded:
                self._unzip_cdm()
                self._install_cdm()
                self._cleanup()
                if self._has_widevine_cdm():
                    dialog.ok(self._language(30001), self._language(30003))
                    return True
                else:
                    dialog.ok(self._language(30004), self._language(30005))

        return False

    def _install_widevine_cdm_arm(self):
        dialog = xbmcgui.Dialog()
        download_dict = self._parse_chromeos_recovery_conf()
        self._url = download_dict['url']

        if dialog.yesno(self._language(30001), self._language(30002)) and dialog.yesno(self._language(30001), self._language(30006).format(self.sizeof_fmt(download_dict['required_diskspace']))):
            if self._os != 'Linux':
                dialog.ok(self._language(30004), self._language(30019).format(self._os))
                return False
            if download_dict['required_diskspace'] >= self._diskspace():
                dialog.ok(self._language(30004), self._language(30018).format(self.sizeof_fmt(download_dict['diskspace'])))
                return False
            if not self._cmd_exists('fdisk') and not self._cmd_exists('parted'):
                dialog.ok(self._language(30004), self._language(30020).format('fdisk', 'parted'))
                return False
            if not self._cmd_exists('mount'):
                dialog.ok(self._language(30004), self._language(30021).format('mount'))
                return False
            if not self._cmd_exists('losetup'):
                dialog.ok(self._language(30004), self._language(30021).format('losetup'))
                return False

            downloaded = self._http_request(download=True)
            if downloaded:
                if not self._unzip_bin() or not self._losetup() or not self._mnt_loop_dev():
                    self._cleanup()
                    return False
                else:
                    self._extract_cdm_from_img()
                    self._install_cdm()
                    self._cleanup()
                    if self._has_widevine_cdm():
                        dialog.ok(self._language(30001), self._language(30003))
                        return True
                    else:
                        dialog.ok(self._language(30004), self._language(30005))

        return False

    def _extract_cdm_from_img(self):
        busy_dialog = xbmcgui.DialogBusy()
        busy_dialog.create()
        """Extract the Widevine CDM binary from the mounted Chrome OS image."""
        for root, dirs, files in os.walk(self._mnt_path()):
            for filename in files:
                if 'widevinecdm' in filename and filename.endswith(config.CDM_EXTENSIONS):
                    shutil.copyfile(os.path.join(root, filename), os.path.join(self._cdm_path(), filename))
                    break

        busy_dialog.close()
        return True

    def _install_cdm(self):
        """Loop through local cdm folder and symlink/copy binaries to inputstream cdm_path."""
        busy_dialog = xbmcgui.DialogBusy()
        busy_dialog.create()
        for cdm_file in os.listdir(self._cdm_path()):
            if cdm_file.endswith(config.CDM_EXTENSIONS):
                cdm_path_addon = os.path.join(self._cdm_path(), cdm_file)
                cdm_path_inputstream = os.path.join(self._inputstream_cdm_path(), cdm_file)
                if self._os == 'Windows':  # don't symlink on Windows
                    shutil.copyfile(cdm_path_addon, cdm_path_inputstream)
                else:
                    os.symlink(cdm_path_addon, cdm_path_inputstream)

        busy_dialog.close()
        return True

    def _unzip_bin(self):
        busy_dialog = xbmcgui.DialogBusy()
        zip_obj = zipfile.ZipFile(self._download_path)
        busy_dialog.create()
        for filename in zip_obj.namelist():
            if filename.endswith('.bin'):
                zip_obj.extract(filename, self._temp_path())
                busy_dialog.close()
                self._bin_path = os.path.join(self._temp_path(), filename)
                return True

    def _unzip_cdm(self):
        busy_dialog = xbmcgui.DialogBusy()
        busy_dialog.create()
        zip_obj = zipfile.ZipFile(self._download_path)
        zip_obj.extractall(self._cdm_path())
        busy_dialog.close()
        return True

    def _cleanup(self):
        """Clean up after Widevine DRM installation."""
        busy_dialog = xbmcgui.DialogBusy()
        busy_dialog.create()
        if self._mounted:
            cmd = ['umount', self._mnt_path()]
            subprocess.check_call(cmd)
            self._mounted = False
        if self._losetup:
            cmd = ['losetup', '-d', config.LOOP_DEV]
            subprocess.check_call(cmd)
            self._losetup = False

        shutil.rmtree(self._temp_path())
        busy_dialog.close()
        return True

    def _supports_hls(self):
        if LooseVersion(self._inputstream_version()) >= LooseVersion(config.HLS_MINIMUM_IA_VERSION):
            return True
        else:
            self._log('HLS is not supported on {0} version {1}'.format(self._inputstream_addon, self._inputstream_version()))
            dialog = xbmcgui.Dialog()
            dialog.ok(self._language(30004), self._language(30017).format(self._inputstream_addon, config.HLS_MINIMUM_IA_VERSION))
            return False

    def _check_drm(self):
        """Main function for ensuring that specified DRM system is installed and available."""
        if self.drm and self._inputstream_addon == 'inputstream.adaptive':
            if self.drm == 'widevine':
                if not self._supports_widevine():
                    return False
                if not self._has_widevine_cdm():
                    if 'x86' in self._arch:
                        return self._install_widevine_cdm_x86()
                    else:
                        return self._install_widevine_cdm_arm()

        return True

    def check_inputstream(self):
        """Main function. Ensures that all components are available for InputStream add-on playback."""
        dialog = xbmcgui.Dialog()
        if not self._has_inputstream():
            self._log('{0} is not installed.'.format(self._inputstream_addon))
            dialog.ok(self._language(30004), self._language(30008).format(self._inputstream_addon))
            return False
        elif not self._inputstream_enabled():
            self._log('{0} is not enabled.'.format(self._inputstream_addon))
            ok = dialog.yesno(self._language(30001), self._language(30009).format(self._inputstream_addon, self._inputstream_addon))
            if ok:
                self._enable_inputstream()
            else:
                return False
        if self.protocol == 'hls' and not self._supports_hls():
            return False

        self._log('{0} is installed and enabled.'.format(self._inputstream_addon))
        return self._check_drm()
