# -*- coding: utf-8 -*-
"""Check Chrome OS recovery images availability"""

from __future__ import absolute_import, division, print_function, unicode_literals
from xml.etree import ElementTree as ET
import requests
from lib.inputstreamhelper.config import CHROMEOS_RECOVERY_ARM_HWIDS


def get_devices():
    """Get Chrome OS devices as json object"""
    url = 'https://www.chromium.org/chromium-os/developer-information-for-chrome-os-devices'
    response = requests.get(url)
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
            elif value.find('a') is not None:
                if value.find('a').text is not None:
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
    url = 'https://cros-updates-serving.appspot.com/csv'
    response = requests.get(url)
    response.raise_for_status()
    csv = response.text
    keys = list(csv.split('\n')[0].split(','))
    serves = []
    for row in csv.split('\n')[1:]:
        serve = {}
        for num, value in enumerate(row.split(',')):
            serve[keys[num]] = value
        serves.append(serve)
    return serves


def get_recoveries():
    """Get Chrome OS recovery items as json object"""
    url = 'https://dl.google.com/dl/edgedl/chromeos/recovery/recovery.json'
    response = requests.get(url)
    response.raise_for_status()
    recoveries = response.json()
    return recoveries


def get_compatibles():
    """Get compatible Chrome OS recovery items"""
    arm_devices = get_arm_devices()
    serves = get_serves()
    recoveries = get_recoveries()
    boards = []
    compatibles = []
    for device in arm_devices:
        full_board = device.get('Board name(s)').lower()
        if '_' in full_board:
            board = full_board.split('_')[1]
        else:
            board = full_board
        for serve in serves:
            if board == serve.get('board') and serve.get('eol') == 'False' and board not in boards:
                boards.append(board)
                for recovery in recoveries:
                    r_board = recovery.get('file').split('_')[2]
                    if '-' in r_board:
                        r_board = r_board.replace('-', '_')
                    if full_board == r_board:
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


def check_hwids():
    """Check if hardware id's in inputstreamhelper.config are up to date"""
    compatibles = get_compatibles()
    hwids = []
    messages = []
    for compatible in compatibles:
        hwid = compatible.get('hwidmatch').strip('^.*-').split(' ')[0]
        if hwid not in hwids:
            hwids.append(hwid)

    for item in CHROMEOS_RECOVERY_ARM_HWIDS:
        if item not in hwids:
            messages.append('%s is end-of-life, consider removing it from inputstreamhelper config' % item)
    for item in hwids:
        if item not in CHROMEOS_RECOVERY_ARM_HWIDS:
            messages.append('%s is missing, please add it to inputstreamhelper config' % item)
    if messages:
        raise Exception(messages)

    smallest = get_smallest()
    hwid = smallest.get('hwidmatch').strip('^.*-').split(' ')[0]
    print('Chrome OS hardware id\'s are up to date, current smallest recovery image is %s' % hwid)


def run():
    """Main function"""
    check_hwids()


if __name__ == '__main__':
    run()
