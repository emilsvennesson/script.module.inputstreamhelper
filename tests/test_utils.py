# -*- coding: utf-8 -*-
# MIT License (see LICENSE.txt or https://opensource.org/licenses/MIT)
"""Implements various helper functions"""

from __future__ import absolute_import, division, unicode_literals
import inputstreamhelper


def delete_cached():
    """Delete cached property from one or more objects"""
    if hasattr(inputstreamhelper.arch, 'cached'):
        del inputstreamhelper.arch.cached
