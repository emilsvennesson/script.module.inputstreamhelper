# -*- coding: utf-8 -*-
# MIT License (see LICENSE.txt or https://opensource.org/licenses/MIT)
"""Implements various Helper functions"""

from __future__ import absolute_import, division, unicode_literals

import os
import re
import struct
from functools import total_ordering
from socket import timeout
from time import time
from typing import NamedTuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from . import config
from .kodiutils import (bg_progress_dialog, copy, delete, exists, get_setting,
                        localize, log, mkdirs, progress_dialog, set_setting,
                        stat_file, translate_path, yesno_dialog)
from .unicodes import compat_path, from_unicode, to_unicode


@total_ordering
class Version(NamedTuple):
    """Minimal version class used for parse_version. Should be enough for our purpose."""
    major: int = 0
    minor: int = 0
    micro: int = 0
    nano: int = 0

    def __str__(self):
        return f"{self.major}.{self.minor}.{self.micro}.{self.nano}"

    def __lt__(self, other):
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        if self.micro != other.micro:
            return self.micro < other.micro

        return self.nano < other.nano

    def __eq__(self, other):
        return all((self.major == other.major, self.minor == other.minor, self.micro == other.micro, self.nano == other.nano))


def temp_path():
    """Return temporary path, usually ~/.kodi/userdata/addon_data/script.module.inputstreamhelper/temp/"""
    tmp_path = translate_path(os.path.join(get_setting('temp_path', 'special://masterprofile/addon_data/script.module.inputstreamhelper'), 'temp', ''))
    if not exists(tmp_path):
        mkdirs(tmp_path)

    return tmp_path


def update_temp_path(new_temp_path):
    """"Updates temp_path and merges files."""
    old_temp_path = temp_path()

    set_setting('temp_path', new_temp_path)
    if old_temp_path != temp_path():
        from shutil import move
        move(old_temp_path, temp_path())


def download_path(url):
    """Choose download target directory based on url."""
    filename = url.split('/')[-1]

    return os.path.join(temp_path(), filename)


def _http_request(url, headers=None, time_out=30):
    """Make a robust HTTP request handling redirections."""
    try:
        response = urlopen(url, timeout=time_out)  # pylint: disable=consider-using-with:w
        if response.status in [301, 302, 303, 307, 308]:  # Handle redirections
            new_url = response.getheader('Location')
            log(1, f"Redirecting to {new_url}")
            return _http_request(new_url, time_out)
        return response  # Return the response for streaming
    except (HTTPError, URLError) as err:
        log(2, 'Download failed with error {}'.format(err))
        if yesno_dialog(localize(30004), '{line1}\n{line2}'.format(line1=localize(30063), line2=localize(30065))):
            return _http_request(url, headers, time_out)
        return None
    except timeout as err:
        log(2, f"HTTP request timed out: {err}")
        return None


def http_get(url):
    """Perform an HTTP GET request and return content"""
    req = _http_request(url)
    if req is None:
        return None
    content = req.read()
    # NOTE: Do not log reponse (as could be large)
    # log(0, 'Response: {response}', response=content)
    return content.decode("utf-8")


def http_head(url):
    """Perform an HTTP HEAD request and return status code."""
    req = Request(url)
    req.get_method = lambda: 'HEAD'
    try:
        with urlopen(req) as resp:
            return resp.getcode()
    except HTTPError as exc:
        return exc.getcode()


