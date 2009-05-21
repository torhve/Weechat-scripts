#
# UrlGrab, version 1.4 for weechat version 0.2.7-devel
#
#   Listens to all channels for URLs, collects them in a list, and launches
#   them in your favourite web server on the local host or a remote server.
#   Copies url to X11 clipboard via xsel
#      (http://www.vergenet.net/~conrad/software/xsel)
#
# Usage:
#
#   The /url command provides access to all UrlGrab functions.  Run
#   '/url help' for complete command usage.
#
#   In general, use '/url list' to list the entire url list for the current
#   channel, and '/url <n>' to launch the nth url in the list.  For
#   example, to launch the first (and most-recently added) url in the list,
#   you would run '/url 1'
#
#   From the server window, you must specify a specific channel for the
#   list and launch commands, for example:
#     /url list weechat 
#     /url 3 weechat
#
# Configuration:
#
#   The '/url set' command lets you get and set the following options:
#
#   historysize
#     The maximum number of URLs saved per channel.  Default is 10
#
#   method
#     Must be one of 'local' or 'remote' - Defines how URLs are launched by
#     the script.  If 'local', the script will run 'localcmd' on the host.
#     If 'remote', the script will run 'remotessh remotehost remotecmd' on
#     the local host which should normally use ssh to connect to another
#     host and run the browser command there.
#
#   localcmd
#     The command to run on the local host to launch URLs in 'local' mode.
#     The string '%s' will be replaced with the URL.  The default is
#     'firefox %s'.
#
#   remotessh
#     The command (and arguments) used to connect to the remote host for
#     'remote' mode.  The default is 'ssh -x' which will connect as the
#     current username via ssh and disable X11 forwarding.
#
#   remotehost
#     The remote host to which we will connect in 'remote' mode.  For ssh,
#     this can just be a hostname or 'user@host' to specify a username
#     other than your current login name.  The default is 'localhost'.
#
#   remotecmd
#     The command to execute on the remote host for 'remote' mode.  The
#     default is 'bash -c "DISPLAY=:0.0 firefox %s"'  Which runs bash, sets
#     up the environment to display on the remote host's main X display,
#     and runs firefox.  As with 'localcmd', the string '%s' will be
#     replaced with the URL.
#
#   cmdoutput
#     The file where the command output (if any) is saved.  Overwritten
#     each time you launch a new URL.  Default is ~/.weechat/urllaunch.log
#
#   default
#     The command that will be run if no arguemnts to /url are given.
#     Default is help
#
# Requirements:
#
#  - Designed to run with weechat version 0.3 or better.
#      http://weechat.flashtux.org/
#
# Acknowlegements:
#
#  - Based on an earlier version called 'urlcollector.py' by 'kolter' of
#    irc.freenode.net/#weechat Honestly, I just cleaned up the code a bit and
#    made the settings a little more useful (to me).
#
#  - With changes by Leonid Evdokimov (weechat at darkk dot net another dot ru):
#    http://darkk.net.ru/weechat/urlgrab.py
#    v1.1:  added better handling of dead zombie-childs
#           added parsing of private messages
#           added default command setting
#           added parsing of scrollback buffers on load
#    v1.2:  `historysize` was ignored
#
#  - With changes by ExclusivE (exclusive_tm at mail dot ru):
#    v1.3: X11 clipboard support
#
#  - V1.4 Just ported it over to weechat 0.2.7  drubin AT smartcube dot co dot za
#  - V1.5b  1) I created a logging feature for urls, Time, Date, buffer, and url.
#           2) Added selectable urls support, similar to the iset plugin (Thanks flashtux)
#           3) Colors/formats are configuarable.
#           4) browser now uses hook_process (Please test with remote clients)
#           5) Added /url open http://url.com functionality
#
# Copyright (C) 2005 Jim Ramsay <i.am@jimramsay.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#

import sys
import os
try:
    import weechat
    import_ok = True
except:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://weechat.flashtux.org/"
    import_ok = False
import subprocess
import time

