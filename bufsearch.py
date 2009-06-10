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

from __future__ import with_statement # This isn't required in Python 2.6
import weechat as w
import re
weechat = w

SCRIPT_NAME    = "bufsearch"
SCRIPT_AUTHOR  = "xt <tor@bash.no>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Search in buffer"
SCRIPT_COMMAND = 'grep'



def buffer_input(*kwargs):
    return w.WEECHAT_RC_OK

def buffer_close(*kwargs):
    global search_buffer
    search_buffer =  None
    return w.WEECHAT_RC_OK

if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                    SCRIPT_DESC, "", ""):
    w.hook_command(SCRIPT_COMMAND,
                         "Buffer searcher",
                         "[expression]",
                         "   expression: search expression\n",
                         "",
                         "bufsearch_cmd",
                         "")

search_buffer = w.buffer_new(SCRIPT_NAME, "buffer_input", "", "buffer_close", "")
w.buffer_set(search_buffer, "type", "free")
w.buffer_set(search_buffer, "title", "Search output buffer")

def print_buffer(matching_lines):
    w.buffer_set(search_buffer, "title", "Search matched %s lines" % len(matching_lines) )
    for y, line in enumerate(matching_lines):
        weechat.prnt_y(search_buffer, y, '%s %s%s %s' % (\
            line[0],
            line[1],
            w.color('reset'),
            line[2]))

def find_infolist_matching_lines(buffer, matcher):
    matching_lines = []
    infolist = w.infolist_get('buffer_lines', buffer, '')
    while w.infolist_next(infolist):
        message = w.infolist_string(infolist, 'message')
        prefix = w.infolist_string(infolist, 'prefix')
        if matcher.search(message) or matcher.search(prefix):
            matching_lines.append((
                w.infolist_time(infolist, 'date'),
                w.infolist_string(infolist, 'prefix'),
                w.infolist_string(infolist, 'message'),
                ))

    w.infolist_free(infolist)

    return matching_lines


def bufsearch_cmd(data, buffer, args):

    if not args:
        w.command('', '/help %s' %SCRIPT_COMMAND)
        return w.WEECHAT_RC_OK

    linfolist = w.infolist_get('logger_buffer', '', '')
    logfilename = ''
    log_enabled = False
    while w.infolist_next(linfolist):
        bpointer = w.infolist_pointer(linfolist, 'buffer')
        if bpointer == buffer:
            logfilename = w.infolist_string(linfolist, 'log_filename')
            log_enabled = w.infolist_integer(linfolist, 'log_enabled')
            break
    w.infolist_free(linfolist)


    matcher = re.compile(args, re.IGNORECASE)
    matching_lines = []

    if log_enabled:
        with file(logfilename, 'r') as f:
            for line in f:
                if matcher.search(line):
                    matching_lines.append(line.split('\t'))
    else:
        matching_lines = find_infolist_matching_lines(buffer, matcher)


    if not matching_lines:
        matching_lines = (('', '', 'No matches.'),)
    print_buffer(matching_lines)

    w.buffer_set(search_buffer, "display", "1")

    return w.WEECHAT_RC_OK


