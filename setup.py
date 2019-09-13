#!/usr/bin/python

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
    package_dir = {'': 'lib'},
    packages=find_packages('lib'),
    zip_safe=False,
)
