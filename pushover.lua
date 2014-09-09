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

By default the script sends messages if you are away and receive highlights or
private messages.

--]]

SCRIPT_NAME     = "pushover"
SCRIPT_AUTHOR   = "Tor Hveem <tor@bash.no>"
SCRIPT_VERSION  = "3"
SCRIPT_LICENSE  = "GPL3"
SCRIPT_DESC     = "Send push notifications from weechat"

local w = weechat

local p_config = {
    token   = 'Your application token',
    user    = 'Your user token',
    ignore_nicks = 'Comma separated list of nicks to ignore',
    ignore_buffers = 'Comma separated list of buffers to ignore',
    ignore_messages = 'Comma separated list of message parts that will ignore the message',
    only_when_away = 'Only send messages when away. String with values either on or off',
    idle_timeout = 'Start sending messages after N seconds of inactivity',
}
local p_config_defaults = {
    token   = '',
    user    = '',
    ignore_nicks = '',
    ignore_buffers = '',
    ignore_messages = '',
    only_when_away = 'on',
    idle_timeout = 0,
}

-- printf function
function printf(buffer, fmt, ...)
    w.print(buffer, string.format(fmt, unpack(arg)))
end

function p_process_cb(data, command, rc, stdout, stderr)
    return w.WEECHAT_RC_OK
end

function get_nick(s)
    local prefix = w.config_string(w.config_get('irc.look.nick_prefix'))
    local suffix = w.config_string(w.config_get('irc.look.nick_suffix'))
    s = s:gsub('^'..prefix, '')
    s = s:gsub(suffix..'$', '')
    s = s:gsub('^[~%+@!]*', '')
    return s
end

local outstanding_messages = {}
local last_inactivity = 0
local check_interval = 10

function pushover_send_queued_messages(data, remaining_calls)
   local timeout = tonumber(w.config_get_plugin('idle_timeout'))
   local inactivity = tonumber(w.info_get("inactivity", ""))
   if inactivity < last_inactivity + check_interval then
      -- either clock goes backwards or you've done something, clear the queue
      outstanding_messages = {}
   end
   if timeout > 0 then
      if timeout < inactivity then
         local val = table.remove(outstanding_messages)
         while val do
            w.hook_process_hashtable(value.url, value.options, 10 * 1000, 'p_process_cb', '')
            val = table.remove(outstanding_messages)
         end
      end
   end
   last_inactivity = inactivity
   return w.WEECHAT_RC_OK
end

function pushover_check(data, buffer, time, tags, display, hilight, prefix, msg)
    if w.config_get_plugin('only_when_away') == 'on' then
        -- Check if buffer has away message set, if not return
        if w.buffer_get_string(buffer, 'localvar_away') == '' then return w.WEECHAT_RC_OK end
    end

    local token = w.config_get_plugin('token')
    local user = w.config_get_plugin('user')

    if token == '' or user == '' then
        return w.WEECHAT_RC_OK
    end

    -- We need highligt or private message, and not ignored by anything
    if (hilight == 1 or string.find(tags, 'notify_private')) and display == 1 then
        local channel = w.buffer_get_string(buffer, 'short_name')
        local nick = get_nick(prefix)

        -- Check for nick ignores
        for ignore in w.config_get_plugin('ignore_nicks'):gmatch('[^,]+') do
            if string.find(nick, ignore) then return w.WEECHAT_RC_OK end
        end
        -- Check for buffer ignores
        for ignore in w.config_get_plugin('ignore_buffers'):gmatch('[^,]+') do
            if string.find(channel, ignore) then return w.WEECHAT_RC_OK end
        end
        -- Check for msg ignores
        for ignore in w.config_get_plugin('ignore_messages'):gmatch('[^,]+') do
            if string.find(msg, ignore) then return w.WEECHAT_RC_OK end
        end

        local message = '<'..nick..'>'.. ' ' .. msg
        local options = {
            postfields = 'token='..token..'&user='..user..'&title='..channel..'&message='..message
        }
        local url = 'https://api.pushover.net/1/messages.json'

        local timeout = tonumber(w.config_get_plugin('idle_timeout'))
        if timeout > 0 then
           if timeout > tonumber(w.info_get("inactivity", "")) then
              table.insert(outstanding_messages, { ["url"] = 'url:'..url, ["options"] = options })
              return w.WEECHAT_RC_OK
           end
        end
        p_hook_process = w.hook_process_hashtable('url:'..url, options, 10 * 1000, 'p_process_cb', '')

    end
    return w.WEECHAT_RC_OK
end


function p_init()
    if w.register(
        SCRIPT_NAME,
        SCRIPT_AUTHOR,
        SCRIPT_VERSION,
        SCRIPT_LICENSE,
        SCRIPT_DESC,
        '', 
        '') then
        for opt, val in pairs(p_config) do
            if w.config_is_set_plugin(opt) == 0 then
                w.config_set_plugin(opt, p_config_defaults[opt])
            end
            w.config_set_desc_plugin(opt, val)
        end
        -- Hook on every message printed
        w.hook_print('', '', '', 1, 'pushover_check', '')
        w.hook_timer(1000*check_interval, 0, 0, 'pushover_send_queued_messages', '')
    end
end

-- Initialize the script
p_init()
