# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Dag Wieers (@dagwieers) <dag@wieers.com>
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
''' Extra functions for testing '''

from __future__ import absolute_import, division, print_function, unicode_literals


def kodi_to_ansi(string):
    ''' Convert Kodi format tags to ANSI codes '''
    if string is None:
        return None
    string = string.replace('[B]', '\033[1m')
    string = string.replace('[/B]', '\033[21m')
    string = string.replace('[I]', '\033[3m')
    string = string.replace('[/I]', '\033[23m')
    string = string.replace('[COLOR gray]', '\033[30;1m')
    string = string.replace('[COLOR red]', '\033[31m')
    string = string.replace('[COLOR green]', '\033[32m')
    string = string.replace('[COLOR yellow]', '\033[33m')
    string = string.replace('[COLOR blue]', '\033[34m')
    string = string.replace('[COLOR purple]', '\033[35m')
    string = string.replace('[/COLOR]', '\033[39;0m')
    return string
