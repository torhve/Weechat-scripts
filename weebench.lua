-- Copyright 2013 xt <xt@bash.no>
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

This script will 
    Changelog:
        version 1, 2013-10-24, xt
            * initial version
--]]

require'os'

SCRIPT_NAME     = "weebench"
SCRIPT_AUTHOR   = "xt <xt@bash.no>"
SCRIPT_VERSION  = "1"
SCRIPT_LICENSE  = "GPL3"
SCRIPT_DESC     = "Benchmark"

local w = weechat

function buffer_input_cb(data, buffer, input_data)
    if input_data == "q" or input_data == "Q" then
        w.buffer_close(buffer)
    end
    return w.WEECHAT_RC_OK
end

function buffer_close_cb(data, buffer)
    return w.WEECHAT_RC_OK
end

function fill_lines(buffer, count)
    for i=0, count do
        w.print_date_tags(buffer, 0, "notify_message,no_log",
            string.format('I am now printing line number %s', i))
    end
end

function line_print_cb(data, buffer, time, tags, display, hilight, prefix, msg)
    return w.WEECHAT_RC_OK
end

function find_all_lines_matching(buffer, substr)
    local matches = {}
    lines = w.hdata_pointer(w.hdata_get('buffer'), buffer, 'own_lines')
    line = w.hdata_pointer(w.hdata_get('lines'), lines, 'first_line')
    hdata_line = weechat.hdata_get('line')
    hdata_line_data = weechat.hdata_get('line_data')
    while #line > 0 do
        data = w.hdata_pointer(hdata_line, line, 'data')
        message = w.hdata_string(hdata_line_data, data, 'message')
        if string.find(message, substr) then
            table.insert(matches, message)
        end
        line = w.hdata_move(hdata_line, line, 1)
    end
    return matches
end

function shutdown(...)
    buffer = w.buffer_search("lua", "weebench")
    w.buffer_close(buffer)
    return w.WEECHAT_RC_OK
end

if w.register(
    SCRIPT_NAME,
    SCRIPT_AUTHOR,
    SCRIPT_VERSION,
    SCRIPT_LICENSE,
    SCRIPT_DESC,
    'shutdown', 
    '') then

    local now = os.clock()

    w.print('','Starting benchmark')

    buffer = w.buffer_search("lua", "weebench")

    if buffer == "" then
        --create buffer
        buffer = w.buffer_new("weebench", "buffer_input_cb", "", "buffer_close_cb", "")
    end

    --set title
    w.buffer_set(buffer, "title", "WeeChat benchmark.")

    --disable logging, by setting local variable "no_log" to "1"
    w.buffer_set(buffer, "localvar_set_no_log", "1")

    local matches = 0

    -- Hook on every message printed in benchmark buffer
    -- this hook does not do anything for now
    w.hook_print(buffer, '', '', 1, 'line_print_cb', '')

    -- default history is 4096 lines so only add that in one go
    local count = 4096
    -- run the test 100 times, it takes roughly 30 seconds on the script author's slow CPU
    for i=0,100 do
        fill_lines(buffer, count)
        matches = matches + #find_all_lines_matching(buffer, 'line')
    end
    
    w.print('', string.format('Found %s lines matching.', matches))

    local endt = os.clock() 

    shutdown()

    w.print('',string.format('Benchmark: %.2f', endt-now))
end
