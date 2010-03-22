# -*- coding: utf-8 -*-
#
# Copyright (c) 2009-2010 by FlashCode <flashcode@flashtux.org>
# Copyright (c) 2010 by xt <xt@bash.no>
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
# Jabber/XMPP protocol for WeeChat.
# (this script requires WeeChat 0.3.0 (or newer) and xmpppy library)
#
# For help, see /help jabber
# Happy chat, enjoy :)
#
# History:
# 2010-03-17, xt <xt@bash.no>:
#     add autoreconnect option, autoreconnects on protocol error
# 2010-03-17, xt <xt@bash.no>:
#     add autoconnect option, add new command /jmsg with -server option
# 2009-02-22, FlashCode <flashcode@flashtux.org>:
#     first version (unofficial)
#

SCRIPT_NAME    = "jabber"
SCRIPT_AUTHOR  = "FlashCode <flashcode@flashtux.org>"
SCRIPT_VERSION = "0.1-dev-20100322"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Jabber/XMPP protocol for WeeChat"
SCRIPT_COMMAND = SCRIPT_NAME

import_ok = True

try:
    import weechat
except:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://www.weechat.org/"
    import_ok = False

try:
    import xmpp
except:
    print "Package python-xmpp (xmpppy) must be installed to use Jabber protocol."
    print "Get xmpppy with your package manager, or at this URL: http://xmpppy.sourceforge.net/"
    import_ok = False

# ==============================[ global vars ]===============================

jabber_servers = []
jabber_server_options = {
    "jid"          : { "type"         : "string",
                       "desc"         : "jabber id (user@server.tld)",
                       "min"          : 0,
                       "max"          : 0,
                       "string_values": "",
                       "default"      : "",
                       "value"        : "",
                       "check_cb"     : "",
                       "change_cb"    : "",
                       "delete_cb"    : "",
                       },
    "password"     : { "type"         : "string",
                       "desc"         : "password for jabber id on server",
                       "min"          : 0,
                       "max"          : 0,
                       "string_values": "",
                       "default"      : "",
                       "value"        : "",
                       "check_cb"     : "",
                       "change_cb"    : "",
                       "delete_cb"    : "",
                       },
    "autoconnect"  : { "type"         : "boolean",
                       "desc"         : "automatically connect to server when script is starting",
                       "min"          : 0,
                       "max"          : 0,
                       "string_values": "",
                       "default"      : "off",
                       "value"        : "off",
                       "check_cb"     : "",
                       "change_cb"    : "",
                       "delete_cb"    : "",
                       },
    "autoreconnect": { "type"         : "boolean",
                       "desc"         : "automatically reconnect to server when disconnected",
                       "min"          : 0,
                       "max"          : 0,
                       "string_values": "",
                       "default"      : "off",
                       "value"        : "off",
                       "check_cb"     : "",
                       "change_cb"    : "",
                       "delete_cb"    : "",
                       },
    }
jabber_config_file = None
jabber_config_section = {}
jabber_config_option = {}

# =================================[ config ]=================================

def jabber_config_init():
    """ Initialize config file: create sections and options in memory. """
    global jabber_config_file, jabber_config_section
    jabber_config_file = weechat.config_new("jabber", "jabber_config_reload_cb", "")
    if not jabber_config_file:
        return
    # look
    jabber_config_section["look"] = weechat.config_new_section(
        jabber_config_file, "look", 0, 0, "", "", "", "", "", "", "", "", "", "")
    if not jabber_config_section["look"]:
        weechat.config_free(jabber_config_file)
        return
    jabber_config_option["debug"] = weechat.config_new_option(
        jabber_config_file, jabber_config_section["look"],
        "debug", "boolean", "display debug messages", "", 0, 0,
        "off", "off", 0, "", "", "", "", "", "")
    # color
    jabber_config_section["color"] = weechat.config_new_section(
        jabber_config_file, "color", 0, 0, "", "", "", "", "", "", "", "", "", "")
    if not jabber_config_section["color"]:
        weechat.config_free(jabber_config_file)
        return
    jabber_config_option["message_join"] = weechat.config_new_option(
        jabber_config_file, jabber_config_section["color"],
        "message_join", "color", "color for text in join messages", "", 0, 0,
        "green", "green", 0, "", "", "", "", "", "")
    jabber_config_option["message_quit"] = weechat.config_new_option(
        jabber_config_file, jabber_config_section["color"],
        "message_quit", "color", "color for text in quit messages", "", 0, 0,
        "red", "red", 0, "", "", "", "", "", "")
    # server
    jabber_config_section["server"] = weechat.config_new_section(
        jabber_config_file, "server", 0, 0,
        "jabber_config_server_read_cb", "", "jabber_config_server_write_cb", "",
        "", "", "", "", "", "")
    if not jabber_config_section["server"]:
        weechat.config_free(jabber_config_file)
        return

