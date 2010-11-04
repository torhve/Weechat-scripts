# -*- coding: utf-8 -*-
###
# Copyright (c) 2010 by xt <xt@bash.no>
# License: GPL3
#
#
#
#   Usage scenarios:
#
#   * Remote control weechat from a jabber account (from phone for example)
#       Requires you to send commands starting with a /
#   * Reply to messages sent via away_action
#       Requires away_action.py installed, will send input to the last buffer away_action recieved a
#       message from
#       
#
#   History:
#   2010-11-04
#   version 0.1: initial release
#
###

SCRIPT_NAME    = "proxy"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Run commands recieved in a configurable buffer"

### Default Settings ###
settings = {
        'buffer': 'jabber.gtalk.otheraccount@otherserver.com', # Buffer to listen for commands
}


try:
    import weechat
    w = weechat
    WEECHAT_RC_OK = weechat.WEECHAT_RC_OK
    import_ok = True
except:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://www.weechat.org/"
    import_ok = False

def proxy_cb(data, buffer, time, tags, display, hilight, prefix, msg):


    if msg.startswith('/'):
        w.command('', msg)
    else:
        buffer = w.info_get('away_action_buffer', '')
        if buffer:
            w.command(buffer, msg)
    return WEECHAT_RC_OK

def conf_update(*args):
    if w.config_get_plugin('buffer'):
        buffer = w.buffer_search('', w.config_get_plugin('buffer'))
        if buffer:
            weechat.hook_print(buffer, '', '', 1, 'proxy_cb', '')
    return WEECHAT_RC_OK

if __name__ == '__main__' and import_ok and \
        weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC,
        '', ''):


    for opt, val in settings.iteritems():
        if not weechat.config_is_set_plugin(opt):
            weechat.config_set_plugin(opt, val)

    weechat.hook_config('plugins.var.python.%s' %SCRIPT_NAME, 'conf_update', '')
    conf_update() # To init hook


# vim:set shiftwidth=4 tabstop=4 softtabstop=4 expandtab textwidth=100:
