# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Dag Wieers (@dagwieers) <dag@wieers.com>
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Extra functions for testing"""

# pylint: disable=invalid-name

from __future__ import absolute_import, division, print_function, unicode_literals
import os
import xml.etree.ElementTree as ET
import polib


def kodi_to_ansi(string):
    """Convert Kodi format tags to ANSI codes"""
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
    string = string.replace('[COLOR cyan]', '\033[36m')
    string = string.replace('[COLOR white]', '\033[37m')
    string = string.replace('[/COLOR]', '\033[39;0m')
    return string


def uri_to_path(uri):
    """Shorten a plugin URI to just the path"""
    if uri is None:
        return None
    return ' \033[33m→ \033[34m%s\033[39;0m' % uri.replace('plugin://' + ADDON_ID, '')


def read_addon_xml(path):
    """Parse the addon.xml and return an info dictionary"""
    info = dict(
        path='./',  # '/storage/.kodi/addons/plugin.video.vrt.nu',
        profile='special://userdata',  # 'special://profile/addon_data/plugin.video.vrt.nu/',
        type='xbmc.python.pluginsource',
    )

    tree = ET.parse(path)
    root = tree.getroot()

    info.update(root.attrib)  # Add 'id', 'name' and 'version'
    info['author'] = info.pop('provider-name')

    for child in root:
        if child.attrib.get('point') != 'xbmc.addon.metadata':
            continue
        for grandchild in child:
            # Handle assets differently
            if grandchild.tag == 'assets':
                for asset in grandchild:
                    info[asset.tag] = asset.text
                continue
            # Not in English ?  Drop it
            if grandchild.attrib.get('lang', 'en_GB') != 'en_GB':
                continue
            # Add metadata
            info[grandchild.tag] = grandchild.text

    return {info['name']: info}


def global_settings():
    """Use the global_settings file"""
    import json
    try:
        with open('tests/userdata/global_settings.json') as f:  # pylint: disable=unspecified-encoding
            settings = json.load(f)
    except OSError as e:
        print("Error: Cannot use 'tests/userdata/global_settings.json' : %s" % e)
        settings = {
            'locale.language': 'resource.language.en_gb',
            'network.bandwidth': 0,
        }

    if 'PROXY_SERVER' in os.environ:
        settings['network.usehttpproxy'] = True
        settings['network.httpproxytype'] = 0
        print('Using proxy server from environment variable PROXY_SERVER')
        settings['network.httpproxyserver'] = os.environ.get('PROXY_SERVER')
        if 'PROXY_PORT' in os.environ:
            print('Using proxy server from environment variable PROXY_PORT')
            settings['network.httpproxyport'] = os.environ.get('PROXY_PORT')
        if 'PROXY_USERNAME' in os.environ:
            print('Using proxy server from environment variable PROXY_USERNAME')
            settings['network.httpproxyusername'] = os.environ.get('PROXY_USERNAME')
        if 'PROXY_PASSWORD' in os.environ:
            print('Using proxy server from environment variable PROXY_PASSWORD')
            settings['network.httpproxypassword'] = os.environ.get('PROXY_PASSWORD')
    return settings


def addon_settings(addon_id=None):
    """Use the addon_settings file"""
    import json
    try:
        with open('tests/userdata/addon_settings.json') as f:  # pylint: disable=unspecified-encoding
            settings = json.load(f)
    except OSError as e:
        print("Error: Cannot use 'tests/userdata/addon_settings.json' : %s" % e)
        settings = {}

    if addon_id:
        return settings[addon_id]

    return settings


def import_language(language):
    """Process the language.po file"""
    try:
        podb = polib.pofile('resources/language/{language}/strings.po'.format(language=language))
    except IOError:
        podb = polib.pofile('resources/language/resource.language.en_gb/strings.po')

    podb.extend([
        # WEEKDAY_LONG
        polib.POEntry(msgctxt='#11', msgstr='Monday'),
        polib.POEntry(msgctxt='#12', msgstr='Tuesday'),
        polib.POEntry(msgctxt='#13', msgstr='Wednesday'),
        polib.POEntry(msgctxt='#14', msgstr='Thursday'),
        polib.POEntry(msgctxt='#15', msgstr='Friday'),
        polib.POEntry(msgctxt='#16', msgstr='Saturday'),
        polib.POEntry(msgctxt='#17', msgstr='Sunday'),
        # MONTH_LONG
        polib.POEntry(msgctxt='#21', msgstr='January'),
        polib.POEntry(msgctxt='#22', msgstr='February'),
        polib.POEntry(msgctxt='#23', msgstr='March'),
        polib.POEntry(msgctxt='#24', msgstr='April'),
        polib.POEntry(msgctxt='#25', msgstr='May'),
        polib.POEntry(msgctxt='#26', msgstr='June'),
        polib.POEntry(msgctxt='#27', msgstr='July'),
        polib.POEntry(msgctxt='#28', msgstr='August'),
        polib.POEntry(msgctxt='#29', msgstr='September'),
        polib.POEntry(msgctxt='#30', msgstr='October'),
        polib.POEntry(msgctxt='#31', msgstr='November'),
        polib.POEntry(msgctxt='#32', msgstr='December'),
        # WEEKDAY_SHORT
        polib.POEntry(msgctxt='#41', msgstr='Mon'),
        polib.POEntry(msgctxt='#42', msgstr='Tue'),
        polib.POEntry(msgctxt='#43', msgstr='Wed'),
        polib.POEntry(msgctxt='#44', msgstr='Thu'),
        polib.POEntry(msgctxt='#45', msgstr='Fri'),
        polib.POEntry(msgctxt='#46', msgstr='Sat'),
        polib.POEntry(msgctxt='#47', msgstr='Sun'),
        # MONTH_LONG
        polib.POEntry(msgctxt='#51', msgstr='Jan'),
        polib.POEntry(msgctxt='#52', msgstr='Feb'),
        polib.POEntry(msgctxt='#53', msgstr='Mar'),
        polib.POEntry(msgctxt='#54', msgstr='Apr'),
        polib.POEntry(msgctxt='#55', msgstr='May'),
        polib.POEntry(msgctxt='#56', msgstr='Jun'),
        polib.POEntry(msgctxt='#57', msgstr='Jul'),
        polib.POEntry(msgctxt='#58', msgstr='Aug'),
        polib.POEntry(msgctxt='#59', msgstr='Sep'),
        polib.POEntry(msgctxt='#50', msgstr='Oct'),
        polib.POEntry(msgctxt='#51', msgstr='Nov'),
        polib.POEntry(msgctxt='#52', msgstr='Dec'),
    ])

    return podb


ADDON_INFO = read_addon_xml('addon.xml')
ADDON_ID = next(iter(list(ADDON_INFO.values()))).get('id')
GLOBAL_SETTINGS = global_settings()
LANGUAGE = import_language(language=GLOBAL_SETTINGS.get('locale.language'))
