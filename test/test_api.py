# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring

from __future__ import absolute_import, division, print_function, unicode_literals
import os
import unittest
import default

xbmc = __import__('xbmc')
xbmcaddon = __import__('xbmcaddon')
xbmcgui = __import__('xbmcgui')
xbmcvfs = __import__('xbmcvfs')


class TestApi(unittest.TestCase):

    @staticmethod
    def test_settings():
        default.run(['default.py'])

    @staticmethod
    def test_widevine_install():
        default.run(['default.py', 'widevine_install'])

    @staticmethod
    def test_widevine_remove():
        default.run(['default.py', 'widevine_remove'])

    @staticmethod
    def test_about():
        default.run(['default.py', 'info'])

    @staticmethod
    def test_check_inputstream():
        if os.path.exists('test/cdm/widevine_config.json'):
            os.remove('test/cdm/widevine_config.json')
        default.run(['default.py', 'check_inputstream', 'mpd', 'com.widevine.alpha'])
        default.run(['default.py', 'check_inputstream', 'hls', 'widevine'])
        default.run(['default.py', 'check_inputstream', 'hls'])
        default.run(['default.py', 'check_inputstream', 'rtmp'])
        default.run(['default.py', 'check_inputstream', 'mpd', 'widevine', 'butter', 'cheese', 'eggs'])


if __name__ == '__main__':
    unittest.main()