def jabber_config_reload_cb(data, config_file):
    """ Reload config file. """
    return weechat.WEECHAT_CONFIG_READ_OK

def jabber_config_server_read_cb(data, config_file, section, option_name, value):
    """ Read server option in config file. """
    global jabber_servers
    rc = weechat.WEECHAT_CONFIG_OPTION_SET_ERROR
    items = option_name.split(".", 1)
    if len(items) == 2:
        server = jabber_search_server_by_name(items[0])
        if not server:
            server = Server(items[0])
            jabber_servers.append(server)
        if server:
            rc = weechat.config_option_set(server.options[items[1]], value, 1)
            # If configuration is set to autoconnect, connect now
            if items[1] == 'autoconnect' and value == 'on':
                server.connect()
    return rc

def jabber_config_server_write_cb(data, config_file, section_name):
    """ Write server section in config file. """
    global jabber_servers
    weechat.config_write_line(config_file, section_name, "")
    for server in jabber_servers:
        for name, option in server.options.iteritems():
            weechat.config_write_option (config_file, option)
    return weechat.WEECHAT_RC_OK

def jabber_config_read():
    """ Read jabber config file (jabber.conf). """
    global jabber_config_file
    return weechat.config_read(jabber_config_file)

def jabber_config_write():
    """ Write jabber config file (jabber.conf). """
    global jabber_config_file
    return weechat.config_write(jabber_config_file)

def jabber_debug_enabled():
    """ Return True if debug is enabled. """
    global jabber_config_options
    if weechat.config_boolean(jabber_config_option["debug"]):
        return True
    return False

def jabber_config_color(color):
    """ Return color code for a jabber color option. """
    global jabber_config_option
    if color in jabber_config_option:
        return weechat.color(weechat.config_color(jabber_config_option[color]))
    return ""

# ================================[ servers ]=================================

