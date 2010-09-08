# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 by xt <xt@bash.no>
# Based on vdm.py script by FlashCode
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
#
# Huge WARNING: This script can block weechat for as long as requests
# to twitter lasts.  Use at own risk.

#
# (this script requires WeeChat 0.3.0 or newer)
#
#
# History:
# 2010-09-08, xt
#   - OAuth, switch to tweepy, add "saved search"
# 2010-03-24, xt <xt@bash.no>:
#     add nicklist
# -
#     version 0.1: initial release
#

import weechat, tweepy
w = weechat
import time, sys, socket, urllib2
#reload(sys)

#sys.setdefaultencoding('UTF-8')

# set short timeout to try to minize blocking issues
SOCKETTIMEOUT = 5
socket.setdefaulttimeout(SOCKETTIMEOUT)


SCRIPT_NAME    = "tweechat"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.4"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Microblog client for weechat"
SCRIPT_COMMAND = 'twitter'

# script options
settings = {
        'username': '',
        'password': '',
        'token_key': '',
        'token_secret': '',
        'refresh_interval': '300', #in seconds
        'loggging': 'on', # log to file using standard weechat logging
}


twitter_buffer           = ""
twitter_list             = []
twitter_lastid           = 0
twitter_search_lastid    = 0
twitter_current_search   = ''
api                      = None


failwhale = '''     v  v        v
     |  |  v     |  v
     | .-, |     |  |
  .--./ /  |  _.---.|
   '-. (__..-"       \\
      \\          a    |           %s
       ',.__.   ,__.-'/
         '--/_.'----'`'''



if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                    SCRIPT_DESC, "", ""):
    w.hook_command(SCRIPT_COMMAND,
                         "Display twitters",
                         " ",
                         "Type tweet Hello from weechat! in twitter buffer to tweet from weechat\n"
                         "Type search #tagname in twitter buffer to add a saved search\n"
                         'Type follow screen_name to follow a user\n'
                         'Type unfollow screen_name to stop following a user',
                         "", "twitter_cmd", "")
    for option, default_value in settings.iteritems():
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, default_value)

    w.hook_signal('input_text_changed', 'title_cb', '')
    w.hook_timer(int(w.config_get_plugin('refresh_interval'))*1000,
            0,
            0,
            'twitter_sched_cb',
            '')

def print_line(line, timestamp=int(time.time())):
    ''' Print a line in the twitter buffer '''

    global twitter_buffer

    #w.buffer_set(twitter_buffer, "unread", "1")
    w.prnt_date_tags(twitter_buffer, timestamp,"notify_message", line)

def get_nick_color(nick):
    if nick != w.config_get_plugin('username'):
        nick_color = w.info_get('irc_nick_color', nick)
    else:
        nick_color = w.color(w.config_string(w.config_get('weechat.color.chat_nick_self')))
    return nick_color


def twitter_display(twitters):
    """ Display twitters in buffer. """
    separator = "\t"
    for status in reversed(twitters):
        nick = unicode(status.user.screen_name)
        nick_color = get_nick_color(nick)


        text = unicode(status.text)
        print_line( "%s%s%s%s" % (nick_color, nick, separator, text),
                time.mktime(status.created_at.timetuple()))

def search_display(twitters):
    """ Display twitters in buffer. """
    separator = "\t"
    for status in reversed(twitters):
        nick = unicode(status.from_user)
        nick_color = get_nick_color(nick)

        text = unicode(status.text)
        print_line( "%s%s%s%s" % (nick_color, nick, separator, text),
                time.mktime(status.created_at.timetuple()))


def title_cb(*kwargs):
    ''' Callback used to set title, used to update char counter '''
    global twitter_buffer

    if not weechat.current_buffer() == twitter_buffer:
        return w.WEECHAT_RC_OK
    title = False
    input_content = w.buffer_get_string(twitter_buffer, "input")
    if input_content.startswith('tweet '):
        length = len(input_content) - 6
        title = 'Tweet char counter: %s' %length
    set_title(title)

    return w.WEECHAT_RC_OK

def set_title(new_title=False):
    global twitter_buffer

    title = 'Get help with /help twitter'
    if new_title:
        title = new_title

    w.buffer_set(twitter_buffer, "title", SCRIPT_NAME + " " + SCRIPT_VERSION + " " + title)

