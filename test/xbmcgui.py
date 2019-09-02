# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Dag Wieers (@dagwieers) <dag@wieers.com>
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
''' This file implements the Kodi xbmcgui module, either using stubs or alternative functionality '''

from __future__ import absolute_import, division, print_function, unicode_literals
from xbmcextra import kodi_to_ansi

# pylint: disable=unused-argument,too-many-arguments


class Dialog:
    ''' A reimplementation of the xbmcgui Dialog class '''

    def __init__(self):
        ''' A stub constructor for the xbmcgui Dialog class '''

    @staticmethod
    def notification(heading, message, icon=None, time=None, sound=None):
        ''' A working implementation for the xbmcgui Dialog class notification() method '''
        heading = kodi_to_ansi(heading)
        message = kodi_to_ansi(message)
        print('[37;100mNOTIFICATION:[35;0m [%s] [35;0m%s[0m' % (heading, message))

    @staticmethod
    def ok(heading, line1, line2=None, line3=None):
        ''' A stub implementation for the xbmcgui Dialog class ok() method '''
        heading = kodi_to_ansi(heading)
        line1 = kodi_to_ansi(line1)
        print('[37;100mOK:[35;0m [%s] [35;0m%s[0m' % (heading, line1))

    @staticmethod
    def yesno(heading, line1, line2=None, line3=None, nolabel=None, yeslabel=None, autoclose=0):
        ''' A stub implementation for the xbmcgui Dialog class yesno() method '''
        heading = kodi_to_ansi(heading)
        line1 = kodi_to_ansi(line1)
        print('[37;100mYESNO:[35;0m [%s] [35;0m%s[0m' % (heading, line1))
        return True

    @staticmethod
    def textviewer(heading, text=None, usemono=None):
        ''' A stub implementation for the xbmcgui Dialog class textviewer() method '''
        heading = kodi_to_ansi(heading)
        text = kodi_to_ansi(text)
        print('[37;100mTEXTVIEWER:[35;0m [%s] [35;0m%s[0m' % (heading, text))


class DialogProgress:
    ''' A reimplementation of the xbmcgui DialogProgress '''

    def __init__(self):
        ''' A stub constructor for the xbmcgui DialogProgress class '''
        self.percentage = 0

    @staticmethod
    def close():
        ''' A stub implementation for the xbmcgui DialogProgress class close() method '''
        print()

    @staticmethod
    def create(heading, line1, line2=None, line3=None):
        ''' A stub implementation for the xbmcgui DialogProgress class create() method '''
        heading = kodi_to_ansi(heading)
        line1 = kodi_to_ansi(line1)
        print('[37;100mPROGRESS:[35;0m [%s] [35;0m%s[0m' % (heading, line1))

    @staticmethod
    def iscanceled():
        ''' A stub implementation for the xbmcgui DialogProgress class iscanceled() method '''

    def update(self, percentage, line1=None, line2=None, line3=None):
        ''' A stub implementation for the xbmcgui DialogProgress class update() method '''
        if (percentage - 5) < self.percentage:
            return
        self.percentage = percentage
        line1 = kodi_to_ansi(line1)
        line2 = kodi_to_ansi(line2)
        line3 = kodi_to_ansi(line3)
        if line1 or line2 or line3:
            print('[37;100mPROGRESS:[35;0m [%d%%] [35;0m%s[0m' % (percentage, line1 or line2 or line3))
        else:
            print('[1G[37;100mPROGRESS:[35;0m [%d%%]' % (percentage), end='')


class DialogBusy:
    ''' A reimplementation of the xbmcgui DialogBusy '''

    def __init__(self):
        ''' A stub constructor for the xbmcgui DialogBusy class '''

    @staticmethod
    def close():
        ''' A stub implementation for the xbmcgui DialogBusy class close() method '''

    @staticmethod
    def create():
        ''' A stub implementation for the xbmcgui DialogBusy class create() method '''


class ListItem:
    ''' A reimplementation of the xbmcgui ListItem class '''

    def __init__(self, label='', label2='', iconImage='', thumbnailImage='', path='', offscreen=False):
        ''' A stub constructor for the xbmcgui ListItem class '''
        self.label = kodi_to_ansi(label)
        self.label2 = kodi_to_ansi(label2)
        self.path = path

    @staticmethod
    def addContextMenuItems(items, replaceItems=False):
        ''' A stub implementation for the xbmcgui ListItem class addContextMenuItems() method '''
        return

    @staticmethod
    def addStreamInfo(stream_type, stream_values):
        ''' A stub implementation for the xbmcgui LitItem class addStreamInfo() method '''
        return

    @staticmethod
    def setArt(key):
        ''' A stub implementation for the xbmcgui ListItem class setArt() method '''
        return

    @staticmethod
    def setContentLookup(enable):
        ''' A stub implementation for the xbmcgui ListItem class setContentLookup() method '''
        return

    @staticmethod
    def setInfo(type, infoLabels):  # pylint: disable=redefined-builtin
        ''' A stub implementation for the xbmcgui ListItem class setInfo() method '''
        return

    @staticmethod
    def setMimeType(mimetype):
        ''' A stub implementation for the xbmcgui ListItem class setMimeType() method '''
        return

    @staticmethod
    def setProperty(key, value):
        ''' A stub implementation for the xbmcgui ListItem class setProperty() method '''
        return

    @staticmethod
    def setSubtitles(subtitleFiles):
        ''' A stub implementation for the xbmcgui ListItem class setSubtitles() method '''
        return
