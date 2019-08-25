# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Dag Wieers (@dagwieers) <dag@wieers.com>
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
''' This file implements the Kodi xbmc module, either using stubs or alternative functionality '''

from __future__ import absolute_import, division, print_function, unicode_literals

import sys
import os
import json
import polib


LOGDEBUG = 'Debug'
LOGERROR = 'Error'
LOGNOTICE = 'Notice'

INFO_LABELS = {
    'System.BuildVersion': '18.2',
}

PO = polib.pofile('resources/language/resource.language.en_gb/strings.po')

# Use the global_settings file
try:
    with open('test/userdata/global_settings.json') as f:
        GLOBAL_SETTINGS = json.load(f)
except OSError as e:
    print("Error using 'test/userdata/global_settings.json' : %s" % e, file=sys.stderr)
    GLOBAL_SETTINGS = {
        'locale.language': 'resource.language.en_gb',
        'network.bandwidth': 0,
    }


def executebuiltin(function, wait=False):  # pylint: disable=unused-argument
    ''' A stub implementation of the xbmc executebuiltin() function '''
    return


def executeJSONRPC(jsonrpccommand):
    ''' A reimplementation of the xbmc executeJSONRPC() function '''
    command = json.loads(jsonrpccommand)
    if command.get('method') == 'Settings.GetSettingValue':
        key = command.get('params').get('setting')
        return '{"id":1,"jsonrpc":"2.0","result":{"value":"%s"}}' % GLOBAL_SETTINGS.get(key)
    if command.get('method') == 'Addons.GetAddonDetails':
        if command.get('params', {}).get('addonid') == 'script.module.inputstreamhelper':
            return '{"id":1,"jsonrpc":"2.0","result":{"addon":{"enabled": "true", "version": "0.3.5"}}}'
        return '{"id":1,"jsonrpc":"2.0","result":{"addon":{"enabled": "true", "version": "1.2.3"}}}'
    return '{"error":{"code":-1,"message":"Not implemented."},"id":1,"jsonrpc":"2.0"}'


def getCondVisibility(string):  # pylint: disable=unused-argument
    ''' A reimplementation of the xbmc getCondVisibility() function '''
    if string == 'system.platform.android':
        return False
    return True


def getInfoLabel(key):
    ''' A reimplementation of the xbmc getInfoLabel() function '''
    return INFO_LABELS.get(key)


def log(msg, level):
    ''' A reimplementation of the xbmc log() function '''
    print('[32;1m%s: [32;0m%s[0m' % (level, msg))


def translatePath(path):
    ''' A stub implementation of the xbmc translatePath() function '''
    if path.startswith('special://home'):
        return path.replace('special://home', os.path.join(os.getcwd(), 'test'))
    if path.startswith('special://profile'):
        return path.replace('special://profile', os.path.join(os.getcwd(), 'test/usedata'))
    if path.startswith('special://userdata'):
        return path.replace('special://userdata', os.path.join(os.getcwd(), 'test/userdata'))
    return path
