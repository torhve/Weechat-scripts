# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 by xt <xt@bash.no>
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
#
# If someone posts an URL in a configured channel
# this script will post back title 

# 
#
# History:
# 2010-02-03, xt
#   version 0.1: initial

import weechat
import re
import time
w = weechat

SCRIPT_NAME    = "colorize_nicks"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL"
SCRIPT_DESC    = "Colorize nicks"

settings = {
    "whitelist_channels"        : '',     # comma separated list of channels
    "blacklist_channels"        : '',     # comma separated list of channels
    "blacklist_nicks"           : '',     # comma separated list of nicks
    "min_nick_length"           : '',     # length
}


VALID_NICK = r'([@~&!%+])?([-a-zA-Z0-9\[\]\\`_^\{|\}]+)'
PREFIX_COLORS = {
        '@' : 'nicklist_prefix1',
        '~' : 'nicklist_prefix1',
        '&' : 'nicklist_prefix1',
        '!' : 'nicklist_prefix1',
        '%' : 'nicklist_prefix2',
        '+' : 'nicklist_prefix3',
}
ignore_channels = []
ignore_nicks = []

colored_nicks = {}

def colorize_cb(data, modifier, modifier_data, line):

    global ignore_nicks, ignore_channels, colored_nicks
    if not 'irc_privmsg' in modifier_data:
        return line

    channel = modifier_data.split(';')[1]
# TODO BLACKLIST CHECK
#
    min_length = int(w.config_get_plugin('min_nick_length'))
    reset = w.color('reset')

    for words in re.findall(VALID_NICK, line):
        prefix, nick = words[0], words[1]
        if len(nick) < min_length:
            continue
        if nick in colored_nicks:
            nick_color = colored_nicks[nick]
            #nick_color = w.info_get('irc_nick_color', nick)
            line = line.replace(nick, '%s%s%s' %(nick_color, nick, reset))

    return line


def populate_nicks(*kwargs):
    servers = w.infolist_get('irc_server', '', '')
    while w.infolist_next(servers):
        servername = w.infolist_string(servers, 'name')
        channels = w.infolist_get('irc_channel', '', servername)
        while w.infolist_next(channels):
            nicklist = w.infolist_get('nicklist', w.infolist_pointer(channels, 'buffer'), '')
            while w.infolist_next(nicklist):
                nick = w.infolist_string(nicklist, 'name')
                colored_nicks[nick] = w.info_get('irc_nick_color', nick)

            w.infolist_free(nicklist)

        w.infolist_free(channels)

    w.infolist_free(servers)
    return w.WEECHAT_RC_OK

if __name__ == "__main__":
    if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                        SCRIPT_DESC, "", ""):
        # Set default settings
        for option, default_value in settings.iteritems():
            if not w.config_is_set_plugin(option):
                w.config_set_plugin(option, default_value)

        for key, value in PREFIX_COLORS.iteritems():
            PREFIX_COLORS[key] = w.color(w.config_string(w.config_get('weechat.look.%s'%value)))
        ignore_channels = w.config_get_plugin('blacklist_channels').split(',')
        ignore_nicks = w.config_get_plugin('blacklist_nicks').split(',')

        populate_nicks()
        w.hook_modifier('weechat_print', 'colorize_cb', '')
        w.hook_signal('nicklist_changed', 'populate_nicks', '')
