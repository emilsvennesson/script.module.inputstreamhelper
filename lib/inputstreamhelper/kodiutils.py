# -*- coding: utf-8 -*-
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Implements Kodi Helper functions"""
from __future__ import absolute_import, division, unicode_literals
import xbmc
from xbmcaddon import Addon
from .unicodehelper import from_unicode, to_unicode

ADDON = Addon('script.module.inputstreamhelper')


class SafeDict(dict):
    """A safe dictionary implementation that does not break down on missing keys"""
    def __missing__(self, key):
        """Replace missing keys with the original placeholder"""
        return '{' + key + '}'


def addon_id():
    """Return add-on ID"""
    return get_addon_info('id')


def addon_profile():
    """Cache and return add-on profile"""
    return to_unicode(xbmc.translatePath(ADDON.getAddonInfo('profile')))


def has_socks():
    """Test if socks is installed, and use a static variable to remember"""
    if hasattr(has_socks, 'cached'):
        return getattr(has_socks, 'cached')
    try:
        import socks  # noqa: F401; pylint: disable=unused-variable,unused-import,useless-suppression
    except ImportError:
        has_socks.cached = False
        return None  # Detect if this is the first run
    has_socks.cached = True
    return True


def browsesingle(type, heading, shares='', mask='', useThumbs=False, treatAsFolder=False, defaultt=None):  # pylint: disable=invalid-name,redefined-builtin
    """Show a Kodi browseSingle dialog"""
    from xbmcgui import Dialog
    if not heading:
        heading = ADDON.getAddonInfo('name')
    return Dialog().browseSingle(type=type, heading=heading, shares=shares, mask=mask, useThumbs=useThumbs, treatAsFolder=treatAsFolder, defaultt=defaultt)


def notification(heading='', message='', icon='info', time=4000):
    """Show a Kodi notification"""
    from xbmcgui import Dialog
    if not heading:
        heading = ADDON.getAddonInfo('name')
    return Dialog().notification(heading=heading, message=message, icon=icon, time=time)


def ok_dialog(heading='', message=''):
    """Show Kodi's OK dialog"""
    from xbmcgui import Dialog
    if not heading:
        heading = ADDON.getAddonInfo('name')
    return Dialog().ok(heading=heading, line1=message)


def select_dialog(heading='', opt_list=None, autoclose=False, preselect=None, useDetails=False):  # pylint: disable=invalid-name
    """Show Kodi's Select dialog"""
    from xbmcgui import Dialog
    if not heading:
        heading = ADDON.getAddonInfo('name')
    return Dialog().select(heading=heading, opt_list=opt_list, autoclose=autoclose, preselect=preselect, useDetails=useDetails)


def progress_dialog():
    """Show Kodi's Progress dialog"""
    from xbmcgui import DialogProgress
    return DialogProgress()


def textviewer(heading='', text='', usemono=False):
    """Show a Kodi textviewer dialog"""
    from xbmcgui import Dialog
    if not heading:
        heading = ADDON.getAddonInfo('name')
    return Dialog().textviewer(heading=heading, text=text, usemono=usemono)


def yesno_dialog(heading='', message='', nolabel=None, yeslabel=None, autoclose=0):
    """Show Kodi's Yes/No dialog"""
    from xbmcgui import Dialog
    if not heading:
        heading = ADDON.getAddonInfo('name')
    return Dialog().yesno(heading=heading, line1=message, nolabel=nolabel, yeslabel=yeslabel, autoclose=autoclose)


def localize(string_id, **kwargs):
    """Return the translated string from the .po language files, optionally translating variables"""
    if kwargs:
        from string import Formatter
        return Formatter().vformat(ADDON.getLocalizedString(string_id), (), SafeDict(**kwargs))
    return ADDON.getLocalizedString(string_id)


def get_setting(key, default=None):
    """Get an add-on setting"""
    try:
        value = to_unicode(ADDON.getSetting(key))
    except RuntimeError:  # Occurs when the add-on is disabled
        return default
    if value == '' and default is not None:
        return default
    return value