def twitter_buffer_create():
    """ Create twitter buffer. """
    global twitter_buffer
    twitter_buffer = w.buffer_search("python", "twitter")
    if twitter_buffer == "":
        twitter_buffer = w.buffer_new("twitter",
                                        "twitter_buffer_input", "",
                                        "twitter_buffer_close", "")
    if twitter_buffer != "":
        set_title()
        w.buffer_set(twitter_buffer, "time_for_each_line", "1")

        # Configure logging
        if w.config_get_plugin('logging') == 'on':
            w.buffer_set(twitter_buffer, "localvar_set_server", "tweechat")
            w.buffer_set(twitter_buffer, "localvar_set_channel", "twitter")
        else:
            w.buffer_set(twitter_buffer, "localvar_set_no_log", "1")
        w.buffer_set(twitter_buffer, "localvar_set_nick", w.config_get_plugin('username'))
        w.buffer_set(twitter_buffer, "nicklist", "1")
        w.buffer_set(twitter_buffer, "nicklist_display_groups", "1")



def twitter_sched_cb(*kwargs):
    ''' Callback for scheduled twitter updates '''

    twitter_get()

    return w.WEECHAT_RC_OK


def twitter_get(args=None):
    """ Get some twitters  """
    global twitter_buffer, twitter_list, api, twitter_lastid, twitter_current_search, twitter_search_lastid
    # open buffer if needed
    if twitter_buffer == "":
        twitter_buffer_create()

    try:

        if not api:
            if not w.config_get_plugin('username'):
                w.prnt('', '%s: Error: No username set' %SCRIPT_COMMAND)
                return
            if not w.config_get_plugin('password'):
                w.prnt('', '%s: Error: No password set' %SCRIPT_COMMAND)
                return
            auth = tweepy.OAuthHandler('Nw9Drox04uc9WmKvU0t0Xw', 'C17Lb71BUmkcUPKm3stZVdNugt2wLigh69ns11X6c78')
            auth.set_access_token(w.config_get_plugin('token_key'), w.config_get_plugin('token_secret'))
            api = tweepy.API(auth)

            #  Populate friends into nicklist
            for user in api.friends(w.config_get_plugin('username')):
                w.nicklist_add_nick(twitter_buffer, "", user.screen_name, \
                        'bar_fg', '', '', 1)

        if twitter_lastid:
            twitters = api.home_timeline(since_id=twitter_lastid)
        else:
            twitters = api.home_timeline()

        if twitters:
            twitter_lastid = twitters[0].id
            twitter_display(twitters)

        if twitter_current_search:
            if twitter_search_lastid:
                search_results = api.search(twitter_current_search,since_id=twitter_search_lastid)
            else:
                search_results = api.search(twitter_current_search)
            if search_results:
                twitter_search_lastid = search_results[0].id
                search_display(search_results)
    except urllib2.URLError, u:
        if 'timed out' in str(u): # ignore timeouts, happens pretty often
            pass
        else:
            w.prnt(twitter_buffer, failwhale %'Error: %s' %u)
    #except Exception, e:
    #    w.prnt(twitter_buffer, failwhale %'Error: %s' %e)

def twitter_buffer_input(data, buffer, input_data):
    """ Read data from user in twitter buffer. """

    global api, twitter_current_search, twitter_search_lastid

    try:
        if input_data == "q" or input_data == "Q":
            w.buffer_close(buffer)
        elif input_data.startswith('tweet'):
            api.update_status(input_data[5:])
            twitter_get()
        elif input_data.startswith('follow'):
            user = input_data[len('follow')+1:]
            api.create_friendship(user)
            prefix_color = w.color(w.config_string(w.config_get('weechat.color.chat_prefix_join')))
            print_line('%s-->%s\tNow following %s' %(prefix_color, w.color('reset'), user))
        elif input_data.startswith('search'):
            query = input_data[len('search')+1:]
            twitter_current_search = query
            twitter_search_lastid = 0 # Reset search id
            twitter_get()
        elif input_data.startswith('unfollow'):
            user = input_data[len('unfollow')+1:]
            api.destroy_friendship(user)
            prefix_color = w.color(w.config_string(w.config_get('weechat.color.chat_prefix_quit')))
            print_line('%s<--%s\tNot following %s anymore' %(prefix_color, w.color('reset'), user))
    except Exception, e:
        w.prnt(twitter_buffer, failwhale %'Error: %s' %e)

    return w.WEECHAT_RC_OK

def twitter_buffer_close(data, buffer):
    """ User closed twitter buffer. Oh no, why? """
    global twitter_buffer
    w.nicklist_remove_all(twitter_buffer)
    twitter_buffer = ""
    return w.WEECHAT_RC_OK

def twitter_cmd(data, buffer, args):
    """ Callback for /twitter command. """
    if args != "":
        twitter_get(args)
    else:
        twitter_get("last")
    return w.WEECHAT_RC_OK


w.command('', '/twitter')
