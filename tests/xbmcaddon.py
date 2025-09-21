# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Dag Wieers (@dagwieers) <dag@wieers.com>
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""This file implements the Kodi xbmcaddon module, either using stubs or alternative functionality"""

# flake8: noqa: FI14; pylint: disable=invalid-name

from xbmcextra import ADDON_ID, ADDON_INFO, addon_settings


class Addon:
    """A reimplementation of the xbmcaddon Addon class"""

    def __init__(self, id=ADDON_ID):  # pylint: disable=redefined-builtin
        """A stub constructor for the xbmcaddon Addon class"""
        self.id = id
        self.settings = addon_settings(id)

    def getAddonInfo(self, key):
        """A working implementation for the xbmcaddon Addon class getAddonInfo() method"""
        stub_info = {'id': self.id, 'name': self.id, 'version': '2.3.4', 'type': 'kodi.inputstream', 'profile': 'special://userdata', 'path': 'special://userdata'}
        # Add stub_info values to ADDON_INFO when missing (e.g. path and profile)
        addon_info = dict(stub_info, **ADDON_INFO)
        return addon_info.get(self.id, stub_info).get(key)

    @staticmethod
    def getLocalizedString(msgctxt):
        """A working implementation for the xbmcaddon Addon class getLocalizedString() method"""
        from xbmc import getLocalizedString
        return getLocalizedString(msgctxt)

    def getSetting(self, key):
        """A working implementation for the xbmcaddon Addon class getSetting() method"""
        return self.settings.get(key, '')

    def getSettingBool(self, key):
        """A working implementation for the xbmcaddon Addon class getSettingBool() method"""
        try:
            return bool(self.settings.get(key, False))
        except ValueError:
            return None

    def getSettingInt(self, key):
        """A working implementation for the xbmcaddon Addon class getSettingInt() method"""
        try:
            return int(self.settings.get(key, 0))
        except ValueError:
            return 0

    def getSettingNumber(self, key):
        """A working implementation for the xbmcaddon Addon class getSettingNumber() method"""
        try:
            return float(self.settings.get(key, 0.0))
        except ValueError:
            return 0.0

    @staticmethod
    def openSettings():
        """A stub implementation for the xbmcaddon Addon class openSettings() method"""

    def setSetting(self, key, value):
        """A stub implementation for the xbmcaddon Addon class setSetting() method"""
        self.settings[key] = value
        # NOTE: Disable actual writing as it is no longer needed for testing
        # with open('tests/userdata/addon_settings.json', 'w') as fd:
        #     json.dump(filtered_settings, fd, sort_keys=True, indent=4)

    def setSettingBool(self, key, value):
        """A stub implementation for the xbmcaddon Addon class setSettingBool() method"""
        self.settings[key] = value

    def setSettingInt(self, key, value):
        """A stub implementation for the xbmcaddon Addon class setSettingInt() method"""
        self.settings[key] = value

    def setSettingNumber(self, key, value):
        """A stub implementation for the xbmcaddon Addon class setSettingNumber() method"""
        self.settings[key] = value