def translate_path(path):
    """Translate special xbmc paths"""
    return to_unicode(xbmc.translatePath(path))


def set_setting(key, value):
    """Set an add-on setting"""
    return ADDON.setSetting(key, from_unicode(str(value)))


def get_global_setting(key):
    """Get a Kodi setting"""
    result = jsonrpc(method='Settings.GetSettingValue', params=dict(setting=key))
    return result.get('result', {}).get('value')


def get_proxies():
    """Return a usable proxies dictionary from Kodi proxy settings"""
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


def get_addon_info(key):
    """Return addon information"""
    return to_unicode(ADDON.getAddonInfo(key))


def jsonrpc(*args, **kwargs):
    """Perform JSONRPC calls"""
    from json import dumps, loads

    # We do not accept both args and kwargs
    if args and kwargs:
        log(4, 'ERROR: Wrong use of jsonrpc()')
        return None

    # Process a list of actions
    if args:
        for (idx, cmd) in enumerate(args):
            if cmd.get('id') is None:
                cmd.update(id=idx)
            if cmd.get('jsonrpc') is None:
                cmd.update(jsonrpc='2.0')
        return loads(xbmc.executeJSONRPC(dumps(args)))

    # Process a single action
    if kwargs.get('id') is None:
        kwargs.update(id=0)
    if kwargs.get('jsonrpc') is None:
        kwargs.update(jsonrpc='2.0')
    return loads(xbmc.executeJSONRPC(dumps(kwargs)))


def log(level=0, message='', **kwargs):
    """Log info messages to Kodi"""
    if kwargs:
        from string import Formatter
        message = Formatter().vformat(message, (), SafeDict(**kwargs))
    message = '[{addon}] {message}'.format(addon=addon_id(), message=message)
    xbmc.log(from_unicode(message), level)


def kodi_to_ascii(string):
    """Convert Kodi format tags to ascii"""
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


def samefile(src, dest):
    """Check if file is identical"""
    stat_src = stat_file(src)
    stat_dest = stat_file(dest)
    # Check if this is a hardlink
    if (stat_src.st_dev(), stat_src.st_ino()) == (stat_dest.st_dev(), stat_dest.st_ino()):
        return True

    # Check file sizes
    if stat_src.st_size() != stat_dest.st_size():
        return False

    # Check if this is a symlink
    from os.path import samefile as opsamefile
    if opsamefile(src, dest):
        return True

    # Otherwise compare content (may be slow)
    with open(src, 'r') as srcfd, open(dest, 'r') as destfd:
        if srcfd.read() == destfd.read():
            return True

    return False


def copy(src, dest):
    """Copy a file (using xbmcvfs)"""
    from xbmcvfs import copy as vfscopy
    log(2, "Copy file '{src}' to '{dest}'.", src=src, dest=dest)
    return vfscopy(src, dest)


def delete(path):
    """Remove a file (using xbmcvfs)"""
    from xbmcvfs import delete as vfsdelete
    log(2, "Delete file '{path}'.", path=path)
    return vfsdelete(path)


def exists(path):
    """Whether the path exists (using xbmcvfs)"""
    from xbmcvfs import exists as vfsexists
    return vfsexists(path)


def hardlink(src, dest):
    """Hardlink a file when possible, copy when needed"""
    from os import link

    if exists(dest):
        delete(dest)

    try:
        link(src, dest)
    except OSError:
        return copy(src, dest)
    log(2, "Hardlink file '{src}' to '{dest}'.", src=src, dest=dest)
    return True


def mkdir(path):
    """Create a directory (using xbmcvfs)"""
    from xbmcvfs import mkdir as vfsmkdir
    log(2, "Create directory '{path}'.", path=path)
    return vfsmkdir(path)


def mkdirs(path):
    """Create directory including parents (using xbmcvfs)"""
    from xbmcvfs import mkdirs as vfsmkdirs
    log(2, "Recursively create directory '{path}'.", path=path)
    return vfsmkdirs(path)


def stat_file(path):
    """Return information about a file (using xbmcvfs)"""
    from xbmcvfs import Stat
    return Stat(path)
