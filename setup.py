#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Dag Wieers (@dagwieers) <dag@wieers.com>
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, unicode_literals
from setuptools import setup, find_packages
import os
from xml.dom.minidom import parse

project_dir = os.path.dirname(os.path.abspath(__file__))
metadata = parse(os.path.join(project_dir, 'addon.xml'))
addon_version = metadata.firstChild.getAttribute('version')
addon_id = metadata.firstChild.getAttribute('id')

setup(
    name='inputstreamhelper',
    version=addon_version,
    url='https://github.com/tamland/kodi-plugin-routing',
    author='Emil Svennesson',
    description='Kodi InputStream Helper',
    long_description=open(os.path.join(project_dir, 'README.md')).read(),
    keywords='Kodi, plugin, inputstream, helper',
    license='MIT',
    package_dir={'': 'lib'},
    packages=find_packages('lib'),
    zip_safe=False,
)
