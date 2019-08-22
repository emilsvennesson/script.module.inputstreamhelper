# coding: utf-8
# Created on: 04.01.2018
# Author: Roman Miroshnychenko aka Roman V.M. (roman1972@gmail.com)
"""
A class for accessing addon properties
"""

# pylint: disable=import-error,unused-wildcard-import,wildcard-import

from __future__ import absolute_import, division, unicode_literals
import sys as _sys
from .utils import PY2 as _PY2, ModuleWrapper as _ModuleWrapper

if _PY2:
    import xbmcaddon as _xbmcaddon
    _WRAPPED_XBMCADDON = _ModuleWrapper(_xbmcaddon)
    _sys.modules[__name__] = _WRAPPED_XBMCADDON
else:
    from xbmcaddon import *  # noqa
