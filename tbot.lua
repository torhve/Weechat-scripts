-- Copyright 2012 Tor Hveem <tor@bash.no>
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

SCRIPT_NAME		= "tbot"
SCRIPT_AUTHOR	= "Tor Hveem <tor@bash.no>"
SCRIPT_VERSION	= "1"
SCRIPT_LICENSE	= "GPL3"
SCRIPT_DESC		= "A bot to manage torrent filters"

local w = weechat

tbot_config = {
    enable  = true,
    hdtrue  = '',
    hdfalse = '',
    sdtrue  = '',
    sdfalse = '',
}

tbot_config_file = nil

-- printf function
function printf(buffer, fmt, ...)
	w.print(buffer, string.format(fmt, unpack(arg)))
end

function string:split(sSeparator, nMax, bRegexp)
    -- Function lifted from http://lua-users.org/wiki/SplitJoin
    assert(sSeparator ~= '')
    assert(nMax == nil or nMax >= 1)

    local aRecord = {}

    if self:len() > 0 then
        local bPlain = not bRegexp
        nMax = nMax or -1

        local nField=1 nStart=1
        local nFirst,nLast = self:find(sSeparator, nStart, bPlain)
        while nFirst and nMax ~= 0 do
            aRecord[nField] = self:sub(nStart, nFirst-1)
            nField = nField+1
            nStart = nLast+1
            nFirst,nLast = self:find(sSeparator, nStart, bPlain)
            nMax = nMax-1
        end
        aRecord[nField] = self:sub(nStart)
    end

    return aRecord
end


function tbot_list(data, buffer, time, tags, displayed, highlight, prefix, message)
    local patterns = w.config_string(tbot_config.hdtrue)
    -- Prettier
    patterns = patterns:split(',')
    table.sort(patterns, function (a, b)
      return string.lower(a) < string.lower(b)
    end)
    patterns = table.concat(patterns, ', ')
    w.command(buffer, "HD: " .. patterns)
    return w.WEECHAT_RC_OK
end


function tbot_add(data, buffer, time, tags, displayed, highlight, prefix, message)
    -- Strip away the command '@tbot add'
    local new = string.sub(message, string.len('@tbot add ') + 1)
    local str = w.config_string(tbot_config.hdtrue)
    str = str .. ',' .. new
    -- Save the new config option
    w.config_option_set(tbot_config.hdtrue, str, 1)
    -- Display the new string
    return tbot_list(data, buffer, time, tags, displayed, highligh, prefix, message)
end

function tbot_remove(data, buffer, time, tags, displayed, highlight, prefix, message)
    -- Strip away the command '@tbot add'
    local removepattern = string.sub(message, string.len('@tbot remove ') + 1)
    local str = w.config_string(tbot_config.hdtrue)
    str, c = str:gsub(',' .. removepattern .. ',', ',')
    -- Save the new config option
    w.config_option_set(tbot_config.hdtrue, str, 1)
    -- Display the new string
    return tbot_list(data, buffer, time, tags, displayed, highligh, prefix, message)
end

function tbot_config_init()
    local structure = {
        general = {
         enable = {
            description = "Enable the bot",
            default = true
         }
      },
      patterns = {
         hdtrue = {
            description = "HD True patterns",
            default = ""
         },
         hdfalse = {
            description = "HD True patterns",
            default = ""
         },
         sdtrue = {
            description = "HD True patterns",
            default = ""
         },
         sdfalse = {
            description = "HD True patterns",
            default = ""
         },
     }
    }
    tbot_config_file = w.config_new('tbot', '', '')
    if tbot_config_file == '' then
        return
    end

    for section_name, section_options in pairs(structure) do
      local section = w.config_new_section(
         tbot_config_file, section_name,
         0, 0,
         "", "", "", "", "", "", "", "", "", "")

      if section == "" then
         w.config_free(tbot_config_file)
         return
      end

      for option, definition in pairs(section_options) do
         local lua_type = type(definition.default)

         if lua_type == "number" then
            tbot_config[option] =
               w.config_new_option(
                  tbot_config_file,
                  section,
                  option,
                  "integer",
                  definition.description,
                  "",
                  (definition.min and definition.min or 0),
                  (definition.max and definition.max or 0),
                  definition.default,
                  definition.default,
                  0,
                  "", "", "", "", "", "")
         elseif lua_type == "boolean" then
            local default = definition.default and "on" or "off"
            tbot_config[option] =
               w.config_new_option(
                  tbot_config_file,
                  section,
                  option,
                  "boolean",
                  definition.description,
                  "",
                  0,
                  0,
                  default,
                  default,
                  0,
                  "", "", "", "", "", "")
         elseif lua_type == "table" or lua_type == "string" then
            local default = definition.default
            if lua_type == "table" then
               default = table.concat(
                           definition.default,
                           (definition.separator and definition.separator or ","))
            end

            tbot_config[option] =
               w.config_new_option(
                  tbot_config_file,
                  section,
                  option,
                  "string",
                  definition.description,
                  "",
                  0,
                  0,
                  default,
                  default,
                  0,
                  "", "", "", "", "", "")
         end
      end
   end
end

function tbot_config_read()
    return w.config_read(tbot_config_file)
end

function tbot_config_write()
    return w.config_write(tbot_config_file)
end

function tbot_unload()
    tbot_config_write()
    return w.WEECHAT_RC_OK
end

function tbot_init()
    w.register(
        SCRIPT_NAME,
        SCRIPT_AUTHOR,
        SCRIPT_VERSION,
        SCRIPT_LICENSE,
        SCRIPT_DESC,
        "tbot_unload", ""
    )
    tbot_config_init()
    tbot_config_read()
   local enabled = w.config_boolean(tbot_config.enable)
   if enabled == 1 then
        -- Register bot commands
        w.hook_print("", "", "@tbot list",    1, "tbot_list", "")
        w.hook_print("", "", "@tbot add",     1, "tbot_add", "")
        w.hook_print("", "", "@tbot remove",  2, "tbot_remove", "")
   end
end

-- Initialize the script
tbot_init()