class Server:
    """ Class to manage a server: buffer, connection, send/recv data. """
    
    def __init__(self, name, jid="", password="", autoconnect=''):
        """ Init server """
        global jabber_config_file, jabber_config_section, jabber_server_options
        self.name = name
        # create options (user can set them with /set)
        self.options = {}
        values = { "jid": jid, "password": password, 'autoconnect': autoconnect, 'autoreconnect': '' }
        for option_name, props in jabber_server_options.iteritems():
            self.options[option_name] = weechat.config_new_option(
                jabber_config_file, jabber_config_section["server"],
                self.name + "." + option_name, props["type"], props["desc"],
                props["string_values"], props["min"], props["max"],
                props["default"], values[option_name], 0,
                props["check_cb"], "", props["change_cb"], "",
                props["delete_cb"], "")
        # internal data
        self.jid = None
        self.client = None
        self.sock = None
        self.hook_fd = None
        self.buffer = ""
        self.nick = ""
        self.nicks = {}
        self.chats = []


    
    def option_string(self, option_name):
        """ Return a server option, as string. """
        return weechat.config_string(self.options[option_name])

    def option_boolean(self, option_name):
        """ Return a server option, as boolean. """
        return weechat.config_boolean(self.options[option_name])

    def connect(self):
        """ Connect to Jabber server. """
        if not self.buffer:
            bufname = "%s.server.%s" % (SCRIPT_NAME, self.name)
            self.buffer = weechat.buffer_search("python", bufname)
            if not self.buffer:
                self.buffer = weechat.buffer_new(bufname,
                                                 "jabber_buffer_input_cb", "",
                                                 "jabber_buffer_close_cb", "")
            if self.buffer:
                weechat.buffer_set(self.buffer, "short_name", self.name)
                weechat.buffer_set(self.buffer, "localvar_set_type", "server")
                weechat.buffer_set(self.buffer, "localvar_set_server", self.name)
                weechat.buffer_set(self.buffer, "nicklist", "1")
                weechat.buffer_set(self.buffer, "nicklist_display_groups", "1")
                weechat.buffer_set(self.buffer, "display", "auto")
        self.disconnect()
        self.jid = xmpp.protocol.JID(self.option_string("jid"))
        self.client = xmpp.Client(self.jid.getDomain(), debug=[])
        conn = self.client.connect()
        if conn:
            weechat.prnt(self.buffer, "jabber: connection ok with %s" % conn)
            res = self.jid.getResource()
            if not res:
                res = "WeeChat"
            self.nick = self.jid.getNode()
            auth = self.client.auth(self.nick,
                                    self.option_string("password"),
                                    res)
            if auth:
                weechat.prnt(self.buffer, "jabber: authentication ok (using %s)" % auth)
                self.client.RegisterHandler("presence", self.presence_handler)
                self.client.RegisterHandler("iq", self.iq_handler)
                self.client.RegisterHandler("message", self.message_handler)
                self.client.sendInitPresence(requestRoster=0)
                #client.SendInitPresence(requestRoster=0)
                self.sock = self.client.Connection._sock.fileno()
                hook_fd = weechat.hook_fd(self.sock, 1, 0, 0, "jabber_fd_cb", "")
                weechat.buffer_set(self.buffer, "highlight_words", self.nick)
                weechat.buffer_set(self.buffer, "localvar_set_nick", self.nick);
            else:
                self.nick = ""
                weechat.prnt(self.buffer, "%sjabber: could not authenticate"
                             % weechat.prefix("error"))
                self.client = None
        else:
            weechat.prnt(self.buffer, "%sjabber: could not connect"
                         % weechat.prefix("error"))
            self.client = None
    
    def search_chat_buffer(self, buddy):
        """ Search a chat buffer for a buddy. """
        for chat in self.chats:
            if chat.buddy == buddy:
                return chat
        return None
    
    def new_chat(self, buddy, switch_to_buffer=False):
        """ Create a new chat with a buddy. """
        chat = self.search_chat_buffer(buddy)
        if not chat:
            chat = Chat(self, buddy, switch_to_buffer)
            self.chats.append(chat)
    
    def print_debug_server(self, message):
        """ Print debug message on server buffer. """
        if jabber_debug_enabled():
            weechat.prnt(self.buffer, "%sjabber: %s" % (weechat.prefix("network"), message))
    
    def print_debug_handler(self, handler_name, node):
        """ Print debug message for a handler on server buffer. """
        self.print_debug_server("%s_handler, xml message:\n%s"
                                % (handler_name,
                                   node.__str__(fancy=True).encode("utf-8")))
    
    def print_error(self, message):
        """ Print error message on server buffer. """
        if jabber_debug_enabled():
            weechat.prnt(self.buffer, "%sjabber: %s" % (weechat.prefix("error"), message))
    
    def get_away_string(self, nick):
        """ Get string with away and reason, with color codes. """
        if not nick["away"]:
            return ""
        str_colon = ": "
        if not nick["status"]:
            str_colon = ""
        return " %s(%saway%s%s%s)" % (weechat.color("chat_delimiters"),
                                      weechat.color("chat"),
                                      str_colon,
                                      nick["status"].replace("\n", " "),
                                      weechat.color("chat_delimiters"))
    
    def presence_handler(self, conn, node):
        """ Receive presence message. """
        self.print_debug_handler("presence", node)
        node_type = node.getType()
        nickname = node.getFrom().getStripped().encode("utf-8")
        #if nickname in self.nicks:
        #    del self.nicks[nickname]
        ptr_nick_gui = weechat.nicklist_search_nick(self.buffer, "", nickname)
        weechat.nicklist_remove_nick(self.buffer, ptr_nick_gui)
        if node_type not in ["error", "unavailable"]:
            nick = { "away": False, "status": "" }
            show = node.getShow()
            nick_color = "bar_fg"
            if node.getStatus():
                nick["status"] = node.getStatus().encode("utf-8")
            else:
                nick["status"] = ""
            if show in ["away", "xa"]:
                nick["away"] = True
                nick_color = "weechat.color.nicklist_away"
            weechat.nicklist_add_nick(self.buffer, "", node.getFrom().getStripped(),
                                      nick_color, "", "", 1)

            # Check if status has change and print if it has
            if nickname in self.nicks:
                if nick['status'] != self.nicks[nickname]['status']:
                    self.print_status(nickname, nick['status'])

            self.nicks[nickname] = nick
            if not ptr_nick_gui:
                weechat.prnt(self.buffer, "%s%s%s%s has joined%s"
                             % (weechat.prefix("join"),
                                weechat.color("chat_nick"),
                                nickname,
                                jabber_config_color("message_join"),
                                self.get_away_string(nick)))
        else:
            if ptr_nick_gui:
                weechat.prnt(self.buffer, "%s%s%s%s has quit"
                             % (weechat.prefix("quit"),
                                weechat.color("chat_nick"),
                                nickname,
                                jabber_config_color("message_quit")))
    
    def iq_handler(self, conn, node):
        """ Receive iq message. """
        self.print_debug_handler("iq", node)
        #weechat.prnt(self.buffer, "jabber: iq handler")
    
    def message_handler(self, conn, node):
        """ Receive message. """
        self.print_debug_handler("message", node)
        node_type = node.getType()
        if node_type in ["message", "chat", None]:
            buddy = node.getFrom().getStripped()
            body = node.getBody()
            if buddy and body:
                self.new_chat(buddy)
                chat = self.search_chat_buffer(buddy)
                if chat:
                    chat.recv_message(buddy.encode("utf-8"), node.getFrom(), body.encode("utf-8"))
        else:
            self.print_error("unknown message type: '%s'" % node_type)
    
    def recv(self):
        """ Receive something from Jabber server. """
        try:
            if self.client:
                self.client.Process(1)
        except xmpp.protocol.StreamError, e:
            weechat.prnt('', '%s: Error from server: %s' %(SCRIPT_NAME, e))
            self.disconnect()

            if weechat.config_boolean(self.options['autoreconnect']):
                autoreconnect_delay = 30
                weechat.command('', '/wait %s /%s connect %s' %(\
                    autoreconnect_delay, SCRIPT_COMMAND, self.name))
    
    def print_status(self, nickname, status):
        ''' Print a status in server window and in chat '''
        weechat.prnt(self.buffer, "%s%s has status %s" % (\
                weechat.prefix("action"),
                nickname,
                status))
        for chat in self.chats:
            if nickname in chat.buddy:
                chat.print_status(status)
                break
    
    def send_message(self, buddy, message):
        """ Send a message to buddy. """
        if self.client:
            msg = xmpp.protocol.Message(to=buddy, body=message, typ='chat')
            self.client.send(msg)
    
    def set_away(self, message):
        """ Set/unset away on server. """
        weechat.prnt(self.buffer, "test, away == %s" % message)
    
    def display_buddies(self):
        """ Display buddies. """
        weechat.prnt(self.buffer, "")
        weechat.prnt(self.buffer, "Buddies:")
        for nickname, nick in self.nicks.iteritems():
            weechat.prnt(self.buffer, "  %s%s%s" % (weechat.color("chat_nick"),
                                                    nickname,
                                                    self.get_away_string(nick)))
            #weechat.prnt(self.buffer, "    dict: %s" % nick)
    
    def disconnect(self):
        """ Disconnect from Jabber server. """
        if self.hook_fd != None:
            weechat.unhook(self.hook_fd)
            self.hook_fd = None
        if self.client != None:
            weechat.prnt(self.buffer, "jabber: disconnecting from %s..." % self.name)
            self.client.disconnect()
            self.client = None
            self.jid = None
            self.sock = None
            self.nick = ""
            self.nicks.clear()
            weechat.nicklist_remove_all(self.buffer)

    
    def close_buffer(self):
        """ Close server buffer. """
        if self.buffer != "":
            weechat.buffer_close(self.buffer)
            self.buffer = ""

    def delete(self):
        """ Delete server. """
        for chat in self.chats:
            chat.delete()
        self.nicks.clear()
        self.disconnect()
        self.close_buffer()
        for option in self.options.keys():
            weechat.config_option_free(option)

