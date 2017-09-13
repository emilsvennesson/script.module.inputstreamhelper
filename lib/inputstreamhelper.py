import os
import platform
import zipfile
import json
from distutils.version import LooseVersion

import config
import xbmc
import xbmcaddon
import xbmcgui


class InputStreamHelper(object):
    def __init__(self, protocol, drm=None):
        self._addon = xbmcaddon.Addon('script.module.inputstreamhelper')
        self._logging_prefix = '[%s-%s]' % (self._addon.getAddonInfo('id'), self._addon.getAddonInfo('version'))
        self._language = self._addon.getLocalizedString
        self._arch = self._get_arch(platform.machine())
        self._os = platform.system()
        self._log('Platform information: {0}'.format(platform.uname()))

        self.protocol = protocol
        if self.protocol not in config.INPUTSTREAM_PROTOCOLS:
            raise self.InputStreamException('UnsupportedProtocol')
        else:
            self._inputstream_addon = config.INPUTSTREAM_PROTOCOLS[self.protocol]
        if not drm or drm not in config.DRM_SCHEMES:
            raise self.InputStreamException('UnsupportedDRMScheme')
        else:
            self.drm = config.DRM_SCHEMES[drm]

    class InputStreamException(Exception):
        pass

    def _get_arch(self, arch):
        if arch in config.ARCHS:
            return config.ARCHS[arch]
        else:
            return arch

    def _log(self, string):
        msg = '{0}: {1}'.format(self._logging_prefix, string)
        xbmc.log(msg=msg, level=xbmc.LOGDEBUG)

    def _cdm_path(self):
        addon = xbmcaddon.Addon('inputstream.adaptive')
        return xbmc.translatePath(addon.getSetting('DECRYPTERPATH'))

    def _kodi_version(self):
        version = xbmc.getInfoLabel('System.BuildVersion')
        return version.split(' ')[0]

    def _inputstream_version(self):
        addon = xbmcaddon.Addon(self._inputstream_addon)
        return addon.getAddonInfo('version')

    def _has_widevine_cdm(self):
        if xbmc.getCondVisibility('system.platform.android'):  # widevine is built in on android
            return True
        else:
            for filename in os.listdir(self._cdm_path()):
                if 'widevine' in filename and filename.endswith(config.WIDEVINE_CDM_EXTENSIONS):
                    self._log('Found Widevine binary at {0}'.format(os.path.join(self._cdm_path(), filename)))
                    return True

            self.log('Widevine is not installed.')
            return False

    def _json_rpc_request(self, payload):
        self._log('jsonrpc payload: {0}'.format(payload))
        response = xbmc.executeJSONRPC(json.dumps(payload))
        self._log('jsonrpc response: {0}'.format(response))

        return json.loads(response)

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
        if data['result']['addon']['enabled']:
            return True
        else:
            return False

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
            dialog.ok(self._language(30004), self._language(30007))
            return False
        if self._os not in config.WIDEVINE_SUPPORTED_OS:
            dialog.ok(self._language(30004), self._language(30011).format(self._os))
            return False
        if LooseVersion(min_version) > LooseVersion(self._kodi_version()):
            dialog.ok(self._language(30004), self._language(30010).format(min_version))
            return False
        if 'WindowsApps' in xbmc.translatePath('special://xbmcbin/'):  # uwp is not supported
            dialog.ok(self._language(30004), self._language(30012))
            return False

        return True

    def check_for_inputstream(self):
        """Ensures that selected InputStream add-on is installed and enabled.
        Displays a select dialog if add-on is installed but not enabled."""
        dialog = xbmcgui.Dialog()
        if not self._has_inputstream():
            self._log('{0} is not installed.'.format(self._inputstream_addon))
            dialog.ok(self._language(30004), self._language(30008).format(self._inputstream_addon))
        elif not self._inputstream_enabled():
            self._log('{0} is not enabled.'.format(self._inputstream_addon))
            ok = dialog.yesno(self._language(30001), self._language(30009).format(self._inputstream_addon, self._inputstream_addon))
            if ok:
                return self._enable_inputstream()
            else:
                return False
        else:
            self._log('{0} is installed and enabled.'.format(self._inputstream_addon))
            return True

    def supports_hls(self):
        if self.protocol == 'hls' and LooseVersion(self._inputstream_version()) >= LooseVersion(config.HLS_MINIMUM_IA_VERSION):
            return True
        else:
            return False
