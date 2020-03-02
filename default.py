# -*- coding: utf-8 -*-
''' This is the actual InputStream Helper API script entry point '''

from __future__ import absolute_import, division, unicode_literals
import sys
import os.path
from xbmc import translatePath
from xbmcaddon import Addon


def to_unicode(text, encoding='utf-8'):
    ''' Force text to unicode '''
    return text.decode(encoding) if isinstance(text, bytes) else text


# NOTE: This is required so our RunScript interface can import our own inputstreamhelper package
sys.path.append(os.path.join(to_unicode(translatePath(Addon().getAddonInfo('path'))), 'lib'))
from inputstreamhelper.api import run  # noqa: E402

run(sys.argv)
