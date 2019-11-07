# -*- coding: utf-8 -*-
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

''' Implements Kodi Helper functions '''
from __future__ import absolute_import, division, unicode_literals
import xbmc
from xbmcaddon import Addon
from .unicodehelper import from_unicode, to_unicode

ADDON = Addon('script.module.inputstreamhelper')


class SafeDict(dict):
    ''' A safe dictionary implementation that does not break down on missing keys '''
    def __missing__(self, key):
        ''' Replace missing keys with the original placeholder '''
        return '{' + key + '}'


def has_socks():
    ''' Test if socks is installed, and remember this information '''

    # If it wasn't stored before, check if socks is installed
    if not hasattr(has_socks, 'installed'):
        try:
            import socks  # noqa: F401; pylint: disable=unused-variable,unused-import
            has_socks.installed = True
        except ImportError:
            has_socks.installed = False
            return None  # Detect if this is the first run

    # Return the stored value
    return has_socks.installed


def browsesingle(type, heading, shares='', mask='', useThumbs=False, treatAsFolder=False, defaultt=None):  # pylint: disable=invalid-name,redefined-builtin
    ''' Show a Kodi browseSingle dialog '''
    from xbmcgui import Dialog
    if not heading:
        heading = ADDON.getAddonInfo('name')
    return Dialog().browseSingle(type=type, heading=heading, shares=shares, mask=mask, useThumbs=useThumbs, treatAsFolder=treatAsFolder, defaultt=defaultt)


def notification(heading='', message='', icon='info', time=4000):
    ''' Show a Kodi notification '''
    from xbmcgui import Dialog
    if not heading:
        heading = ADDON.getAddonInfo('name')
    return Dialog().notification(heading=heading, message=message, icon=icon, time=time)


def ok_dialog(heading='', message=''):
    ''' Show Kodi's OK dialog '''
    from xbmcgui import Dialog
    if not heading:
        heading = ADDON.getAddonInfo('name')
    return Dialog().ok(heading=heading, line1=message)


def select_dialog(heading='', opt_list=None, autoclose=False, preselect=None, useDetails=False):  # pylint: disable=invalid-name
    ''' Show Kodi's Select dialog '''
    from xbmcgui import Dialog
    if not heading:
        heading = ADDON.getAddonInfo('name')
    return Dialog().select(heading=heading, opt_list=opt_list, autoclose=autoclose, preselect=preselect, useDetails=useDetails)


def progress_dialog():
    ''' Show Kodi's Progress dialog '''
    from xbmcgui import DialogProgress
    return DialogProgress()


def textviewer(heading='', text='', usemono=False):
    ''' Show a Kodi textviewer dialog '''
    from xbmcgui import Dialog
    if not heading:
        heading = ADDON.getAddonInfo('name')
    return Dialog().textviewer(heading=heading, text=text, usemono=usemono)


def yesno_dialog(heading='', message='', nolabel=None, yeslabel=None, autoclose=0):
    ''' Show Kodi's Yes/No dialog '''
    from xbmcgui import Dialog
    if not heading:
        heading = ADDON.getAddonInfo('name')
    return Dialog().yesno(heading=heading, line1=message, nolabel=nolabel, yeslabel=yeslabel, autoclose=autoclose)


def localize(string_id, **kwargs):
    ''' Return the translated string from the .po language files, optionally translating variables '''
    if kwargs:
        import string
        return string.Formatter().vformat(ADDON.getLocalizedString(string_id), (), SafeDict(**kwargs))

    return ADDON.getLocalizedString(string_id)


def get_setting(setting_id, default=None):
    ''' Get an add-on setting '''
    value = to_unicode(ADDON.getSetting(setting_id))
    if value == '' and default is not None:
        return default
    return value


def translate_path(path):
    ''' Translate special xbmc paths '''
    return to_unicode(xbmc.translatePath(path))


def set_setting(setting_id, setting_value):
    ''' Set an add-on setting '''
    return ADDON.setSetting(setting_id, setting_value)


def get_global_setting(setting):
    ''' Get a Kodi setting '''
    result = execute_jsonrpc(dict(jsonrpc='2.0', id=1, method='Settings.GetSettingValue', params=dict(setting='%s' % setting)))
    return result.get('result', dict()).get('value')


def get_proxies():
    ''' Return a usable proxies dictionary from Kodi proxy settings '''
    usehttpproxy = get_global_setting('network.usehttpproxy')
    if usehttpproxy is not True:
        return None

    try:
        httpproxytype = int(get_global_setting('network.httpproxytype'))
    except ValueError:
        httpproxytype = 0

    socks_supported = has_socks()
    if httpproxytype != 0 and not socks_supported:
        # Only open the dialog the first time (to avoid multiple popups)
        if socks_supported is None:
            ok_dialog('', localize(30042))  # Requires PySocks
        return None

    proxy_types = ['http', 'socks4', 'socks4a', 'socks5', 'socks5h']
    if 0 <= httpproxytype < 5:
        httpproxyscheme = proxy_types[httpproxytype]
    else:
        httpproxyscheme = 'http'

    httpproxyserver = get_global_setting('network.httpproxyserver')
    httpproxyport = get_global_setting('network.httpproxyport')
    httpproxyusername = get_global_setting('network.httpproxyusername')
    httpproxypassword = get_global_setting('network.httpproxypassword')

    if httpproxyserver and httpproxyport and httpproxyusername and httpproxypassword:
        proxy_address = '%s://%s:%s@%s:%s' % (httpproxyscheme, httpproxyusername, httpproxypassword, httpproxyserver, httpproxyport)
    elif httpproxyserver and httpproxyport and httpproxyusername:
        proxy_address = '%s://%s@%s:%s' % (httpproxyscheme, httpproxyusername, httpproxyserver, httpproxyport)
    elif httpproxyserver and httpproxyport:
        proxy_address = '%s://%s:%s' % (httpproxyscheme, httpproxyserver, httpproxyport)
    elif httpproxyserver:
        proxy_address = '%s://%s' % (httpproxyscheme, httpproxyserver)
    else:
        return None

    return dict(http=proxy_address, https=proxy_address)


def get_userdata_path():
    ''' Return the addon's addon_data path '''
    return translate_path(ADDON.getAddonInfo('profile'))


def get_addon_info(key):
    ''' Return addon information '''
    return to_unicode(ADDON.getAddonInfo(key))


def execute_jsonrpc(payload):
    ''' Kodi JSON-RPC request. Return the response in a dictionary. '''
    import json
    log('jsonrpc payload: {payload}', payload=payload)
    response = xbmc.executeJSONRPC(json.dumps(payload))
    log('jsonrpc response: {response}', response=response)
    return json.loads(response)


def log(msg, level=xbmc.LOGDEBUG, **kwargs):
    ''' InputStream Helper log method '''
    xbmc.log(msg=from_unicode('[{addon}]: {msg}'.format(addon=get_addon_info('id'), msg=msg.format(**kwargs))), level=level)


def kodi_to_ascii(string):
    ''' Convert Kodi format tags to ascii '''
    if string is None:
        return None
    string = string.replace('[B]', '')
    string = string.replace('[/B]', '')
    string = string.replace('[I]', '')
    string = string.replace('[/I]', '')
    string = string.replace('[COLOR gray]', '')
    string = string.replace('[COLOR yellow]', '')
    string = string.replace('[/COLOR]', '')
    return string
