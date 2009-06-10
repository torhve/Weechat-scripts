''' Buffer searcher '''
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
# Set screen title
# (this script requires WeeChat 0.3.0 or newer)
#
# History:
# 2009-05-24, xt <xt@bash.no>
#     version 0.1: initial release

import weechat as w
import re
weechat = w

SCRIPT_NAME    = "bufsearch"
SCRIPT_AUTHOR  = "xt <tor@bash.no>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Search in buffer"
SCRIPT_COMMAND = 'grep'

# script options
#settings = {
#    "title_priority"       : '2',
#    }

#hooks = (
#        'buffer_switch',
#        'hotlist_*',
#)

if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                    SCRIPT_DESC, "", ""):
#    for option, default_value in settings.iteritems():
#        if weechat.config_get_plugin(option) == "":
#            weechat.config_set_plugin(option, default_value)
#    for hook in hooks:
#        weechat.hook_signal(hook, 'update_title', '')
    w.hook_command(SCRIPT_COMMAND,
                         "Buffer searcher",
                         "[expression]",
                         "   expression: search expression\n",
                         "",
                         "bufsearch_cmd",
                         "")

def bufsearch_cmd(data, buffer, args):
    #cb = weechat.current_buffer()

    matcher = re.compile(args)

    infolist = w.infolist_get('buffer_lines', buffer, '')
    channel =  w.buffer_get_string(buffer, 'name')
    while w.infolist_next(infolist):
        message = w.infolist_string(infolist, 'message')
        prefix = w.infolist_string(infolist, 'prefix')
        if matcher.search(message) or matcher.search(prefix):
            w.prnt('', '%s %s%s %s' %(\
                w.infolist_time(infolist, 'date'),
                w.infolist_string(infolist, 'prefix'),
                w.color('reset'),
                w.infolist_string(infolist, 'message'),
                ))

    w.infolist_free(infolist)
    return weechat.WEECHAT_RC_OK


