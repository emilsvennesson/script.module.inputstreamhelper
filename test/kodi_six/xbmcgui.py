# coding: utf-8
# Created on: 04.01.2018
# Author: Roman Miroshnychenko aka Roman V.M. (roman1972@gmail.com)
"""
Classes and functions for interacting with Kodi GUI
"""

# pylint: disable=import-error,unused-wildcard-import,wildcard-import

from __future__ import absolute_import, division, unicode_literals
import sys as _sys
from .utils import PY2 as _PY2, ModuleWrapper as _ModuleWrapper

if _PY2:
    import xbmcgui as _xbmcgui
    _WRAPPED_XBMCGUI = _ModuleWrapper(_xbmcgui)
    _sys.modules[__name__] = _WRAPPED_XBMCGUI
else:
    from xbmcgui import *  # noqa
