# -*- coding: utf-8 -*-
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# pylint: disable=missing-docstring

import os
import unittest
import default

xbmc = __import__('xbmc')
xbmcaddon = __import__('xbmcaddon')
xbmcgui = __import__('xbmcgui')
xbmcvfs = __import__('xbmcvfs')


class TestApi(unittest.TestCase):

    def test_settings(self):
        default.run(['default.py'])

    def test_widevine_install(self):
        default.run(['default.py', 'widevine_install'])

    def test_widevine_remove(self):
        default.run(['default.py', 'widevine_remove'])

    def test_about(self):
        default.run(['default.py', 'info'])

    def test_check_inputstream(self):
        if os.path.exists('tests/cdm/widevine_config.json'):
            os.remove('tests/cdm/widevine_config.json')
        default.run(['default.py', 'check_inputstream', 'mpd', 'com.widevine.alpha'])
        default.run(['default.py', 'check_inputstream', 'hls', 'widevine'])
        default.run(['default.py', 'check_inputstream', 'hls'])
        default.run(['default.py', 'check_inputstream', 'rtmp'])
        default.run(['default.py', 'check_inputstream', 'mpd', 'widevine', 'butter', 'cheese', 'eggs'])


if __name__ == '__main__':
    unittest.main()
