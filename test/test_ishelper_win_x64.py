# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring,protected-access

from __future__ import absolute_import, division, print_function, unicode_literals
import unittest
import inputstreamhelper

xbmc = __import__('xbmc')
xbmcaddon = __import__('xbmcaddon')
xbmcgui = __import__('xbmcgui')
xbmcvfs = __import__('xbmcvfs')


class WindowsX64Tests(unittest.TestCase):
    inputstreamhelper.system_os = lambda: 'Windows'

    def test_check_inputstream_mpd(self):
        is_helper = inputstreamhelper.Helper('mpd', drm='com.widevine.alpha')
        is_helper._arch = lambda: 'x86_64'
        is_helper.remove_widevine()
        is_installed = is_helper.check_inputstream()
        self.assertTrue(is_installed, True)

    def test_check_inputstream_mpd_again(self):
        is_helper = inputstreamhelper.Helper('mpd', drm='com.widevine.alpha')
        is_helper._arch = lambda: 'x86_64'
        is_installed = is_helper.check_inputstream()
        self.assertTrue(is_installed, True)

    def test_check_inputstream_rtmp(self):
        is_helper = inputstreamhelper.Helper('rtmp', drm='com.widevine.alpha')
        is_helper._arch = lambda: 'x86_64'
        is_installed = is_helper.check_inputstream()
        self.assertTrue(is_installed, True)


if __name__ == '__main__':
    unittest.main()