SCRIPT_NAME    = "urlgrab"
SCRIPT_AUTHOR  = "David Rubin <drubin [At] smartcube [dot] co [dot] za>"
SCRIPT_VERSION = "1.5b"
SCRIPT_LICENSE = "GPL"
SCRIPT_DESC    = "Url functionality added, Loggin, opening of browser"

def urlGrabPrint(message):
    bufferd=weechat.current_buffer()
    if urlGrabSettings.get('output_main_buffer') == "on":
        weechat.prnt("","[%s] %s" % ( SCRIPT_NAME, message ) )
    else :
        weechat.prnt(bufferd,"[%s] %s" % ( SCRIPT_NAME, message ) )
        
def hashBufferName(bufferp):
    if not weechat.buffer_get_string(bufferp, "short_name"):
        bufferd = weechat.buffer_get_string(bufferp, "name")
    else:
        bufferd = weechat.buffer_get_string(bufferp, "short_name")
    return bufferd

class WeechatSetting:
    def __init__(self, name, default, description = "" ):
        self.name = name
        self.default = default
        self.description = description
        test = weechat.config_get_plugin( name )
        if test is None or test == "":
            weechat.config_set_plugin( name, default )

class UrlGrabSettings:
    def __init__(self):
        self.settings = {
        'default':WeechatSetting('default', 'help',
                "default command to /url to run if none given" ),
        'historysize':WeechatSetting('historysize', '10',
                "Number of URLs to keep per channel" ),
        'method':WeechatSetting('method', 'local',
                """Where to launch URLs
            If 'local', runs %localcmd%.
            If 'remote' runs the following command:
            `%remotessh% %remotehost% %remotecmd`"""),
            'localcmd':WeechatSetting('localcmd', 'firefox %s',
                """Command to launch local URLs.  '%s' becomes the URL.
            Default 'firefox %s'"""),
        'remotessh':WeechatSetting('remotessh', 'ssh -x',
                """Command (and arguments) to connect to a remote machine.
                Default 'ssh -x'"""),
        'remotehost':WeechatSetting('remotehost', 'localhost',
                """Hostname for remotypete launching
                 Default 'localhost'"""),
        'remotecmd':WeechatSetting('remotecmd',
                'bash -c \"DISPLAY=:0.0 firefox %s\"',
                """Command to launch remote URLs.  '%s' becomes the URL.
             Default 'bash -c \"DISPLAY=:0.0 firefox %s\"'"""),
        'url_log':WeechatSetting('url_log',
                '~/.weechat/urls.log',
                """File where command output is saved.  Overwritten each
                time an URL is launched
                Default '~/.weechat/urls.log'"""), 
        'time_format':WeechatSetting('time_format',
                '%H:%M:%S',
                """File where command output is saved.  Overwritten each
                time an URL is launched
                Default '%H:%M:%S'"""), 
        'showbuffer':WeechatSetting('showbuffer','on',
            """Shows logs to a buffer and inturn saves them to a logfile."""),  
        'output_main_buffer':WeechatSetting('output_main_buffer','on',
            """Shows logs to a buffer and inturn saves them to a logfile."""),
        'color_buffer':WeechatSetting('color_buffer','red',
            """Shows logs to a buffer and inturn saves them to a logfile."""),
        'color_url':WeechatSetting('color_url','blue',
            """Shows logs to a buffer and inturn saves them to a logfile."""),
        'color_time': WeechatSetting('color_time','cyan',
            """Shows logs to a buffer and inturn saves them to a logfile."""),
        'color_buffer_selected':WeechatSetting('color_buffer_selected','red',
            """Shows logs to a buffer and inturn saves them to a logfile."""),
        'color_url_selected':WeechatSetting('color_url_selected','blue',
            """Shows logs to a buffer and inturn saves them to a logfile."""),
        'color_time_selected':WeechatSetting('color_time_selected','cyan',
            """Shows logs to a buffer and inturn saves them to a logfile."""),
        'color_bg_selected':WeechatSetting('color_bg_selected','green',
            """Shows logs to a buffer and inturn saves them to a logfile."""
                )
		}

    def has(self, name):    
        return name in self.settings

    def names(self):
        return self.settings.keys()

    def description(self, name):
        return self.settings[name].description

    def set(self, name, value):
        # Force string values only
        if type(value) != type("a"):
            value = str(value)
        if name == "method":
            if value.lower() == "remote":
                weechat.config_set_plugin( 'method', "remote" )
            elif value.lower() == "local":
                weechat.config_set_plugin( 'method', "local" )
            else:
                raise ValueError( "\'%s\' is not \'local\' or \'remote\'" % value )
        elif name == "localcmd":
            if value.find("%s") == -1:
                weechat.config_set_plugin( 'localcmd', value + " %s" )
            else:
                weechat.config_set_plugin( 'localcmd', value )
        elif name == "remotecmd":
            if value.find( "%s" ) == -1:
                weechat.config_set_plugin( 'remotecmd', value + " %s" )
            else:
                weechat.config_set_plugin( 'remotecmd', value )
        elif self.has(name):
            weechat.config_set_plugin( name, value )
            if name == "historysize":
                urlGrab.setHistorysize(int(value))
        else:
            raise KeyError( name )

    def get(self, name):
        if self.has(name):
            if name == 'historysize':
                try:
                    return int(weechat.config_get_plugin(name))
                except:
                    return int(self.settings[name].default)
            else:
                return weechat.config_get_plugin(name)
        else:
            raise KeyError( name )

    def prnt(self, name, verbose = True):
        weechat.prnt( ""," %s = %s" % (name.ljust(11), self.get(name)) )
        if verbose:
            weechat.prnt( "","  -> %s" % (self.settings[name].description) )

    def prntall(self):
        for key in self.names():
            self.prnt(key, verbose = False)

    def createCmd(self, url):
        if weechat.config_get_plugin( 'method' ) == 'remote':
            tmplist = weechat.config_get_plugin( 'remotessh' ).split(" ")
            tmplist.append(weechat.config_get_plugin( 'remotehost' ))
            tmplist.append(weechat.config_get_plugin( 'remotecmd' ) % (url))
        else:
            tmplist = (weechat.config_get_plugin( 'localcmd' ) % (url) )
        return tmplist

