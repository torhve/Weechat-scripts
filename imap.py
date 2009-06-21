# -*- coding: utf-8 -*-
# Copyright (c) 2009 by xt <xt@bash.no>
# (this script requires WeeChat 0.3.0 or newer)
#
# History:
#
# 2009-06-18, xt <xt@bash.no>
#   version 0.1: initial release.
#
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
'''  
Usage: put [imap] in your status bar items.  (Or any other bar to your liking)
"/set weechat.bar.status.items".

Also /imap for a crude imap client.

Keybindings are :
meta-r for mark as read
meta-d for delete
meta-f for fetch (read)

right arrow for next folder
left arrow for previous folder

up arrow for previous message
down arrow for next message
'''

import weechat as w
import time
from datetime import datetime
import imaplib as i
import re
from email.Header import decode_header
from email import message_from_string

SCRIPT_NAME    = "imap"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Bar item with unread imap messages count"
SCRIPT_COMMAND = SCRIPT_NAME

# script options
settings = {
    "username"          : '',
    "password"          : '',
    "hostname"          : '',
    "port"              : '993',
    'message'           : 'Mail: ',
    'message_color'     : 'default',
    'count_color'       : 'default',
    'interval'          : '5',
    'short_name'        : 'on',
    'time_format'       : '%H:%M',
}

imap = False
imap_buffer = False

active_folder_line = 0
active_folder_name = ''

active_message_line = 0
active_message_uid = 0

cached_folder_list = []

class Imap(object):

    iRe = re.compile("UNSEEN (\d+)")
    conn = False

    def __init__(self):
        username = w.config_get_plugin('username')
        password = w.config_get_plugin('password')
        hostname = w.config_get_plugin('hostname')
        port = int(w.config_get_plugin('port'))

        if username and password and hostname and port:
             M = i.IMAP4_SSL(hostname, port)
             M.login(username, password)
             self.conn = M

    def unreadCount(self, mailbox='INBOX'):
        unreadCount = int(self.iRe.search(self.conn.status(mailbox, "(UNSEEN)")[1][0]).group(1))
        return unreadCount

    def list(self):
        # only subscribed folders
        status, flist = self.conn.lsub()
        if status == 'OK':
            return flist

    def logout(self):
        try:
            self.conn.close()
        except Exception, e:
            self.conn.logout()

    def messages(self, mailbox='INBOX'):
        self.conn.select(mailbox, readonly=True)
        return self.conn.search('UTF-8', 'UNSEEN')

    def decode_helper(self, headerpart):
        retur = ''
        headerbits = decode_header(headerpart)
        for item in headerbits:
            header, c = item
            if c:
                header = header.decode(c)
            retur += header
        return retur.strip().encode('UTF-8', 'replace')

    def delete(self, mailbox, uid):
        ''' Mark a message as deleted given mailbox and uid.
            Also expunge the box.
        '''

        self.conn.select(mailbox)
        self.conn.store(uid, '+FLAGS', '\\Deleted')
        self.conn.expunge()

    def mark_read(self, mailbox, uid):
        ''' Mark a message as seen given mailbox and uid'''

        self.conn.select(mailbox)
        self.conn.store(uid, '+FLAGS', '\\Seen')

    def fetch_num(self, mailbox, uid, readonly=True):
        ''' Fetch a message as seen given mailbox and uid'''

        self.conn.select(mailbox, readonly)
        typ, data = self.conn.fetch(active_message_uid, '(RFC822)')
        data = data[0] # only one message is returned
        meta, mail = data[0], data[1]
        
        message = message_from_string(mail)


        return message

def imap_cb(*kwargs):
    ''' Callback for the bar item with unread count '''

    imap = Imap()
    unreadCount = imap.unreadCount()
    imap.logout()

    if not unreadCount == 0:
        return '%s%s%s%s%s' % (\
             w.color(w.config_get_plugin('message_color')),
             w.config_get_plugin('message'),
             w.color(w.config_get_plugin('count_color')),
             unreadCount,
             w.color('reset'))
    return ''

def imap_update(*kwargs):
    w.bar_item_update('imap')

    return w.WEECHAT_RC_OK

def buffer_input(data, buffer, string):

    global cached_folder_list, active_folder_line

    for i, folder in enumerate(cached_folder_list):
        if string in folder:
            active_folder_line = i
            w.bar_item_update('imap_folders')
            

    return w.WEECHAT_RC_OK

