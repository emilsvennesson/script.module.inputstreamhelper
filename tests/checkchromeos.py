# -*- coding: utf-8 -*-
"""Check Chrome OS recovery images availability"""

from __future__ import absolute_import, division, print_function, unicode_literals
from xml.etree import ElementTree as ET
import requests
from lib.inputstreamhelper.config import CHROMEOS_RECOVERY_ARM_BNAMES, CHROMEOS_RECOVERY_ARM64_BNAMES, CHROMEOS_RECOVERY_URL


class OutdatedException(Exception):
    """Is thrown when InputStreamHelper configuration should be updated."""

    def __init__(self, message):
        self.message = message
        super(OutdatedException, self).__init__(self.message)


def get_devices():
    """Get Chrome OS devices as json object"""
    url = 'https://www.chromium.org/chromium-os/developer-information-for-chrome-os-devices'
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    html = response.text.split('<table>')[3].split('</table>')[0]
    html = '<table>' + html + '</table>'
    html = html.replace('&', '&#38;')
    html = html.replace('<white label>', 'white label')
    table = ET.XML(html.encode('utf-8'))
    keys = [k.text.strip() for k in table[0]]
    devices = []
    for row in table[1:]:
        device = {}
        for num, value in enumerate(row):
            device[keys[num]] = None
            if value.text:
                device[keys[num]] = value.text.strip()
            elif value.find('a') is not None and value.find('a').text is not None:
                device[keys[num]] = value.find('a').text.strip()
        devices.append(device)
    return devices


def get_arm_devices():
    """Get Chrome OS ARM devices as json object"""
    devices = get_devices()
    arm_devices = []
    for device in devices:
        if device.get('User ABI') == 'arm':
            arm_devices.append(device)
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
    serves = get_serves()
    recoveries = get_recoveries()
    compatibles = []
    for device in arm_devices:
        board = device.get('Board name(s)').lower().replace('_', '-')
        served_board = serves.get(board)
        if served_board and not served_board.get('isAue'):
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