def jabber_search_server_by_name(name):
    """ Search a server by name. """
    global jabber_servers
    for server in jabber_servers:
        if server.name == name:
            return server
    return None

def jabber_search_context(buffer):
    """ Search a server / chat for a buffer. """
    global jabber_servers
    context = { "server": None, "chat": None }
    for server in jabber_servers:
        if server.buffer == buffer:
            context["server"] = server
            return context
        for chat in server.chats:
            if chat.buffer == buffer:
                context["server"] = server
                context["chat"] = chat
                return context
    return context

def jabber_search_context_by_name(server_name):
    ''' Search for buffer given name of server '''

    bufname = "%s.server.%s" % (SCRIPT_NAME, server_name)
    return jabber_search_context(weechat.buffer_search("python", bufname))

# =================================[ chats ]==================================

class Chat:
    """ Class to manage private chat with buddy or MUC. """
    
    def __init__(self, server, buddy, switch_to_buffer):
        """ Init chat """
        self.server = server
        self.buddy = buddy
        bufname = "%s.%s.%s" % (SCRIPT_NAME, server.name, buddy)
        self.buffer = weechat.buffer_new(bufname,
                                         "jabber_buffer_input_cb", "",
                                         "jabber_buffer_close_cb", "")
        self.buffer_title = self.buddy
        if self.buffer:
            weechat.buffer_set(self.buffer, "title", self.buffer_title)
            weechat.buffer_set(self.buffer, "short_name", self.buddy)
            weechat.buffer_set(self.buffer, "localvar_set_type", "private")
            weechat.buffer_set(self.buffer, "localvar_set_server", server.name)
            weechat.buffer_set(self.buffer, "localvar_set_channel", buddy)
            weechat.hook_signal_send("logger_backlog",
                                     weechat.WEECHAT_HOOK_SIGNAL_POINTER, self.buffer)
            if switch_to_buffer:
                weechat.buffer_set(self.buffer, "display", "auto")
    
    def recv_message(self, buddy_stripped, buddy, message):
        """ Receive a message from buddy. """
        if buddy != self.buffer_title:
            self.buffer_title = buddy
            weechat.buffer_set(self.buffer, "title", "%s" % self.buffer_title)
        weechat.prnt_date_tags(self.buffer, 0, "notify_private",
                               "%s%s\t%s" % (weechat.color("chat_nick_other"),
                                             buddy_stripped,
                                             message))
    
    def send_message(self, message):
        """ Send message to buddy. """
        self.server.send_message(self.buddy, message)
        weechat.prnt(self.buffer, "%s%s@%s\t%s" % (weechat.color("chat_nick_self"),
                                                   self.server.jid.getNode(),
                                                   self.server.jid.getDomain(),
                                                   message))
    def print_status(self, status):
        ''' Print a status message in chat '''
        weechat.prnt(self.buffer, "%s%s has status %s" % (\
                    weechat.prefix("action"),
                    self.buddy,
                    status))
    
    def close_buffer(self):
        """ Close chat buffer. """
        if self.buffer != "":
            weechat.buffer_close(self.buffer)
            self.buffer = ""

    def delete(self):
        """ Delete chat. """
        self.close_buffer()

