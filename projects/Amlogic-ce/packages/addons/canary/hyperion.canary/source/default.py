# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026-present Team CoreELEC (https://coreelec.org)

import subprocess

import xbmc

from feeder import Feeder

ADDON_ID = 'service.hyperion.canary'
UNIT = 'hyperion-canary.service'


def systemctl(command):
    try:
        subprocess.call(['systemctl', command, '--no-block', UNIT],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


if __name__ == '__main__':
    systemctl('start')
    try:
        Feeder().run()
    finally:
        # Kodi also ends this script when it quits or reinstalls the add-on, the LEDs stay on then
        if not xbmc.getCondVisibility('System.AddonIsEnabled({})'.format(ADDON_ID)):
            systemctl('stop')