def buffer_close(*kwargs):
    global imap_buffer
    imap_buffer =  None
    return w.WEECHAT_RC_OK

def buffer_create():
    ''' create imap buffer '''
    global imap_buffer

    imap_buffer = w.buffer_search('python', SCRIPT_COMMAND)
    if not imap_buffer:
        imap_buffer = w.buffer_new(SCRIPT_COMMAND, "buffer_input", "", "buffer_close", "")
    w.buffer_set(imap_buffer, "time_for_each_line", "0")
    w.buffer_set(imap_buffer, "nicklist", "0")
    w.buffer_set(imap_buffer, "title", "imap")
    #w.buffer_set(imap_buffer, "type", "free")
    w.buffer_set(imap_buffer, "localvar_set_no_log", "1")
    w.buffer_set(imap_buffer, 'key_bind_meta2-A', '/%s message_up' %SCRIPT_COMMAND)
    w.buffer_set(imap_buffer, 'key_bind_meta2-B', '/%s message_down' %SCRIPT_COMMAND)
    w.buffer_set(imap_buffer, 'key_bind_meta2-D', '/%s folder_up' %SCRIPT_COMMAND)
    w.buffer_set(imap_buffer, 'key_bind_meta2-C', '/%s folder_down' %SCRIPT_COMMAND)
    w.buffer_set(imap_buffer, 'key_bind_meta-f', '/%s message_fetch' %SCRIPT_COMMAND)
    w.buffer_set(imap_buffer, 'key_bind_meta-r', '/%s message_mark_read' %SCRIPT_COMMAND)
    w.buffer_set(imap_buffer, 'key_bind_meta-d', '/%s message_delete' %SCRIPT_COMMAND)

def irc_nick_find_color(nick, bgcolor='default'):

    color = 0
    for char in nick:
        color += ord(char)

    color %= w.config_integer(w.config_get("weechat.look.color_nicks_number"))
    color = w.config_get('weechat.color.chat_nick_color%02d' %(color+1))
    color = w.config_string(color)
    return '%s%s%s' %(w.color('%s,%s' %(color, bgcolor)), nick, w.color('reset'))

def print_message():
    ''' Print a single email to the buffer '''

    global imap_buffer, active_message_line, active_message_uid

    imap = Imap()
    mail = imap.fetch_num(active_folder_name, active_message_uid)
    imap.logout()

    w.buffer_clear(imap_buffer)
    w.prnt(imap_buffer, mail.get_payload())


def print_messages(mailbox='INBOX'):
    ''' Print all unread messages in a folder to buffer '''

    global imap_buffer, active_message_line, active_message_uid

    w.buffer_clear(imap_buffer)
    imap = Imap()

    typ, data = imap.messages(mailbox)
    if not typ == 'OK':
        print 'bad type returned'
        imap.logout()
        return

    y = 0
    for num in data[0].split():
        typ, data = imap.conn.fetch(num, '(FLAGS INTERNALDATE BODY[HEADER.FIELDS (SUBJECT FROM)])')
        data = data[0] # only one message is returned
        meta, headers = data[0], data[1]
        #flags = re.search(r'\(FLAGS \((?P<flags>.+)\) ', meta).groupdict()['flags']

        internaldate = datetime.fromtimestamp(time.mktime(i.Internaldate2tuple(meta)))
        internaldate = internaldate.strftime(w.config_get_plugin('time_format'))
        internaldate = internaldate.replace(':', '%s:%s' %
                (w.color(w.config_string(
                w.config_get('weechat.color.chat_time_delimiters'))),
                w.color('reset')))
        internaldate = internaldate.strip()
                
        sender = re.search(r'From: ?(?P<from>.+)\s', headers, re.I)
        if sender:
            sender = sender.groupdict()['from']

        subject = re.search(r'Subject: ?(?P<subject>.+)\s', headers, re.I)
        if subject:
            subject = subject.groupdict()['subject']


        sender = imap.decode_helper(sender)
        subject = imap.decode_helper(subject)

        bgcolor = 'default'
        if y == active_message_line:
            active_message_uid = num
            bgcolor = 'red'

        if ' ' in sender:
            sender = irc_nick_find_color(sender.split()[0].strip('"'))
        else:
            sender = irc_nick_find_color(sender)

        w.prnt(imap_buffer, '%s %s\t%s %s' % \
                (internaldate, sender, w.color('default,%s' %bgcolor), subject))
        y += 1
        if y == 25:
            break

    imap.logout()