# ================================[ commands ]================================

def jabber_hook_commands_and_completions():
    """ Hook commands and completions. """
    weechat.hook_command(SCRIPT_COMMAND, "List, add, remove, connect to Jabber servers",
                         "[ list | add name jid password | connect server | "
                         "disconnect | del server | away [message] | buddies ]",
                         "      list: list servers and chats\n"
                         "       add: add a server"
                         "   connect: connect to server using password\n"
                         "disconnect: disconnect from server\n"
                         "       del: delete server\n"
                         "      away: set away with a message (if no message, away is unset)"
                         "   buddies: display buddies on server\n"
                         "     debug: toggle jabber debug on/off (for all servers)\n\n"
                         "Without argument, this command lists servers and chats.\n\n"
                         "Examples:\n"
                         "  Add a server:       /jabber add myserver user@server.tld password\n"
                         "  Connect to server:  /jabber connect myserver\n"
                         "  Disconnect:         /jabber disconnect myserver\n"
                         "  Delete server:      /jabber del myserver\n\n"
                         "Other jabber commands:\n"
                         "  /jchat  chat with a buddy (in private buffer)\n"
                         "  /jmsg   send message to a buddy",
                         "list %(jabber_servers)"
                         " || add %(jabber_servers)"
                         " || connect %(jabber_servers)"
                         " || disconnect %(jabber_servers)"
                         " || del %(jabber_servers)"
                         " || away"
                         " || buddies"
                         " || debug",
                         "jabber_cmd_jabber", "")
    weechat.hook_command("jchat", "Chat with a Jabber buddy",
                         "buddy",
                         "buddy: buddy id",
                         "",
                         "jabber_cmd_jchat", "")
    weechat.hook_command("jmsg", "Send a messge to a buddy",
                         "[-server servername] buddy text",
                         "servername: name of jabber server buddy is on\n"
                         "     buddy: buddy id",
                         "",
                         "jabber_cmd_jmsg", "")
    weechat.hook_completion("jabber_servers", "list of jabber serves",
                            "jabber_completion_servers", "")

