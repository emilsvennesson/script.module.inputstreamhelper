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
        self._arch = platform.machine()
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

    def has_widevine_cdm(self):
        if xbmc.getCondVisibility('system.platform.android'):  # widevine is built in on android
            return True
        else:
            for filename in os.listdir(self._cdm_path()):
                if 'widevine' in filename and filename.endswith(config.WIDEVINE_CDM_EXTENSIONS):
                    self._log('Found Widevine binary at {0}'.format(os.path.join(self._cdm_path(), filename)))
                    return True

            self.log('Widevine is not installed.')
            return False

    def supports_hls(self):
        if self.protocol == 'hls' and LooseVersion(self._inputstream_version()) >= LooseVersion(config.HLS_MINIMUM_IA_VERSION):
            return True
        else:
            return False
