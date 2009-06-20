# -*- coding: utf-8 -*-
#
#Copyright (c) 2009 by xt <xt@bash.no>
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
# Bar with URLs (easy click on long URLs)
# (this script requires WeeChat 0.3.0 or newer)
#
# History:
# 2009-06-19, xt <xt@bash.no>
#     version 0.1: initial
#

import weechat
w = weechat
import re
import urllib2

SCRIPT_NAME    = "spotify"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL"
SCRIPT_DESC    = "Look up spotify urls"

settings = {
    "buffers"        : 'xt`,',     # comma separated list of buffers
    "gateway"        : '',         # http spotify gw address
}


spotify_track_res = ( re.compile(r'spotify:track:(?P<track_id>\w{22})'),
            re.compile(r'http://open.spotify.com/track/(?P<track_id>\w{22})') )


cache = {}

spotify_hook_process = ''
buffer_name = ''


def get_buffer_name(bufferp):
    bufferd = weechat.buffer_get_string(bufferp, "name")
    return bufferd

def printReply(buffer_name, reply):
    splits = buffer_name.split('.')
    server = splits[0]
    buffer = '.'.join(splits[1:])
    w.command('', '/msg -server %s %s %s' %(server, buffer, reply))

def get_spotify_ids(s):
    for r in spotify_track_res:
        for track in r.findall(s):
            yield "spotify:track:" + track


def spotify_print_cb(data, buffer, time, tags, displayed, highlight, prefix, message):

    global spotify_hook_process, buffer_name, cache

    msg_buffer_name = get_buffer_name(buffer)
    # Skip ignored buffers
    found = False
    for active_buffer in weechat.config_get_plugin('buffers').split(','):
        if active_buffer.lower() == msg_buffer_name.lower():
            found = True
            buffer_name = msg_buffer_name
            break

    if not found:
        return weechat.WEECHAT_RC_OK

       
    for spotify_id in get_spotify_ids(message):
        if spotify_id in cache:
            printReply(buffer_name, cache[spotify_id])
            return weechat.WEECHAT_RC_OK

        url = w.config_get_plugin('gateway') + spotify_id
        if spotify_hook_process != "":
            weechat.unhook(spotify_hook_process)
            spotify_hook_process = ""
        spotify_hook_process = weechat.hook_process(
            "python -c \"import urllib2; print urllib2.urlopen('" + url + "').read()\"",
            30 * 1000, "spotify_process_cb", "")

    return weechat.WEECHAT_RC_OK

def spotify_process_cb(data, command, rc, stdout, stderr):
    """ Callback reading HTML data from website. """

    global spotify_hook_process, buffer_name

    spotify_hook_process = ""

    #if int(rc) >= 0:
    reply = stdout
    spotify_id = reply[:36]
    reply = reply[37:] # strip spotify url
    reply = reply.strip()
    if reply:
        cache[spotify_id] = reply
        printReply(buffer_name, reply)

    return weechat.WEECHAT_RC_OK




if __name__ == "__main__":
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                        SCRIPT_DESC, "", ""):
        # Set default settings
        for option, default_value in settings.iteritems():
            if not weechat.config_is_set_plugin(option):
                weechat.config_set_plugin(option, default_value)

        weechat.hook_print("", "", "spotify:", 1, "spotify_print_cb", "")