# pylint: disable=too-many-positional-arguments
def http_download(url, message=None, checksum=None, hash_alg='sha1', dl_size=None, background=False):
    """Makes HTTP request and displays a progress dialog on download."""
    calc_checksum = _initialize_checksum(checksum, hash_alg)
    if checksum and not calc_checksum:
        checksum = None

    response = _http_request(url)
    if response is None:
        return None

    dl_path = download_path(url)
    filename = os.path.basename(dl_path)
    if not message:
        message = localize(30015, filename=filename)  # Downloading file

    total_length = int(response.info().get('content-length', 0))
    if dl_size and dl_size != total_length:
        log(2, 'The given file size does not match the request!')
        dl_size = total_length

    progress = _create_progress_dialog(background, message)

    success = _download_file(response, dl_path, calc_checksum, total_length, message, progress, background)

    progress.close()
    response.close()

    if not success:
        return False

    checksum_ok = _verify_checksum(checksum, calc_checksum)
    size_ok = _verify_size(dl_size, dl_path)

    if not checksum_ok or not size_ok:
        if not _handle_corrupt_file(dl_size, dl_path, checksum, calc_checksum, filename):
            return False

    return dl_path


def _initialize_checksum(checksum, hash_alg):
    if not checksum:
        return None

    from hashlib import md5, sha1
    if hash_alg == 'sha1':
        return sha1()
    if hash_alg == 'md5':
        return md5()
    log(4, 'Invalid hash algorithm specified: {}'.format(hash_alg))
    return None


def _create_progress_dialog(background, message):
    progress = bg_progress_dialog() if background else progress_dialog()
    progress.create(localize(30014), message=message)  # Download in progress
    return progress


