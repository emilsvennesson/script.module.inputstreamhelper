# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Dag Wieers (@dagwieers) <dag@wieers.com>
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=invalid-name,missing-docstring

from __future__ import absolute_import, division, print_function, unicode_literals
import unittest
import platform
import inputstreamhelper
from test_utils import delete_cached

xbmc = __import__('xbmc')
xbmcaddon = __import__('xbmcaddon')
xbmcgui = __import__('xbmcgui')
xbmcvfs = __import__('xbmcvfs')


class WindowsX64Tests(unittest.TestCase):

    def setUp(self):
        delete_cached()

    def test_check_inputstream_mpd(self):
        inputstreamhelper.system_os = lambda: 'Windows'
        platform.machine = lambda: 'x86_64'
        is_helper = inputstreamhelper.Helper('mpd', drm='com.widevine.alpha')
        is_helper.remove_widevine()
        is_installed = is_helper.check_inputstream()
        self.assertTrue(is_installed, True)

    def test_check_inputstream_hls_again(self):
        inputstreamhelper.system_os = lambda: 'Windows'
        platform.machine = lambda: 'AMD64'
        platform.architecture = lambda: ['64bit', '']
        is_helper = inputstreamhelper.Helper('hls', drm='com.widevine.alpha')
        is_installed = is_helper.check_inputstream()
        self.assertTrue(is_installed, True)

    def test_check_inputstream_rtmp(self):
        inputstreamhelper.system_os = lambda: 'Windows'
        platform.machine = lambda: 'x86_64'
        is_helper = inputstreamhelper.Helper('rtmp')
        is_installed = is_helper.check_inputstream()
        self.assertTrue(is_installed, True)

    def test_check_inputstream_disabled(self):
        inputstreamhelper.system_os = lambda: 'Windows'
        platform.machine = lambda: 'x86_64'
        is_helper = inputstreamhelper.Helper('mpd', drm='com.widevine.alpha')
        is_helper.disable()
        is_installed = is_helper.check_inputstream()
        is_helper.enable()
        self.assertTrue(is_installed, True)


if __name__ == '__main__':
    unittest.main()
