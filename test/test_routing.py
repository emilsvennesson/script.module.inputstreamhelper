# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring

from __future__ import absolute_import, division, print_function, unicode_literals
import unittest
import addon

xbmc = __import__('xbmc')
xbmcaddon = __import__('xbmcaddon')
xbmcgui = __import__('xbmcgui')
xbmcvfs = __import__('xbmcvfs')

plugin = addon.plugin


class TestRouter(unittest.TestCase):

    def test_settings(self):
        # plugin.run(['addon.py', '0', ''])
        plugin.run(['plugin://script.module.inputstreamhelper/', '0', ''])
        plugin.run(['plugin://script.module.inputstreamhelper/settings', '0', ''])
        self.assertEqual(plugin.url_for(addon.settings), 'plugin://script.module.inputstreamhelper/settings')

    def test_widevine_install(self):
        plugin.run(['plugin://script.module.inputstreamhelper/widevine/install', '0', ''])
        plugin.run(['plugin://script.module.inputstreamhelper/widevine/install/latest', '0', ''])
        self.assertEqual(plugin.url_for(addon.widevine_install), 'plugin://script.module.inputstreamhelper/widevine/install/latest')

    def test_widevine_remove(self):
        plugin.run(['plugin://script.module.inputstreamhelper', '0', ''])
        self.assertEqual(plugin.url_for(addon.widevine_remove), 'plugin://script.module.inputstreamhelper/widevine/remove')

    def test_check_inputstream(self):
        plugin.run(['plugin://script.module.inputstreamhelper/check/mpd/widevine', '0', ''])
        self.assertEqual(plugin.url_for(addon.check_inputstream, protocol='mpd', drm='widevine'), 'plugin://script.module.inputstreamhelper/check/mpd/widevine')


if __name__ == '__main__':
    unittest.main()