# pylint: disable=too-many-positional-arguments
def _download_file(response, dl_path, calc_checksum, total_length, message, progress, background):
    starttime = time()
    chunk_size = 32 * 1024
    size = 0

    with open(compat_path(dl_path), 'wb') as image:
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break

            image.write(chunk)
            if calc_checksum:
                calc_checksum.update(chunk)
            size += len(chunk)
            percent = int(round(size * 100 / total_length)) if total_length > 0 else 0

            if not background and progress.iscanceled():
                return False

            if time() - starttime > 5 and size > 0:
                time_left = int(round((total_length - size) * (time() - starttime) / size))
                prog_message = '{line1}\n{line2}'.format(
                    line1=message,
                    line2=localize(30058, mins=time_left // 60, secs=time_left % 60))
            else:
                prog_message = message

            progress.update(percent, prog_message)

    return True


def _verify_checksum(checksum, calc_checksum):
    if not checksum:
        return True
    if calc_checksum:
        return calc_checksum.hexdigest() == checksum
    return False


def _verify_size(dl_size, dl_path):
    if not dl_size:
        return True
    return stat_file(dl_path).st_size() == dl_size


def _handle_corrupt_file(dl_size, dl_path, checksum, calc_checksum, filename):
    log(4, 'Something may be wrong with the downloaded file.')
    if checksum and calc_checksum:
        log(4, 'Provided checksum: {}\nCalculated checksum: {}'.format(checksum, calc_checksum.hexdigest()))
    if dl_size:
        free_space = sizeof_fmt(diskspace())
        log(4, 'Expected filesize: {}\nReal filesize: {}\nRemaining diskspace: {}'.format(
            dl_size, stat_file(dl_path).st_size(), free_space))
    if yesno_dialog(localize(30003), localize(30070, filename=filename)):
        log(4, 'Continuing despite possibly corrupt file!')
        return True

    return False


def unzip(source, destination, file_to_unzip=None, result=[]):  # pylint: disable=dangerous-default-value
    """Unzip files to specified path"""

    if not exists(destination):
        mkdirs(destination)

    from zipfile import ZipFile
    with ZipFile(compat_path(source)) as zip_obj:
        for filename in zip_obj.namelist():
            if file_to_unzip and filename != file_to_unzip:
                continue

            # Detect and remove (dangling) symlinks before extraction
            fullname = os.path.join(destination, filename)
            if os.path.islink(compat_path(fullname)):
                log(3, 'Remove (dangling) symlink at {symlink}', symlink=fullname)
                delete(fullname)

            zip_obj.extract(filename, compat_path(destination))
            result.append(True)  # Pass by reference for Thread

    return bool(result)


def system_os():
    """Get system platform, and remember this information"""

    if hasattr(system_os, 'cached'):
        return getattr(system_os, 'cached')

    from xbmc import getCondVisibility
    if getCondVisibility('system.platform.android'):
        sys_name = 'Android'
    else:
        from platform import system
        sys_name = system()

    system_os.cached = sys_name
    return sys_name


def diskspace():
    """Return the free disk space available (in bytes) in temp_path."""
    statvfs = os.statvfs(compat_path(temp_path()))
    return statvfs.f_frsize * statvfs.f_bavail


def cmd_exists(cmd):
    """Check whether cmd exists on system."""
    # https://stackoverflow.com/questions/377017/test-if-executable-exists-in-python
    import subprocess
    return subprocess.call(['type ' + cmd], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0


def run_cmd(cmd, sudo=False, shell=False):
    """Run subprocess command and return if it succeeds as a bool"""
    import subprocess
    env = os.environ.copy()
    env['LANG'] = 'C'
    output = ''
    success = False
    if sudo and os.getuid() != 0 and cmd_exists('sudo'):
        cmd.insert(0, 'sudo')

    try:
        output = to_unicode(subprocess.check_output(cmd, shell=shell, stderr=subprocess.STDOUT, env=env))
    except subprocess.CalledProcessError as error:
        output = to_unicode(error.output)
        log(4, '{cmd} cmd failed.', cmd=cmd)
    except OSError as error:
        log(4, '{cmd} cmd doesn\'t exist. {error}', cmd=cmd, error=error)
    else:
        success = True
        log(0, '{cmd} cmd executed successfully.', cmd=cmd)

    if output.rstrip():
        log(0, '{cmd} cmd output:\n{output}', cmd=cmd, output=output)
    if from_unicode('sudo') in cmd:
        subprocess.call(['sudo', '-k'])  # reset timestamp

    return {
        'output': output,
        'success': success
    }


def sizeof_fmt(num, suffix='B'):
    """Return size of file in a human readable string."""
    # https://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def arch():
    """Map together, cache and return the system architecture"""

    if hasattr(arch, 'cached'):
        return getattr(arch, 'cached')

    from platform import architecture, machine
    sys_arch = machine()
    if sys_arch == 'AMD64':
        sys_arch_bit = architecture()[0]
        if sys_arch_bit == '32bit':
            sys_arch = 'x86'  # else, sys_arch = AMD64

    elif 'armv' in sys_arch:
        arm_version = re.search(r'\d+', sys_arch.split('v')[1])
        if arm_version:
            sys_arch = 'armv' + arm_version.group()

    if sys_arch in config.ARCH_MAP:
        sys_arch = config.ARCH_MAP[sys_arch]

    log(0, 'Found system architecture {arch}', arch=sys_arch)

    arch.cached = sys_arch
    return sys_arch


def userspace64():
    """To check if userspace is 64bit or 32bit"""
    return struct.calcsize('P') * 8 == 64


def hardlink(src, dest):
    """Hardlink a file when possible, copy when needed"""
    if exists(dest):
        delete(dest)

    try:
        from os import link
        link(compat_path(src), compat_path(dest))
    except (AttributeError, OSError, ImportError):
        return copy(src, dest)
    log(2, "Hardlink file '{src}' to '{dest}'.", src=src, dest=dest)
    return True


def remove_tree(path):
    """Remove an entire directory tree"""
    from shutil import rmtree
    rmtree(compat_path(path))


def parse_version(vstring):
    """Parse a version string and return a comparable version object, properly handling non-numeric prefixes."""
    vstring = vstring.strip('v').lower()
    parts = re.split(r'\.', vstring)  # split on periods first

    vnums = []
    for part in parts:
        # extract numeric part, ignoring non-numeric prefixes
        numeric_part = re.search(r'\d+', part)
        if numeric_part:
            vnums.append(int(numeric_part.group()))
        else:
            vnums.append(0)  # default to 0 if no numeric part found

    # ensure the version tuple always has 4 components
    vnums = (vnums + [0] * 4)[:4]

    return Version(*vnums)
