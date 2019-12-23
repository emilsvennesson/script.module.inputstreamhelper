# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Dag Wieers (@dagwieers) <dag@wieers.com>
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=duplicate-code,invalid-name,missing-docstring,protected-access

from __future__ import absolute_import, division, print_function, unicode_literals
import os
import unittest
import platform
import inputstreamhelper
import default

xbmc = __import__('xbmc')
xbmcaddon = __import__('xbmcaddon')
xbmcgui = __import__('xbmcgui')
xbmcvfs = __import__('xbmcvfs')


class LinuxVendorTests(unittest.TestCase):

    def setUp(self):
        with open('test/cdm/libwidevinecdm_vendor.so', 'w') as fdesc:
            fdesc.write('Linux\n1.2.3.4')

    def tearDown(self):
        os.unlink('test/cdm/libwidevinecdm_vendor.so')

    def test_check_inputstream_mpd(self):
        inputstreamhelper.system_os = lambda: 'Linux'
        platform.machine = lambda: 'arm'
        is_helper = inputstreamhelper.Helper('mpd', drm='com.widevine.alpha')
        is_helper.remove_widevine()
        is_installed = is_helper.check_inputstream()
        self.assertTrue(is_installed, True)

    def test_check_inputstream_hls_again(self):
        inputstreamhelper.system_os = lambda: 'Linux'
        platform.machine = lambda: 'arm'
        is_helper = inputstreamhelper.Helper('hls', drm='com.widevine.alpha')
        is_installed = is_helper.check_inputstream()
        self.assertTrue(is_installed, True)

    @staticmethod
    def test_about():
        default.run(['default.py', 'info'])


class WindowsVendorTests(unittest.TestCase):

    def setUp(self):
        with open('test/cdm/widevinecdm_vendor.dll', 'w') as fdesc:
            fdesc.write('Windows\n1.2.3.4')

    def tearDown(self):
        os.unlink('test/cdm/widevinecdm_vendor.dll')

    def test_check_inputstream_hls(self):
        inputstreamhelper.system_os = lambda: 'Windows'
        platform.machine = lambda: 'AMD64'
        platform.architecture = lambda: ['64bit', '']
        is_helper = inputstreamhelper.Helper('hls', drm='com.widevine.alpha')
        is_installed = is_helper.check_inputstream()
        self.assertTrue(is_installed, True)

    def test_check_inputstream_mpd_again(self):
        inputstreamhelper.system_os = lambda: 'Windows'
        platform.machine = lambda: 'AMD64'
        platform.architecture = lambda: ['64bit', '']
        is_helper = inputstreamhelper.Helper('mpd', drm='com.widevine.alpha')
        is_installed = is_helper.check_inputstream()
        self.assertTrue(is_installed, True)

    @staticmethod
    def test_about():
        default.run(['default.py', 'info'])


class DarwinVendorTests(unittest.TestCase):

    def setUp(self):
        with open('test/cdm/libwidevinecdm_vendor.dylib', 'w') as fdesc:
            fdesc.write('macOS\n1.2.3.4')

    def tearDown(self):
        os.unlink('test/cdm/libwidevinecdm_vendor.dylib')

    def test_check_inputstream_mpd(self):
        inputstreamhelper.system_os = lambda: 'Darwin'
        platform.machine = lambda: 'x86_64'
        is_helper = inputstreamhelper.Helper('mpd', drm='com.widevine.alpha')
        is_helper.remove_widevine()
        is_installed = is_helper.check_inputstream()
        self.assertTrue(is_installed, True)

    def test_check_inputstream_hls_again(self):
        inputstreamhelper.system_os = lambda: 'Darwin'
        platform.machine = lambda: 'x86_64'
        is_helper = inputstreamhelper.Helper('hls', drm='com.widevine.alpha')
        is_installed = is_helper.check_inputstream()
        self.assertTrue(is_installed, True)

    @staticmethod
    def test_about():
        default.run(['default.py', 'info'])


if __name__ == '__main__':
    unittest.main()