def jabber_list_servers_chats(name):
    """ List servers and chats. """
    global jabber_servers
    weechat.prnt("", "")
    if len(jabber_servers) > 0:
        weechat.prnt("", "jabber servers:")
        for server in jabber_servers:
            if name == "" or server.name.find(name) >= 0:
                connected = ""
                if server.sock >= 0:
                    connected = " (connected)"
                weechat.prnt("", "  %s - %s%s" % (server.name, server.option_string("jid"), connected))
                for chat in server.chats:
                    weechat.prnt("", "    chat with %s" % (chat.buddy))
    else:
        weechat.prnt("", "jabber: no server defined")

def jabber_cmd_jabber(data, buffer, args):
    """ Command '/jabber'. """
    global jabber_servers, jabber_config_option
    if args == "" or args == "list":
        jabber_list_servers_chats("")
    else:
        argv = args.split(" ")
        argv1eol = ""
        pos = args.find(" ")
        if pos > 0:
            argv1eol = args[pos+1:]
        if argv[0] == "list":
            jabber_list_servers_chats(argv[1])
        elif argv[0] == "add":
            if len(argv) >= 4:
                server = jabber_search_server_by_name(argv[1])
                if server:
                    weechat.prnt("", "jabber: server '%s' already exists" % argv[1])
                else:
                    server = Server(argv[1], argv[2], argv[3])
                    jabber_servers.append(server)
                    weechat.prnt("", "jabber: server '%s' created" % argv[1])
        elif argv[0] == "connect":
            if len(argv) >= 2:
                server = jabber_search_server_by_name(argv[1])
                if server:
                    server.connect()
                else:
                    weechat.prnt("", "jabber: server '%s' not found" % argv[1])
            else:
                context = jabber_search_context(buffer)
                if context["server"]:
                    context["server"].connect()
        elif argv[0] == "disconnect":
            context = jabber_search_context(buffer)
            if context["server"]:
                context["server"].disconnect()
        elif argv[0] == "del":
            if len(argv) >= 2:
                server = jabber_search_server_by_name(argv[1])
                if server:
                    server.delete()
                    jabber_servers.remove(server)
                    weechat.prnt("", "jabber: server '%s' deleted" % argv[1])
                else:
                    weechat.prnt("", "jabber: server '%s' not found" % argv[1])
        elif argv[0] == "send":
            if len(argv) >= 3:
                context = jabber_search_context(buffer)
                if context["server"]:
                    context["server"].send_message(argv[1], argv[2])
        elif argv[0] == "read":
            jabber_config_read()
        elif argv[0] == "away":
            context = jabber_search_context(buffer)
            if context["server"]:
                context["server"].set_away(argv1eol)
        elif argv[0] == "buddies":
            context = jabber_search_context(buffer)
            if context["server"]:
                context["server"].display_buddies()
        elif argv[0] == "debug":
            weechat.config_option_set(jabber_config_option["debug"], "toggle", 1)
            if jabber_debug_enabled():
                weechat.prnt("", "jabber: debug is now ON")
            else:
                weechat.prnt("", "jabber: debug is now off")
        else:
            weechat.prnt("", "jabber: unknown action")
    return weechat.WEECHAT_RC_OK