class UrlGrabber:
    def __init__(self, historysize):
        # init
        self.urls = {}
        self.globalUrls = []
        self.historysize = 5
        # control
        self.setHistorysize(historysize)

    def setHistorysize(self, count):
        if count > 1:
            self.historysize = count

    def getHistorysize(self):
        return self.historysize

    def addUrl(self, bufferp,url ):
        global urlGrabSettings
        self.globalUrls.insert(0,{"buffer":bufferp, "url":url, "time":time.strftime(urlGrabSettings.get("time_format"))})
        #Log urls only if we have set a log path.
        if urlGrabSettings.get('url_log'):
            try :
                index = self.globalUrls[0] 
                logfile = os.path.expanduser(urlGrabSettings.get('url_log'))
                dout = open(logfile, "a")
                dout.write("%s %s %s\n" % (index['time'], index['buffer'], index['url']))
                dout.close()
            except :
                urlGrabPrint ("failed to log url")
        
        # check for server
        if not  bufferp in self.urls:
            self.urls[bufferp] = []
        # check for chan
        # add url
        if url in self.urls[bufferp]:
            self.urls[bufferp].remove(url)
        self.urls[bufferp].insert(0, url)
        # removing old urls
        while len(self.urls[bufferp]) > self.historysize:
            self.urls[bufferp].pop()

    def hasIndex( self, bufferp, index ):
        return bufferp in self.urls and \
                len(self.url[bufferp]) >= index

    def hasBuffer( self, bufferp ):
        return bufferp in self.urls
    

    def getUrl(self, bufferp, index):
        url = ""
        if  bufferp in self.urls:
       		if len(self.urls[bufferp]) >= index:
                    url = self.urls[bufferp][index-1]
        return url
        

    def prnt(self, buff):
        found = True
        if self.urls.has_key(buff):
            if len(self.urls[buff]) > 0:
                i = 1
                for url in self.urls[buff]:
                    urlGrabPrint("--> " + str(i) + " : " + url)
                    i += 1
            else:
                found = False
        elif buff == "*":
            for b in self.urls.keys():
              self.prnt(b)
        else:
            found = False

        if not found:
            urlGrabPrint(buff + ": no entries")

