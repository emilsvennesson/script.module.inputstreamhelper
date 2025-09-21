# -*- coding: utf-8 -*-
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=missing-docstring

import unittest
import platform

import inputstreamhelper
from test_utils import delete_cached, cleanup

xbmc = __import__('xbmc')
xbmcaddon = __import__('xbmcaddon')
xbmcgui = __import__('xbmcgui')
xbmcvfs = __import__('xbmcvfs')


class LinuxARMTests(unittest.TestCase):

    def setUp(self):
        delete_cached()
        cleanup()
        inputstreamhelper.system_os = lambda: 'Linux'
        inputstreamhelper.widevine.widevine.system_os = lambda: 'Linux'
        inputstreamhelper.widevine.repo.system_os = lambda: 'Linux'

    def test_check_inputstream_mpd_lacros(self):
        platform.machine = lambda: 'arm'

        inputstreamhelper.userspace64 = lambda: False
        inputstreamhelper.widevine.arm.userspace64 = lambda: False

        is_helper = inputstreamhelper.Helper('mpd', drm='com.widevine.alpha')
        is_helper.remove_widevine()
        is_installed = is_helper.check_inputstream()
        self.assertTrue(is_installed, True)

    def test_check_inputstream_mpd_chromeos(self):
        platform.machine = lambda: 'arm'

        inputstreamhelper.cdm_from_lacros = lambda: False
        inputstreamhelper.widevine.widevine.cdm_from_lacros = lambda: False
        inputstreamhelper.widevine.arm.cdm_from_lacros = lambda: False

        inputstreamhelper.userspace64 = lambda: False
        inputstreamhelper.widevine.arm.userspace64 = lambda: False

        is_helper = inputstreamhelper.Helper('mpd', drm='com.widevine.alpha')
        is_helper.remove_widevine()
        is_installed = is_helper.check_inputstream()
        self.assertTrue(is_installed, True)

    def test_check_inputstream_hls_again(self):
        platform.machine = lambda: 'armv7'

        inputstreamhelper.userspace64 = lambda: False
        inputstreamhelper.widevine.arm.userspace64 = lambda: False

        is_helper = inputstreamhelper.Helper('hls', drm='com.widevine.alpha')
        is_installed = is_helper.check_inputstream()
        self.assertTrue(is_installed, True)

    def test_check_inputstream_rtmp(self):
        platform.machine = lambda: 'armv8'

        inputstreamhelper.userspace64 = lambda: False
        inputstreamhelper.widevine.arm.userspace64 = lambda: False

        is_helper = inputstreamhelper.Helper('rtmp')
        is_installed = is_helper.check_inputstream()
        self.assertTrue(is_installed, True)

    def test_check_inputstream_disabled(self):
        platform.machine = lambda: 'arm'

        inputstreamhelper.userspace64 = lambda: False
        inputstreamhelper.widevine.arm.userspace64 = lambda: False

        is_helper = inputstreamhelper.Helper('mpd', drm='com.widevine.alpha')
        is_helper.disable()
        is_installed = is_helper.check_inputstream()
        is_helper.enable()
        self.assertTrue(is_installed, True)


if __name__ == '__main__':
    unittest.main()
