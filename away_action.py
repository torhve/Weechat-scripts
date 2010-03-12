# -*- coding: utf-8 -*-
###
# Copyright (c) 2010 by xt <xt@bash.no>
# Parts from inotify.py by Elián Hanisch <lambdae2@gmail.com>
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
###

###
#
#
#   History:
#   2010-03-11
#   version 0.1: release
#
###

SCRIPT_NAME    = "away_action"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Run command on highlight when away"

### Default Settings ###
settings = {
'ignore_channel' : '',
'ignore_nick'    : '',
'ignore_text'    : '',
'command'        : '/msg -server minbif tor'
}

ignore_nick, ignore_text, ignore_channel = (), (), ()
try:
    import weechat
    w = weechat
    WEECHAT_RC_OK = weechat.WEECHAT_RC_OK
    import_ok = True
except:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://www.weechat.org/"
    import_ok = False

class Ignores(object):
    def __init__(self, ignore_type):
        self.ignore_type = ignore_type
        self.ignores = []
        self.exceptions = []
        self._get_ignores()

    def _get_ignores(self):
        assert self.ignore_type is not None
        ignores = weechat.config_get_plugin(self.ignore_type).split(',')
        ignores = [ s.lower() for s in ignores if s ]
        self.ignores = [ s for s in ignores if s[0] != '!' ]
        self.exceptions = [ s[1:] for s in ignores if s[0] == '!' ]

    def __contains__(self, s):
        s = s.lower()
        for p in self.ignores:
            if fnmatch(s, p):
                for e in self.exceptions:
                    if fnmatch(s, e):
                        return False
                return True
        return False

config_string = lambda s : weechat.config_string(weechat.config_get(s))
def get_nick(s):
    """Strip nickmodes and prefix, suffix."""
    if not s: return ''
    # prefix and suffix
    prefix = config_string('irc.look.nick_prefix')
    suffix = config_string('irc.look.nick_suffix')
    if s[0] == prefix:
        s = s[1:]
    if s[-1] == suffix:
        s = s[:-1]
    # nick mode
    modes = '~+@!%'
    s = s.lstrip(modes)
    return s

def away_cb(data, buffer, time, tags, display, hilight, prefix, msg):

    global ignore_nick, ignore_text, ignore_channel
    #print tags, display, hilight, prefix, 'msg_len:%s' %len(msg)

    if not w.buffer_get_string(buffer, 'localvar_away'):
        return WEECHAT_RC_OK
    if (hilight == '1' or 'notify_private' in tags) and display == '1':
        channel = weechat.buffer_get_string(buffer, 'short_name')
        prefix = get_nick(prefix)
        if prefix not in ignore_nick \
                and channel not in ignore_channel \
                and msg not in ignore_text:
            w.command('', '%s %s %s' %(weechat.config_get_plugin('command'), prefix, msg))
    return WEECHAT_RC_OK

def ignore_update(*args):
    ignore_channel._get_ignores()
    ignore_nick._get_ignores()
    ignore_text._get_ignores()
    return WEECHAT_RC_OK

if __name__ == '__main__' and import_ok and \
        weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC,
        '', ''):


    for opt, val in settings.iteritems():
        if not weechat.config_is_set_plugin(opt):
            weechat.config_set_plugin(opt, val)

    weechat.hook_config('plugins.var.python.%s.ignore_*' %SCRIPT_NAME, 'ignore_update', '')

    weechat.hook_print('', '', '', 1, 'away_cb', '')


# vim:set shiftwidth=4 tabstop=4 softtabstop=4 expandtab textwidth=100:
