# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Dag Wieers (@dagwieers) <dag@wieers.com>
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""This file implements the Kodi xbmcgui module, either using stubs or alternative functionality"""

# pylint: disable=invalid-name,super-on-old-class,too-few-public-methods,too-many-arguments,unused-argument,useless-super-delegation

from __future__ import absolute_import, division, print_function, unicode_literals
import sys
from xbmcextra import kodi_to_ansi


class Control:
    """A reimplementation of the xbmcgui Control class"""

    def __init__(self):
        """A stub constructor for the xbmcgui Control class"""

    @staticmethod
    def selectItem(index):
        """A stub implementation for the xbmcgui Control class selectItem() method"""


class ControlLabel(Control):
    """A reimplementation of the xbmcgui ControlLabel class"""

    def __init__(self):  # pylint: disable=super-init-not-called
        """A stub constructor for the xbmcgui ControlLabel class"""

    @staticmethod
    def getLabel():
        """A stub implementation for the xbmcgui ControlLabel class getLabel() method"""
        return 'Label'

    @staticmethod
    def setLabel(label='', font=None, textColor=None, disabledColor=None, shadowColor=None, focusedColor=None, label2=''):
        """A stub implementation for the xbmcgui ControlLabel class getLabel() method"""


class Dialog:
    """A reimplementation of the xbmcgui Dialog class"""

    def __init__(self):
        """A stub constructor for the xbmcgui Dialog class"""

    @staticmethod
    def notification(heading, message, icon=None, time=None, sound=None):
        """A working implementation for the xbmcgui Dialog class notification() method"""
        heading = kodi_to_ansi(heading)
        message = kodi_to_ansi(message)
        print('\033[37;44;1mNOTIFICATION:\033[35;49;1m [%s] \033[37;1m%s\033[39;0m' % (heading, message))

    @staticmethod
    def ok(heading, line1, line2=None, line3=None):
        """A stub implementation for the xbmcgui Dialog class ok() method"""
        heading = kodi_to_ansi(heading)
        line1 = kodi_to_ansi(line1)
        print('\033[37;44;1mOK:\033[35;49;1m [%s] \033[37;1m%s\033[39;0m' % (heading, line1))

    @staticmethod
    def info(listitem):
        """A stub implementation for the xbmcgui Dialog class info() method"""

    @staticmethod
    def select(heading, opt_list, autoclose=0, preselect=None, useDetails=False):
        """A stub implementation for the xbmcgui Dialog class select() method"""
        if preselect is None:
            preselect = []
        heading = kodi_to_ansi(heading)
        print('\033[37;44;1mSELECT:\033[35;49;1m [%s] \033[37;1m%s\033[39;0m' % (heading, ', '.join(opt_list)))
        return -1

    @staticmethod
    def multiselect(heading, options, autoclose=0, preselect=None, useDetails=False):  # pylint: disable=useless-return
        """A stub implementation for the xbmcgui Dialog class multiselect() method"""
        if preselect is None:
            preselect = []
        heading = kodi_to_ansi(heading)
        print('\033[37;44;1mMULTISELECT:\033[35;49;1m [%s] \033[37;1m%s\033[39;0m' % (heading, ', '.join(options)))
        return None

    @staticmethod
    def contextmenu(items):
        """A stub implementation for the xbmcgui Dialog class contextmenu() method"""
        print('\033[37;44;1mCONTEXTMENU:\033[35;49;1m \033[37;1m%s\033[39;0m' % (', '.join(items)))
        return -1

    @staticmethod
    def yesno(heading, line1, line2=None, line3=None, nolabel=None, yeslabel=None, autoclose=0):
        """A stub implementation for the xbmcgui Dialog class yesno() method"""
        heading = kodi_to_ansi(heading)
        line1 = kodi_to_ansi(line1)
        print('\033[37;44;1mYESNO:\033[35;49;1m [%s] \033[37;1m%s\033[39;0m' % (heading, line1))
        return True

    @staticmethod
    def textviewer(heading, text=None, usemono=None):
        """A stub implementation for the xbmcgui Dialog class textviewer() method"""
        heading = kodi_to_ansi(heading)
        text = kodi_to_ansi(text)
        print('\033[37;44;1mTEXTVIEWER:\033[35;49;1m [%s]\n\033[37;1m%s\033[39;0m' % (heading, text))

    @staticmethod
    def browseSingle(type, heading, shares, mask=None, useThumbs=None, treatAsFolder=None, defaultt=None):  # pylint: disable=redefined-builtin
        """A stub implementation for the xbmcgui Dialog class browseSingle() method"""
        print('\033[37;44;1mBROWSESINGLE:\033[35;49;1m [%s] \033[37;1m%s\033[39;0m' % (type, heading))
        return 'special://masterprofile/addon_data/script.module.inputstreamhelper/'


class DialogProgress:
    """A reimplementation of the xbmcgui DialogProgress"""

    def __init__(self):
        """A stub constructor for the xbmcgui DialogProgress class"""
        self.percentage = 0

    def close(self):
        """A stub implementation for the xbmcgui DialogProgress class close() method"""
        self.percentage = 0
        print()
        sys.stdout.flush()

    def create(self, heading, line1, line2=None, line3=None):
        """A stub implementation for the xbmcgui DialogProgress class create() method"""
        self.percentage = 0
        heading = kodi_to_ansi(heading)
        line1 = kodi_to_ansi(line1)
        print('\033[37;44;1mPROGRESS:\033[35;49;1m [%s] \033[37;1m%s\033[39;0m' % (heading, line1))
        sys.stdout.flush()

    @staticmethod
    def iscanceled():
        """A stub implementation for the xbmcgui DialogProgress class iscanceled() method"""

    def update(self, percentage, line1=None, line2=None, line3=None):
        """A stub implementation for the xbmcgui DialogProgress class update() method"""
        if (percentage - 5) < self.percentage:
            return
        self.percentage = percentage
        line1 = kodi_to_ansi(line1)
        line2 = kodi_to_ansi(line2)
        line3 = kodi_to_ansi(line3)
        if line1 or line2 or line3:
            print('\033[1G\033[37;44;1mPROGRESS:\033[35;49;1m [%d%%] \033[37;1m%s\033[39;0m' % (percentage, line1 or line2 or line3), end='')
        else:
            print('\033[1G\033[37;44;1mPROGRESS:\033[35;49;1m [%d%%]\033[39;0m' % (percentage), end='')
        sys.stdout.flush()


class DialogProgressBG:
    """A reimplementation of the xbmcgui DialogProgressBG"""

    def __init__(self):
        """A stub constructor for the xbmcgui DialogProgressBG class"""
        self.percentage = 0

    @staticmethod
    def close():
        """A stub implementation for the xbmcgui DialogProgressBG class close() method"""
        print()

    @staticmethod
    def create(heading, message):
        """A stub implementation for the xbmcgui DialogProgressBG class create() method"""
        heading = kodi_to_ansi(heading)
        message = kodi_to_ansi(message)
        print('\033[37;44;1mPROGRESS:\033[35;49;1m [%s] \033[37;1m%s\033[39;0m' % (heading, message))

    @staticmethod
    def isfinished():
        """A stub implementation for the xbmcgui DialogProgressBG class isfinished() method"""

    def update(self, percentage, heading=None, message=None):
        """A stub implementation for the xbmcgui DialogProgressBG class update() method"""
        if (percentage - 5) < self.percentage:
            return
        self.percentage = percentage
        message = kodi_to_ansi(message)
        if message:
            print('\033[37;44;1mPROGRESS:\033[35;49;1m [%d%%] \033[37;1m%s\033[39;0m' % (percentage, message))
        else:
            print('\033[1G\033[37;44;1mPROGRESS:\033[35;49;1m [%d%%]\033[39;0m' % (percentage), end='')


class DialogBusy:
    """A reimplementation of the xbmcgui DialogBusy"""

    def __init__(self):
        """A stub constructor for the xbmcgui DialogBusy class"""

    @staticmethod
    def close():
        """A stub implementation for the xbmcgui DialogBusy class close() method"""

    @staticmethod
    def create():
        """A stub implementation for the xbmcgui DialogBusy class create() method"""


class ListItem:
    """A reimplementation of the xbmcgui ListItem class"""

    def __init__(self, label='', label2='', iconImage='', thumbnailImage='', path='', offscreen=False):
        """A stub constructor for the xbmcgui ListItem class"""
        self.label = kodi_to_ansi(label)
        self.label2 = kodi_to_ansi(label2)
        self.path = path

    @staticmethod
    def addContextMenuItems(items, replaceItems=False):
        """A stub implementation for the xbmcgui ListItem class addContextMenuItems() method"""

    @staticmethod
    def addStreamInfo(stream_type, stream_values):
        """A stub implementation for the xbmcgui LitItem class addStreamInfo() method"""

    @staticmethod
    def setArt(key):
        """A stub implementation for the xbmcgui ListItem class setArt() method"""

    @staticmethod
    def setContentLookup(enable):
        """A stub implementation for the xbmcgui ListItem class setContentLookup() method"""

    @staticmethod
    def setInfo(type, infoLabels):  # pylint: disable=redefined-builtin
        """A stub implementation for the xbmcgui ListItem class setInfo() method"""

    @staticmethod
    def setIsFolder(isFolder):
        """A stub implementation for the xbmcgui ListItem class setIsFolder() method"""

    @staticmethod
    def setLabel2(label):
        """A stub implementation for the xbmcgui ListItem class setLabel2() method"""

    @staticmethod
    def setMimeType(mimetype):
        """A stub implementation for the xbmcgui ListItem class setMimeType() method"""

    def setPath(self, path):
        """A stub implementation for the xbmcgui ListItem class setPath() method"""
        self.path = path

    @staticmethod
    def setProperty(key, value):
        """A stub implementation for the xbmcgui ListItem class setProperty() method"""

    @staticmethod
    def setProperties(dictionary):
        """A stub implementation for the xbmcgui ListItem class setProperties() method"""

    @staticmethod
    def setSubtitles(subtitleFiles):
        """A stub implementation for the xbmcgui ListItem class setSubtitles() method"""

    @staticmethod
    def setUniqueIDs(values, defaultrating=None):
        """A stub implementation for the xbmcgui ListItem class setUniqueIDs() method"""


class Window:
    """A reimplementation of the xbmcgui Window"""

    def __init__(self, windowId):
        """A stub constructor for the xbmcgui Window class"""

    def close(self):
        """A stub implementation for the xbmcgui Window class close() method"""

    @staticmethod
    def getControl():
        """A stub implementation for the xbmcgui Window class getControl() method"""
        return ControlLabel()

    @staticmethod
    def getFocusId():
        """A stub implementation for the xbmcgui Window class getFocusId() method"""
        return 0

    @staticmethod
    def getProperty(key):
        """A stub implementation for the xbmcgui Window class getProperty() method"""
        return ''

    @staticmethod
    def setProperty(key, value):
        """A stub implementation for the xbmcgui Window class setProperty() method"""

    @staticmethod
    def clearProperty(key):
        """A stub implementation for the xbmcgui Window class clearProperty() method"""

    def show(self):
        """A stub implementation for the xbmcgui Window class show() method"""


class WindowXML(Window):
    """A reimplementation of the xbmcgui WindowXML"""

    def __init__(self):
        """A stub constructor for the xbmcgui WindowXML class"""
        super(WindowXML, self).__init__()


class WindowXMLDialog(WindowXML):
    """A reimplementation of the xbmcgui WindowXMLDialog"""

    def __init__(self):
        """A stub constructor for the xbmcgui WindowXMLDialog class"""
        super(WindowXMLDialog, self).__init__()


def getCurrentWindowId():
    """A stub implementation of the xbmcgui getCurrentWindowId() method"""
    return 0
