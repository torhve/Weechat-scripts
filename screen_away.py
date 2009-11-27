# -*- coding: utf-8 -*-
#
# Copyright (c) 2009 by xt <xt@bash.no>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

#
# (this script requires WeeChat 0.3.0 or newer)
#
# History:
# 2009-11-27, xt <xt@bash.no>
#   version 0.1: initial release

import weechat as w
import re
import os

SCRIPT_NAME    = "screen_away"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Set away status on screen detach"

settings = {
        'message': 'Detached from screen',
        'interval': '60': # How often in seconds to check screen status
}

IS_AWAY = False

if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                    SCRIPT_DESC, "", ""):
    for option, default_value in settings.iteritems():
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, default_value)
    w.hook_timer(\
            int(w.config_get_plugin(̈́'interval')) * 1000,
            0,
            0,
            "screen_away_timer_cb",
            '')

def screen_away_timer_cb(buffer, args):

    global IS_AWAY

    if not 'STY' in os.environ.keys():
        # We are not running under screen, just exit.
        return w.WEECHAT_RC_OK

    cmd_output = os.popen('LC_ALL=C screen -ls').read()
    socket_path = re.findall('Sockets? in (?P<socket_path>.+)\.', cmd_output)[0]
    socket_file = os.environ['STY']
    socket = os.path.join(socket_path, socket_file)
    if os.access(socket, os.X_OK):
        # Screen is attached
        if IS_AWAY:
            # Only remove away status if it was set by this script
            w.command('', "/away -all")
            w.prnt('', '%s: Detected screen attach. Clearing away status' %SCRIPT_NAME)
            IS_AWAY = False
    else:
        # if it has X bit set screen is attached 
        if not IS_AWAY: # Do not set away if we are already set away
            w.command('', "/away -all %s" %w.config_get_plugin('message') );
            w.prnt('', '%s: Detected screen detach. Setting away status' %SCRIPT_NAME)
            IS_AWAY = True

    return w.WEECHAT_RC_OK