def urlGrabCheckMsgline(bufferp, message):
	global urlGrab, max_buffer_length
	if not message:
		return
	# Ignore output from 'tinyurl.py' and our selfs
	if message.startswith( "[AKA] http://tinyurl.com" ) or message.startswith("[urlgrab]"):
		return
	# Check for URLs
	#TODO: Get better url detection this isn't great..
	for word in message.split(" "):
	    if (word[0:7] == "http://" or word[0:8] == "https://" or  word[0:6] == "ftp://"):
	        if len(bufferp) > max_buffer_length: 
	            max_buffer_length = len(bufferp)
	        urlGrab.addUrl(bufferp,word)
	        if urlgrab_buffer:
	            refresh();

def urlGrabCheck(data, bufferp, uber_empty, tagsn, isdisplayed, ishilight, prefix, message):
	global urlGrab
	urlGrabCheckMsgline(hashBufferName(bufferp), message)
	return weechat.WEECHAT_RC_OK

def urlGrabCheckOnload():
    for buf in weechat.get_buffer_info().itervalues():
        if len(buf['channel']):
            lines = weechat.get_buffer_data(buf['server'], buf['channel'])
            for line in reversed(lines):
                urlGrabCheckMsgline(buf['server'], buf['channel'], line['data'])

def urlGrabCopy(bufferd, index):
    global urlGrab
    if bufferd == "":
        urlGrabPrint( "No current channel, you must activate one" )
    elif not urlGrab.hasBuffer(bufferd):
        urlGrabPrint("No URL found - Invalid channel")
    else:
        if index <= 0:
            urlGrabPrint("No URL found - Invalid index")
            return
        url = urlGrab.getUrl(bufferd,index)
    if url == "":
        urlGrabPrint("No URL found - Invalid index")
    else:
        try: 
            pipe = os.popen("xsel -i","w")
            pipe.write(url)
            pipe.close()
            urlGrabPrint("Url: %s gone to clipboard." % url)
        except:
	        urlGrabPrint("Url: %s faile to copy to clipboard." % url)	

def urlGrabOpenUrl(url):
    global urlGrab, urlGrabSettings
    argl = urlGrabSettings.createCmd( url )
    #no callback we don't really care about it.
    weechat.hook_process(argl,1000, "", "")


def urlGrabOpen(bufferd, index):
    global urlGrab, urlGrabSettings 
    if bufferd == "":
        urlGrabPrint( "No current channel, you must specify one" )
    elif not urlGrab.hasBuffer(bufferd) :
        urlGrabPrint("No URL found - Invalid channel")
    else:
        if index <= 0:
            urlGrabPrint("No URL found - Invalid index")
            return
        url =  urlGrab.getUrl(bufferd,index)
        if url == "":
            urlGrabPrint("No URL found - Invalid index")
        else:
            urlGrabPrint("loading %s %sly" % (url, urlGrabSettings.get("method")))
            urlGrabOpenUrl (url)

def urlGrabList( args ):
    global urlGrab
    if len(args) == 0:
        buf = hashBufferName(weechat.current_buffer())
    else:
        buf = args[0]
    if buf == "" or buf == "all":
        buf = "*"
    urlGrab.prnt(buf)
        
def urlGrabHelp():
    urlGrabPrint("Help")
    urlGrabPrint(" Usage : ")
    urlGrabPrint("    /url help")
    urlGrabPrint("        -> display this help")
    urlGrabPrint("    /url list [buffer]")
    urlGrabPrint("        -> display list of recorded urls in the specified channel")
    urlGrabPrint("           If no channel is given, lists the current channel")
    urlGrabPrint("    /url set [name [[=] value]]")
    urlGrabPrint("        -> set or get one of the parameters")
    urlGrabPrint("    /url n [buffer]")
    urlGrabPrint("        -> launch the nth url in `/url list`")
    urlGrabPrint("           or the nth url in the specified channel")
    urlGrabPrint("    /url copy [n]")
    urlGrabPrint("        -> copy nth or last url to X11 clipboard")
    urlGrabPrint("")

