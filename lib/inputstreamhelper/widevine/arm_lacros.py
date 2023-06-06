# -*- coding: utf-8 -*-
# MIT License (see LICENSE.txt or https://opensource.org/licenses/MIT)
"""Implements ARM specific widevine functions for Lacros image"""

import os
import json
from ctypes.util import find_library

from lib.PySquashfsImage import SquashFsImage
from .. import config
from ..kodiutils import localize, log, mkdirs, open_file, progress_dialog
from ..utils import http_download, http_get, store, system_os, userspace64


def cdm_from_lacros():
    """Whether the Widevine CDM can/should be extracted from a lacros image"""
    return bool(find_library("zstd"))  # The lacros images are compressed with zstd


def latest_lacros():
    """Finds the version of the latest lacros beta image (stable images are not available for download)"""
    latest = json.loads(http_get(config.LACROS_LATEST))[0]["version"]
    log(0, f"latest lacros image version is {latest}")
    return latest


def extract_widevine_lacros(dl_path, backup_path, img_version):
    """Extract Widevine from the given Lacros image"""
    progress = progress_dialog()
    progress.create(heading=localize(30043), message=localize(30044))  # Extracting Widevine CDM, prepping image

    with SquashFsImage(dl_path) as img:
        fnames = (config.WIDEVINE_CDM_FILENAME[system_os()], config.WIDEVINE_MANIFEST_FILE, "LICENSE")  # Here it's not LICENSE.txt, as defined in the config.py
        mkdirs(os.path.join(backup_path, img_version))
        for num, fname in enumerate(fnames):
            cfile = img.find(fname)
            if not cfile:
                log(3, f"{fname} not found in {os.path.basename(dl_path)}")
                return False

            with open_file(os.path.join(backup_path, img_version, cfile.name), 'wb') as outfile:
                outfile.write(cfile.read_bytes())
            progress.update(int(90 / len(fnames) * (num + 1)), localize(30048))  # Extracting from image

    log(0, f"Successfully extracted all files from lacros image {os.path.basename(dl_path)}")
    return progress


def install_widevine_arm_lacros(backup_path, img_version=None):
    """Installs Widevine CDM extracted from a Chrome browser SquashFS image on ARM-based architectures."""

    if not img_version:
        img_version = latest_lacros()

    url = config.LACROS_DOWNLOAD_URL.format(version=img_version, arch=("arm64" if userspace64() else "arm"))

    downloaded = http_download(url, message=localize(30072))

    if downloaded:
        progress = extract_widevine_lacros(store("download_path"), backup_path, img_version)
        if progress:
            return (progress, img_version)

    return False
