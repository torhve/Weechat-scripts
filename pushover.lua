-- Copyright 2013 Tor Hveem <tor@bash.no>
--
-- This program is free software: you can redistribute it and/or modify
-- it under the terms of the GNU General Public License as published by
-- the Free Software Foundation, either version 3 of the License, or
-- (at your option) any later version.
--
-- This program is distributed in the hope that it will be useful,
-- but WITHOUT ANY WARRANTY; without even the implied warranty of
-- MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
-- GNU General Public License for more details.
--
-- You should have received a copy of the GNU General Public License
-- along with this program.  If not, see <http://www.gnu.org/licenses/>.
--


--[[


To use this script you must register for an account at <https://pushover.net/>
Then you must register an app there to get the token.

Next you must configure the script:

/set plugins.var.lua.pushover.user your user token here
/set plugins.var.lua.pushover.token your application token here

Then script should send messages if you are away and receive highlights or
private messages.


--]]

SCRIPT_NAME     = "pushover"
SCRIPT_AUTHOR   = "Tor Hveem <tor@bash.no>"
SCRIPT_VERSION  = "1"
SCRIPT_LICENSE  = "GPL3"
SCRIPT_DESC     = "Send push notifications from weechat"

local w = weechat

p_config = {
    token   = '',
    user    = '',
}

p_hook_process = nil

-- printf function
function printf(buffer, fmt, ...)
    w.print(buffer, string.format(fmt, unpack(arg)))
end

function pushover_unload()
    return w.WEECHAT_RC_OK
end

function p_process_cb(data, command, rc, stdout, stderr)
    if tonumber(rc) >= 0 then
        p_hook_process = nil
    end
end

function get_nick(s)
    local prefix = w.config_string(w.config_get('irc.look.nick_prefix'))
    local suffix = w.config_string(w.config_get('irc.look.nick_suffix'))
    s = s:gsub('^'..prefix, '')
    s = s:gsub(suffix..'$', '')
    s = s:gsub('^[~%+@!]*', '')
    return s
end

function pushover_check(data, buffer, time, tags, display, hilight, prefix, msg)
    if w.buffer_get_string(buffer, 'localvar_away') == '' then return w.WEECHAT_RC_OK end

    local token = w.config_get_plugin('token')
    local user = w.config_get_plugin('user')

    if token == '' or user == '' then
        return w.WEECHAT_RC_OK
    end

    if (hilight == '1' or string.find(tags, 'notify_private')) and display == '1' then
        local channel = w.buffer_get_string(buffer, 'short_name')
        local url = 'https://api.pushover.net/1/messages.json'
        local nick = get_nick(prefix)
        local message = '<'..nick..'>'.. ' ' .. msg
        local options = {
            postfields = 'token='..token..'&user='..user..'&title='..channel..'&message='..message
        }
        p_hook_process = w.hook_process_hashtable('url:'..url, options, 10 * 1000, 'p_process_cb', '')
    end
end


function p_init()
    w.register(
        SCRIPT_NAME,
        SCRIPT_AUTHOR,
        SCRIPT_VERSION,
        SCRIPT_LICENSE,
        SCRIPT_DESC,
        "pushover_unload", ""
    )
    for opt, val in pairs(p_config) do
        if w.config_is_set_plugin(opt) == 0 then
            w.config_set_plugin(opt, val)
        end
    end
    w.hook_print('', '', '', 1, 'pushover_check', '')
end

-- Initialize the script
p_init()
