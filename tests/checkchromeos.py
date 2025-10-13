# -*- coding: utf-8 -*-
"""Check Chrome OS recovery images availability"""

import requests
from lib.inputstreamhelper.config import CHROMEOS_RECOVERY_ARM_BNAMES, CHROMEOS_RECOVERY_ARM64_BNAMES, CHROMEOS_RECOVERY_URL


class OutdatedException(Exception):
    """Is thrown when InputStreamHelper configuration should be updated."""

    def __init__(self, message):
        self.message = message
        super(OutdatedException, self).__init__(self.message)


def get_arm_devices():
    """Get Chrome OS ARM devices as json object"""
    serves = get_serves()
    arm_devices = []

    for main, data in serves.items():
        # Collect all candidate boards (top-level + submodels)
        candidates = []

        # Top-level board
        if 'brandNameToFormattedDeviceMap' in data:
            candidates.append((data.get('fsiMilestoneNumber', 0), data, main.split('-')[-1]))

        # Submodels
        for sub_data in (data.get('models') or {}).values():
            if 'brandNameToFormattedDeviceMap' in sub_data:
                candidates.append((sub_data.get('fsiMilestoneNumber', 0), sub_data, main))

        if not candidates:
            continue

        # Pick the board with the highest milestone number
        _, best, board = max(candidates, key=lambda x: x[0] or 0)

        device_map = best.get('brandNameToFormattedDeviceMap', {})
        push_recoveries = best.get('pushRecoveries', {})
        max_version = int(max(push_recoveries.keys(), default=0))
        first_available = best.get('fsiMilestoneNumber')
        eol = best.get('isAue', False)

        serving_stable = best.get('servingStable', {})
        chrome_version = serving_stable.get('chromeVersion')
        version = serving_stable.get('version')

        # Build output entries for ARM devices
        entry = {
            board: {
                'first': first_available,
                'last': max_version,
                'eol': eol,
                'chrome': chrome_version,
                'version': version,
            }
        }

        # Append only if architecture is ARM
        for info in device_map.values():
            arch = info.get('architecture', '').lower()
            if arch in {'arm_64', 'arm_32'} and entry not in arm_devices:
                arm_devices.append(entry)

    return arm_devices


def get_serves():
    """Get Chrome OS serving updates as json object"""
    url = 'https://chromiumdash.appspot.com/cros/fetch_serving_builds?deviceCategory=Chrome%20OS'
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    serves = response.json().get('builds')
    return serves


def get_recoveries():
    """Get Chrome OS recovery items as json object"""
    response = requests.get(CHROMEOS_RECOVERY_URL, timeout=10)
    response.raise_for_status()
    recoveries = response.json()
    return recoveries


def get_compatibles():
    """Get compatible Chrome OS recovery items"""
    arm_devices = get_arm_devices()
    recoveries = get_recoveries()
    compatibles = []
    for device in arm_devices:
        board = next(iter(device), None)
        if board and not device[board].get('eol'):
            for recovery in recoveries:
                r_board = recovery.get('file').split('_')[2]
                if board == r_board:
                    compatibles.append(recovery)
    return compatibles


def get_smallest():
    """Get the Chrome OS recovery item with the smallest filesize"""
    compatibles = get_compatibles()
    smallest = None
    for item in compatibles:
        if smallest is None:
            smallest = item
        if (int(item.get('filesize')) + int(item.get('zipfilesize'))
                < int(smallest.get('filesize')) + int(smallest.get('zipfilesize'))):
            smallest = item
    return smallest


def check_boardnames():
    """Check if boardnames in inputstreamhelper.config are up to date"""
    compatibles = get_compatibles()
    bnames = []
    messages = []
    for compatible in compatibles:
        bname = compatible.get('file').split('_')[2]
        if bname not in bnames:
            bnames.append(bname)

    for item in CHROMEOS_RECOVERY_ARM_BNAMES + CHROMEOS_RECOVERY_ARM64_BNAMES:
        if item not in bnames:
            messages.append('{} is end-of-life, consider removing it from inputstreamhelper config'.format(item))
    for item in bnames:
        if item not in CHROMEOS_RECOVERY_ARM_BNAMES + CHROMEOS_RECOVERY_ARM64_BNAMES:
            messages.append('{} is missing, please add it to inputstreamhelper config'.format(item))
    if messages:
        raise OutdatedException(messages)

    smallest = get_smallest()
    bname = smallest.get('file').split('_')[2]
    print('Chrome OS boardnames are up to date, current smallest recovery image is {}'.format(bname))


def run():
    """Main function"""
    check_boardnames()


if __name__ == '__main__':
    run()
