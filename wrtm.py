#
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
# (this script requires WeeChat 0.3.0 or newer)
#
# History:
# 2009-06-22, xt <xt@bash.no>
#     version 0.1: initial release

import weechat as w
from rtm import createRTM
import datetime
import time

SCRIPT_NAME    = "wrtm"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "TODO"
SCRIPT_COMMAND = 'rtm'

settings = {
    "token"              : '',
    "update_interval"   : '5', #In minutes, must be int
}

rtm = False

#def lists_update(*kwargs):
#    ''' update the bar with the lists '''
#
#    w.bar_item_update('rtm_lists')
#    return w.WEECHAT_RC_OK

#def toggle_rtm_bar(data, signal, signaldata):
#    ''' cb for signal buffer_switch '''
#
#    global rtm_buffer
#
#    if w.current_buffer() == rtm_buffer:
#        w.command('', '/bar show rtm')
#    else:
#        w.command('', '/bar hide rtm')
#
#    w.unhook('buffer_switch')
#
#    return w.WEECHAT_RC_OK

def buffer_input(data, buffer, string):
    ''' Callback on rtm buffer input '''

    for list in rtm.list_names():
        if string.lower() == list.lower():
            rtm.active_list_name = list
            rtm.redraw()
            break

    return w.WEECHAT_RC_OK

def buffer_close(*kwargs):
    rtm.buffer = None
    return w.WEECHAT_RC_OK


def rtm_cmd(data, buffer, args):
    ''' Callback for /rtm command '''

    if not args:
        #lists_update()
        #w.command('', '/bar show %s' %SCRIPT_COMMAND)
        #w.hook_signal('buffer_switch', 'toggle_imap_bar', '')
        rtm.redraw()
        w.command('', '/buffer %s' %SCRIPT_COMMAND)

    elif args == 'list_left' or args == 'list_right':
        new_name = ''
        for i, name in enumerate(rtm.list_names()):
            if name == rtm.active_list_name:
                if args.endswith('left'):
                    new_name = rtm.list_names()[i-1]
                else:
                    new_name = rtm.list_names()[i+1]

        rtm.active_list_name = new_name
        rtm.redraw()


    return w.WEECHAT_RC_OK


class RTM(object):

    def __init__(self, token):
        self.token = token
        apik = 'e282189b97ed465ba34b5bc000543065'
        secret = 'b68702a7f207244c'
        if not token:
            raise ValueError('Error: Need token configured')
        else:
            self.rtm = createRTM(apik, secret, token)
            self._active_list_name = False
            self.active_task_id = 0
            self.lists  = {}
            self._list_names = []
            self.buffer_create()


    def list_names(self):
        ''' Return cached list of list names '''


        if not self.lists:
            rspLists = self.rtm.lists.getList()
            for list in rspLists.lists.list:
                self.lists[list.name] = list.id
                self._list_names.append(list.name)
        return self._list_names

    @property
    def active_list_name(self):
        if not self._active_list_name:
            default = self._default_list_name()
            self._active_list_name = default
        return self._active_list_name

    @active_list_name.setter
    def active_list_name(self, value):
        if value in self.list_names():
            self._active_list_name = value
        else:
            raise ValueError('Wrong list name')

    def _default_list_name(self):
        default_id = self.rtm.settings.getList().settings.defaultlist
        for name, id in self.lists.iteritems():
            if int(id) == int(default_id):
                return name

    def buffer_create(self):
        ''' create rtm buffer '''

        rtm_buffer = w.buffer_search('python', SCRIPT_COMMAND)
        if not rtm_buffer:
            rtm_buffer = w.buffer_new(SCRIPT_COMMAND, "buffer_input", "", "buffer_close", "")
        w.buffer_set(rtm_buffer, "time_for_each_line", "0")
        w.buffer_set(rtm_buffer, "nicklist", "0")
        w.buffer_set(rtm_buffer, "title", "Remember The Milk !")
        #w.buffer_set(rtm_buffer, "type", "free")
        w.buffer_set(rtm_buffer, "localvar_set_no_log", "1")
        w.buffer_set(rtm_buffer, 'key_bind_meta2-A', '/%s task_up' %SCRIPT_COMMAND)
        w.buffer_set(rtm_buffer, 'key_bind_meta2-B', '/%s task_down' %SCRIPT_COMMAND)
        w.buffer_set(rtm_buffer, 'key_bind_meta2-D', '/%s list_left' %SCRIPT_COMMAND)
        w.buffer_set(rtm_buffer, 'key_bind_meta2-C', '/%s list_right' %SCRIPT_COMMAND)

        self.buffer = rtm_buffer

    def update_title(self):
        result = ''

        for rlist in self.list_names():
            fgcolor = 'green'
            bgcolor = 'default'
            if rlist == self.active_list_name:
                bgcolor = 'red'
            result += '%s%s%s    ' % (w.color('%s,%s' %(fgcolor, bgcolor)), rlist, w.color('reset'))
        w.buffer_set(self.buffer, "title", result)
        return str(result)

    def print_tasks(self):

        w.buffer_clear(self.buffer)

        list_id = self.lists[self.active_list_name]
        rspTasks = self.rtm.tasks.getList(list_id=list_id, filter='status:incomplete')
        for task in reversed(rspTasks.tasks.list.taskseries):
            if not self.active_task_id:
                self.active_task_id = task.id

            priority = task.task.priority
            
            fgcolor = 'default'
            bgcolor = 'default'
            if priority == '3':
                fgcolor = 'green'
            elif priority == '2':
                fgcolor = 'cyan'
            elif priority == '1':
                fgcolor = 'yellow'
            elif priority == 'N':
                fgcolor = 'default'
            if int(task.id) == int(self.active_task_id):
                bgcolor = 'red'
            try:
                ttime = datetime.datetime.fromtimestamp(time.mktime(time.strptime(task.created, "%Y-%m-%dT%H:%M:%SZ")))
            except Exception, e:
                ttime = ''
                print task.created, e
           
            task_name = task.name.encode('UTF-8')
            task_name = '%s%s%s' %(w.color('%s,%s' %(fgcolor,bgcolor)), task_name, w.color('reset'))
            taskstr = '%s\t%s %s' %(ttime, '', task_name)
            w.prnt(self.buffer, taskstr)

    def redraw(self):
        self.update_title()
        self.print_tasks()


def update_interval_cb(*kwargs):
    global rtm
    rtm.redraw()

    return w.WEECHAT_RC_OK


if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
    for option, default_value in settings.iteritems():
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, default_value)


    token = w.config_get_plugin('token')
    rtm = RTM(token)

    w.hook_command(SCRIPT_COMMAND,
                             "weechat RTM interface",
                             "[]",
                             "\n",
                             "",
                             "rtm_cmd", "")
    w.command('', '/' + SCRIPT_COMMAND)
    update_interval = int(w.config_get_plugin('update_interval'))
    if update_interval > 0:
        w.hook_timer(\
            update_interval*1000*60,
            0,
            0,
            'update_interval_cb',
            '')
    #w.bar_item_new("rtm_lists", "rtm_lists_cb", "");
    #w.bar_new("rtm", "on", "2000", "window", "", "top", "horizontal",
    #                "horizontal", "0", "0", "default", "default", "default", "1",
    #                "rtm_lists")