def jabber_cmd_jchat(data, buffer, args):
    """ Command '/jchat'. """
    if args:
        context = jabber_search_context(buffer)
        if context["server"]:
            context["server"].new_chat(args, True)
    return weechat.WEECHAT_RC_OK

def jabber_cmd_jmsg(data, buffer, args):
    """ Command '/jmsg'. """

    if args:
        argv = args.split()
        if len(argv) < 2:
            return weechat.WEECHAT_RC_OK
        if argv[0] == '-server':
            context = jabber_search_context_by_name(argv[1])
            recipient = argv[2]
            message = " ".join(argv[3:])
        else:
            context = jabber_search_context(buffer)
            recipient = argv[0]
            message = " ".join(argv[1:])
        if context["server"]:
            context["server"].send_message(recipient, message)

    return weechat.WEECHAT_RC_OK

def jabber_completion_servers(data, completion_item, buffer, completion):
    """ Completion with jabber server names. """
    global jabber_servers
    for server in jabber_servers:
        weechat.hook_completion_list_add(completion, server.name,
                                         0, weechat.WEECHAT_LIST_POS_SORT)
    return weechat.WEECHAT_RC_OK

# ==================================[ fd ]====================================

def jabber_fd_cb(data, fd):
    """ Callback for reading socket. """
    global jabber_servers
    for server in jabber_servers:
        if server.sock == int(fd):
            server.recv()
    return weechat.WEECHAT_RC_OK

# ================================[ buffers ]=================================

def jabber_buffer_input_cb(data, buffer, input_data):
    """ Callback called for input data on a jabber buffer. """
    context = jabber_search_context(buffer)
    if context["server"] and context["chat"]:
        context["chat"].send_message(input_data)
    elif context["server"]:
        if input_data == "buddies" or "buddies".startswith(input_data):
            context["server"].display_buddies()
    return weechat.WEECHAT_RC_OK

def jabber_buffer_close_cb(data, buffer):
    """ Callback called when a jabber buffer is closed. """
    context = jabber_search_context(buffer)
    if context["server"] and context["chat"]:
        context["chat"].buffer = ""
        context["server"].chats.remove(context["chat"])
    elif context["server"]:
        context["server"].buffer = ""
    return weechat.WEECHAT_RC_OK

# ==================================[ main ]==================================

if __name__ == "__main__" and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                        SCRIPT_LICENSE, SCRIPT_DESC,
                        "jabber_unload_script", ""):
        jabber_hook_commands_and_completions()
        jabber_config_init()
        jabber_config_read()

# ==================================[ end ]===================================

def jabber_unload_script():
    """ Function called when script is unloaded. """
    global jabber_servers
    jabber_config_write()
    for server in jabber_servers:
        server.disconnect()
        server.delete()
    return weechat.WEECHAT_RC_OK