def urlGrabMain(data, bufferp, args):
    if args[0:2] == "**":
        keyEvent(data, bufferp, args[2:])
        return weechat.WEECHAT_RC_OK

    bufferd = hashBufferName(bufferp)
    largs = args.split(" ")
    #strip spaces
    while '' in largs:
        largs.remove('')
    while ' ' in largs:
        largs.remove(' ')
    if len(largs) == 0:
        largs = [urlGrabSettings.get('default')]
    if largs[0] == 'help':
        urlGrabHelp()
    elif largs[0] == 'open' and len(largs) == 2:
        urlGrabOpenUrl(largs[1])
    elif largs[0] == "show":
        if not urlgrab_buffer:
            init();
        refresh();
        weechat.buffer_set(urlgrab_buffer, "display", "1");
    elif largs[0] == 'list':
        urlGrabList( largs[1:] )
    elif largs[0] == 'set':
        try:
            if (len(largs) == 1):
                urlGrabPrint( "Available settings:" )
                urlGrabSettings.prntall()
            elif (len(largs) == 2):
                name = largs[1]
                urlGrabPrint( "Get %s" % name )
                urlGrabSettings.prnt( name )
            elif (len(largs) > 2):
                name = largs[1]
                value = None
                if( largs[2] != "="):
                    value = " ".join(largs[2:])
                elif( largs > 3 and largs[2] == "=" ):
                    value = " ".join(largs[3:])
                urlGrabPrint( "set %s = \'%s\'" % (name, value) )
                if value is not None:
                    try:
                        urlGrabSettings.set( name, value )
                        urlGrabSettings.prnt( name, verbose=False )
                    except ValueError, msg:
                        weechat.prnt( "  Failed: %s" % msg )
                else:
                    weechat.prnt( "  Failed: No value given" )
        except KeyError:
            weechat.prnt( "  Failed: Unrecognized parameter '%s'" % name )
    elif largs[0] == 'copy':
    	if len(largs) > 1:
		no = int(largs[1])
		urlGrabCopy(bufferd, no)
	else:
		urlGrabCopy(bufferd,1)       
    else:
        try:
            no = int(largs[0])
            if len(largs) > 1:
                urlGrabOpen(largs[1], no)
            else:
                urlGrabOpen(bufferd, no)
        except ValueError:
            #not a valid number so try opening it as a url.. 
            urlGrabOpenUrl(largs[1])
            urlGrabPrint( "Unknown command '%s'.  Try '/url help' for usage" % largs[0])
    return weechat.WEECHAT_RC_OK

def buffer_input(*kwargs):
    return weechat.WEECHAT_RC_OK

def buffer_close(*kwargs):
    global urlgrab_buffer
    urlgrab_buffer =  None
    return weechat.WEECHAT_RC_OK

def keyEvent (data, bufferp, args):
    global urlGrab , urlGrabSettings, urlgrab_buffer, current_line
    if args == "refresh":
        refresh()
    elif args == "up":
        if current_line > 0:
            current_line = current_line -1
            refresh_line (current_line + 1)
            refresh_line (current_line)
    elif args == "down":
         if current_line < len(urlGrab.globalUrls) - 1:
            current_line = current_line +1
            refresh_line (current_line - 1)
            refresh_line (current_line)
    elif args == "scroll_top":
        temp_current = current_line
        current_line =  0
        refresh_line (temp_current)
        refresh_line (current_line)
        weechat.command(urlgrab_buffer, "/window scroll_top");
        pass 
    elif args == "scroll_bottom":
        temp_current = current_line
        current_line =  len(urlGrab.globalUrls)
        refresh_line (temp_current)
        refresh_line (current_line)
        weechat.command(urlgrab_buffer, "/window scroll_bottom");
    elif args == "enter":
        if urlGrab.globalUrls[current_line]:
            urlGrabOpenUrl (urlGrab.globalUrls[current_line]['url'])