def imap_cmd(data, buffer, args):
    ''' Callback for /imap command '''

    global active_folder_line, active_message_line, active_folder_name, active_message_uid

    if not args:
        buffer_create()
        #print_messages()
        w.bar_item_update('imap_folders')
        w.command('', '/bar show imap')
        w.hook_signal('buffer_switch', 'toggle_imap_bar', '')
        w.command('', '/buffer %s' %SCRIPT_COMMAND)
    if args == 'folder_down':
        active_folder_line += 1
        w.bar_item_update('imap_folders')
    if args == 'folder_up':
        if active_folder_line > 0:
            active_folder_line -= 1
            w.bar_item_update('imap_folders')
    if args == 'message_down':
        active_message_line += 1
        print_messages(active_folder_name)
    if args == 'message_up':
        if active_message_line > 0:
            active_message_line -= 1
            print_messages(active_folder_name)
    if args == 'message_mark_read':
        if active_message_uid:
            imap = Imap()
            imap.mark_read(active_folder_name, active_message_uid)
            imap.logout()
            w.bar_item_update('imap_folders')
    if args == 'message_delete':
        if active_message_uid:
            imap = Imap()
            imap.delete(active_folder_name, active_message_uid)
            imap.logout()
            w.bar_item_update('imap_folders')
    if args == 'message_fetch':
        if active_message_uid:
            print_message()
    return w.WEECHAT_RC_OK


def create_folder_cache():
    global cached_folder_list

    imap = Imap()

    for folder in imap.list():
        name = ' '.join(folder.split()[2:])
        name = name.strip('"')
        cached_folder_list.append(name)

    cached_folder_list.sort()
    imap.logout()
    
def imap_folders_item_cb(data, item, window):
    ''' Callback that prints iamp folders on the imap bar '''

    global active_folder_line, active_folder_name, active_message_uid, active_message_line

    active_message_uid = 0
    active_message_line = 0

    active_folder_has_unread_messages = False

    imap = Imap()

    result = ''

    for linenr, folder in enumerate(imap.list()):
        name = ' '.join(folder.split()[2:])
        name = name.strip('"')
        unreadCount = imap.unreadCount(name)
        if unreadCount == 0:
            unreadCount = ''
        if unreadCount > 0:
            unreadCount = '%s%3s%s ' % (w.color('cyan'), unreadCount, w.color('reset'))

        bgcolor = 'default'
        fgcolor = 'yellow'
        if linenr == active_folder_line:
           bgcolor = 'red'
           active_folder_name = name
           if unreadCount:
               if unreadCount > 0:
                   active_folder_has_unread_messages = True


        if w.config_get_plugin('short_name') == 'on' and '.' in name:
            name = '.'.join(name.split('.')[1:])
        result += '%3s%s%s\n' % (unreadCount, w.color('%s,%s' %(fgcolor, bgcolor)), name)

    imap.logout()


    if active_folder_has_unread_messages:
        print_messages(active_folder_name)
    return result

def toggle_imap_bar(data, signal, signaldata):
    ''' cb for signal buffer_switch '''

    global imap_buffer

    if w.current_buffer() == imap_buffer:
        w.command('', '/bar show imap')
    else:
        w.command('', '/bar hide imap')

    w.unhook('buffer_switch')

    return w.WEECHAT_RC_OK


def unload_cb(*kwargs):
    ''' Callback on script unload '''

    w.command('', '/bar del imap')

    return w.WEECHAT_RC_OK


if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
        SCRIPT_DESC, 'unload_cb', ''):
    for option, default_value in settings.iteritems():
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, default_value)


    w.bar_item_new('imap', 'imap_cb', '')
    w.hook_timer(\
            int(w.config_get_plugin('interval'))*1000*60,
            0,
            0,
            'imap_update',
            '')

    w.hook_command(SCRIPT_COMMAND,
                             "imap client",
                             "[]",
                             "                                    \n",
                             "",
                             "imap_cmd", "")
    w.bar_item_new("imap_folders", "imap_folders_item_cb", "");
    w.bar_new("imap", "on", "0", "root", "", "right", "horizontal",
                    "vertical", "0", "0", "default", "default", "default", "1",
                    "imap_folders")

    create_folder_cache()
