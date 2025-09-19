# -*- coding: utf-8 -*-
# MIT License (see LICENSE.txt or https://opensource.org/licenses/MIT)
"""Implements various helper functions"""

from shutil import rmtree

import inputstreamhelper

xbmcvfs = __import__('xbmcvfs')


def delete_cached():
    """Delete cached property from one or more objects"""
    if hasattr(inputstreamhelper.arch, 'cached'):
        del inputstreamhelper.arch.cached


def cleanup():
    """Delete cdm directory before starting tests for different platform"""
    try:
        rmtree(xbmcvfs.translatePath('special://home/cdm'))
    except FileNotFoundError:
        pass