def refresh_line (y):
    global urlGrab , urlGrabSettings, urlgrab_buffer, current_line, max_buffer_length
    format = "%%s%%s %%s%%-%ds%%s%%s" % (max_buffer_length+4)
    
    #non selected colors
    color_buffer = urlGrabSettings.get("color_buffer")
    color_url = urlGrabSettings.get("color_url")
    color_time =urlGrabSettings.get("color_time")
    #selected colors
    color_buffer_selected = urlGrabSettings.get("color_buffer_selected")
    color_url_selected = urlGrabSettings.get("color_url_selected")
    color_time_selected = urlGrabSettings.get("color_time_selected")
    
    color_bg_selected = weechat.config_get_plugin("color_bg_selected")
    
    color1 = color_time
    color2 = color_buffer
    color3 = color_url
    
    if y == current_line:
          color1 = "%s,%s" % (color_time_selected, color_bg_selected)
          color2 = "%s,%s" % (color_buffer_selected, color_bg_selected)
          color3 = "%s,%s" % (color_url_selected, color_bg_selected)
          
    color1 = weechat.color(color1)
    color2 = weechat.color(color2)
    color3 = weechat.color(color3)
    text = format % (color1,
                    urlGrab.globalUrls[y]['time'],
                    color2, 
                    urlGrab.globalUrls[y]['buffer'],
                    color3, 
                    urlGrab.globalUrls[y]['url'] )
    weechat.prnt_y(urlgrab_buffer,y,text)

def refresh():
    global urlGrab
    y=0
    for x in urlGrab.globalUrls:
        refresh_line (y)
        y += 1
    
    
def init():
    global urlGrab , urlGrabSettings, urlgrab_buffer
    if not urlgrab_buffer:
        urlgrab_buffer = weechat.buffer_new("urlgrab", "buffer_input", "", "buffer_close", "");
    if urlgrab_buffer:
        weechat.buffer_set(urlgrab_buffer, "type", "free");
        weechat.buffer_set(urlgrab_buffer, "key_bind_ctrl-R",        "/url **refresh")
        weechat.buffer_set(urlgrab_buffer, "key_bind_meta2-A",       "/url **up")
        weechat.buffer_set(urlgrab_buffer, "key_bind_meta2-B",       "/url **down")
        weechat.buffer_set(urlgrab_buffer, "key_bind_meta-ctrl-J",   "/url **enter")
        weechat.buffer_set(urlgrab_buffer, "key_bind_meta-ctrl-M",   "/url **enter")
        weechat.buffer_set(urlgrab_buffer, "key_bind_meta-meta2-1./~", "/url **scroll_top")
        weechat.buffer_set(urlgrab_buffer, "key_bind_meta-meta2-4~", "/url **scroll_bottom")
        weechat.buffer_set(urlgrab_buffer, "title","Lists the urls in the applications")
        weechat.buffer_set(urlgrab_buffer, "display", "1");

def completion_urls_cb(data, completion_item, bufferp, completion):
    """ Complete with URLS, for command '/url'. """
    global urlGrab
    bufferd = hashBufferName( bufferp)
    for url in urlGrab.globalUrls :
        if url['buffer'] == bufferd:
            weechat.hook_completion_list_add(completion, url['url'], 0, weechat.WEECHAT_LIST_POS_SORT)
    return weechat.WEECHAT_RC_OK
            

#Main stuff
if import_ok and weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,SCRIPT_DESC, "", ""):
    urlgrab_buffer = None
    current_line = 0
    max_buffer_length = 0
    urlGrabSettings = UrlGrabSettings()
    urlGrab = UrlGrabber( urlGrabSettings.get('historysize') )
    weechat.hook_print("", "", "", 1, "urlGrabCheck", "")
    weechat.hook_command("url",
                             "Url grabber",
                             "Controls UrlGrab -> '/url help' for usage",
                             "",
                             "open %(urlgrab_urls) || %(urlgrab_urls)",
                             "urlGrabMain", "")
    weechat.hook_completion("urlgrab_urls111", "list of URLs",
                                "completion_urls_cb", "")
else:
    print "failed to load weechat"