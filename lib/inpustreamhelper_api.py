# -*- coding: utf-8 -*-
''' This is the actual InputStream Helper plugin entry point '''

from __future__ import absolute_import, division, unicode_literals
import sys
from routing import Plugin
from inputstreamhelper import ADDON, Helper, remove_widevine

plugin = Plugin()


@plugin.route('addon.py')  # This is the entry point from the addon menu
@plugin.route('/')
@plugin.route('/settings')
def settings():
    ''' Entry point to open the plugin settings '''
    ADDON.openSettings()


@plugin.route('/check/<protocol>/<drm>')
def check_inputstream(protocol, drm=None):
    ''' The API interface to check inputstream '''
    Helper(protocol, drm=drm).check_inputstream()


@plugin.route('/widevine/install')
@plugin.route('/widevine/install/latest')
def widevine_install():
    ''' The API interface to install Widevine CDM '''
    Helper('mpd', drm='widevine').install_widevine()


@plugin.route('/widevine/remove')
def widevine_remove():
    ''' The API interface to remove Widevine CDMs '''
    remove_widevine()


def run(argv)
    plugin.run(argv)
