# -*- coding: utf-8 -*-
# MIT License (see LICENSE.txt or https://opensource.org/licenses/MIT)
"""Implements various Helper functions"""

from __future__ import absolute_import, division, unicode_literals
import os

from . import config
from .kodiutils import copy, delete, exists, get_setting, localize, log, mkdirs, ok_dialog, progress_dialog, set_setting, stat_file, translate_path


def temp_path():
    """Return temporary path, usually ~/.kodi/userdata/addon_data/script.module.inputstreamhelper/temp"""
    tmp_path = translate_path(os.path.join(get_setting('temp_path', 'special://masterprofile/addon_data/script.module.inputstreamhelper'), 'temp'))
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


def _http_request(url):
    """Perform an HTTP request and return request"""

    try:  # Python 3
        from urllib.error import HTTPError
        from urllib.request import urlopen
    except ImportError:  # Python 2
        from urllib2 import HTTPError, urlopen

    log(0, 'Request URL: {url}', url=url)
    filename = url.split('/')[-1]

    try:
        req = urlopen(url, timeout=5)
        log(0, 'Response code: {code}', code=req.getcode())
        if 400 <= req.getcode() < 600:
            raise HTTPError('HTTP %s Error for url: %s' % (req.getcode(), url), response=req)
    except HTTPError:
        ok_dialog(localize(30004), localize(30013, filename=filename))  # Failed to retrieve file
        return None
    return req


def http_get(url):
    """Perform an HTTP GET request and return content"""
    req = _http_request(url)
    if req is None:
        return None

    content = req.read()
    # NOTE: Do not log reponse (as could be large)
    # log(0, 'Response: {response}', response=content)
    return content.decode()


def chunked_read(readable_obj, chunk_size=32*1024):
    """Read an object in chunks, saving memory"""
    while True:
        chunk = readable_obj.read(chunk_size)
        if not chunk:
            break
        yield chunk


def after_download_check(dl_size, download_path, checksum=None, calc_checksum=None):
    """Checks download size and checksum if available"""
    empty_hashes = ('da39a3ee5e6b4b0d3255bfef95601890afd80709', 'd41d8cd98f00b204e9800998ecf8427e')
    if checksum and calc_checksum.hexdigest() in empty_hashes:
        with open(download_path, 'rb') as dl_file:
            message = localize(30058, filename=os.path.basename(download_path))  # Calculating checksum
            progress = progress_dialog()
            progress.create(localize(30014), message)  # Download in progress

            chunk_size = 32*1024
            size = 0
            for chunk in chunked_read(dl_file, chunk_size=chunk_size):
                if progress.iscanceled():
                    progress.close()
                    raise KeyboardInterrupt

                size += len(chunk)
                percent = int(100 * size / dl_size)
                progress.update(percent)
                calc_checksum.update(chunk)
        progress.close()

    if checksum and not calc_checksum.hexdigest() == checksum:
        log(4, 'Download failed, checksums do not match!')
        return False

    if not stat_file(download_path).st_size() == dl_size:
        log(4, 'Download failed, filesize does not match!')
        return False

    return True


def http_download(url, message=None, checksum=None, hash_alg='sha1', dl_size=None):
    """Makes HTTP request and displays a progress dialog on download."""
    calc_checksum = None
    if checksum:
        from hashlib import sha1, md5
        if hash_alg == 'sha1':
            calc_checksum = sha1()
        elif hash_alg == 'md5':
            calc_checksum = md5()
        else:
            log(4, 'Invalid hash algorithm specified: {}'.format(hash_alg))
            checksum = None

    filename = url.split('/')[-1]
    download_path = os.path.join(temp_path(), filename)
    if exists(download_path) and dl_size and after_download_check(dl_size, download_path, checksum, calc_checksum):
        store('download_path', download_path)
        return True

    req = _http_request(url)
    if req is None:
        return None

    if not message:  # display "downloading [filename]"
        message = localize(30015, filename=filename)  # Downloading file

    total_length = float(req.info().get('content-length'))
    progress = progress_dialog()
    progress.create(localize(30014), message)  # Download in progress

    with open(download_path, 'wb') as image:
        size = 0
        for chunk in chunked_read(req):
            image.write(chunk)
            if checksum:
                calc_checksum.update(chunk)
            size += len(chunk)
            percent = int(size * 100 / total_length)
            if progress.iscanceled():
                progress.close()
                req.close()
                raise KeyboardInterrupt
            progress.update(percent)

    if not dl_size:
        dl_size = total_length
    if not after_download_check(dl_size, download_path, checksum, calc_checksum):
        return False

    progress.close()
    req.close()
    store('download_path', download_path)
    return True


def unzip(source, destination, file_to_unzip=None, result=[]):  # pylint: disable=dangerous-default-value
    """Unzip files to specified path"""

    if not exists(destination):
        mkdirs(destination)

    from zipfile import ZipFile
    zip_obj = ZipFile(source)
    for filename in zip_obj.namelist():
        if file_to_unzip and filename != file_to_unzip:
            continue

        # Detect and remove (dangling) symlinks before extraction
        fullname = os.path.join(destination, filename)
        if os.path.islink(fullname):
            log(3, 'Remove (dangling) symlink at {symlink}', symlink=fullname)
            delete(fullname)

        zip_obj.extract(filename, destination)
        result.append(True)  # Pass by reference for Thread

    return bool(result)


def p7unzip(source, destination=temp_path(), file_to_unzip=None, result=[]):  # pylint: disable=dangerous-default-value
    """Unzip file to specified path using p7zip"""
    if not exists(destination):
        mkdirs(destination)

    cmd = ['7z', 'e', '-y', '-o' + destination, source]
    if file_to_unzip:
        cmd.append(file_to_unzip)

    output = run_cmd(cmd)

    result.append(output['success'])
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


def store(name, val=None):
    """Store arbitrary value across functions"""

    if val is not None:
        setattr(store, name, val)
        log(0, 'Stored {value} in {name}', value=val, name=name)
        return val

    if not hasattr(store, name):
        return None
    return getattr(store, name)


def diskspace():
    """Return the free disk space available (in bytes) in temp_path."""
    statvfs = os.statvfs(temp_path())
    return statvfs.f_frsize * statvfs.f_bavail


def cmd_exists(cmd):
    """Check whether cmd exists on system."""
    # https://stackoverflow.com/questions/377017/test-if-executable-exists-in-python
    import subprocess
    return subprocess.call(['type ' + cmd], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0


def run_cmd(cmd, sudo=False, shell=False):
    """Run subprocess command and return if it succeeds as a bool"""
    from .unicodes import to_unicode
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
    if 'sudo' in cmd:
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
            return "{:3.1f}{}{}".format(num, unit, suffix)
        num /= 1024.0
    return "{:.1f}{}{}".format(num, 'Yi', suffix)


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
        import re
        arm_version = re.search(r'\d+', sys_arch.split('v')[1])
        if arm_version:
            sys_arch = 'armv' + arm_version.group()

    if sys_arch in config.ARCH_MAP:
        sys_arch = config.ARCH_MAP[sys_arch]

    log(0, 'Found system architecture {arch}', arch=sys_arch)

    arch.cached = sys_arch
    return sys_arch


def hardlink(src, dest):
    """Hardlink a file when possible, copy when needed"""
    from os import link

    if exists(dest):
        delete(dest)

    try:
        link(src, dest)
    except (AttributeError, OSError):
        return copy(src, dest)
    log(2, "Hardlink file '{src}' to '{dest}'.", src=src, dest=dest)
    return True
