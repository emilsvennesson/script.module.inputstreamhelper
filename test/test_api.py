# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring

from __future__ import absolute_import, division, print_function, unicode_literals
import os
import unittest
import addon

xbmc = __import__('xbmc')
xbmcaddon = __import__('xbmcaddon')
xbmcgui = __import__('xbmcgui')
xbmcvfs = __import__('xbmcvfs')


class TestApi(unittest.TestCase):

    @staticmethod
    def test_settings():
        addon.run(['addon.py'])

    @staticmethod
    def test_widevine_install():
        addon.run(['addon.py', 'widevine_install'])

    @staticmethod
    def test_widevine_remove():
        addon.run(['addon.py', 'widevine_remove'])

    @staticmethod
    def test_about():
        addon.run(['addon.py', 'about'])

    @staticmethod
    def test_check_inputstream():
        if os.path.exists('test/cdm/widevine_config.json'):
            os.remove('test/cdm/widevine_config.json')
        addon.run(['addon.py', 'check_inputstream', 'mpd', 'com.widevine.alpha'])
        addon.run(['addon.py', 'check_inputstream', 'hls', 'widevine'])
        addon.run(['addon.py', 'check_inputstream', 'hls'])
        addon.run(['addon.py', 'check_inputstream', 'rtmp'])
        addon.run(['addon.py', 'check_inputstream', 'mpd', 'widevine', 'butter', 'cheese', 'eggs'])


if __name__ == '__main__':
    unittest.main()
