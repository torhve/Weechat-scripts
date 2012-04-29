# -*- coding: utf-8 -*-
#
# Copyright (C) 2011-2012 Sebastien Helleu <flashcode@flashtux.org>
# Copyright (C) 2011-2012 xt <xt@bash.no>
# Copyright (C) 2012 Filip H.F. "FiXato" Slagter <fixato+weechat+urlserver@gmail.com>
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
# Shorten URLs with own HTTP server.
# (this script requires Python >= 2.6)
#
# How does it work?
#
# 1. The URLs displayed in buffers are shortened and stored in memory (saved in
#    a file when script is unloaded).
# 2. URLs shortened can be displayed below messages, in a dedicated buffer, or
#    as HTML page in your browser.
# 3. This script embeds an HTTP server, which will redirect shortened URLs
#    to real URL and display list of all URLs if you browse address without URL key.
# 4. It is recommended to customize/protect the HTTP server using script options
#    (see /help urlserver)
#
# Example:
#
#   FlashCode | look at this: http://test.server.com/this-is-a-very-looooong-url
#             | http://myhost.org:1234/8aK
#
# List of URLs:
# - in WeeChat: /urlserver
# - in browser: http://myhost.org:1234/
#
# History:
#
# 2012-04-29, Tor Hveem <xt@bash.no>:
#   version 10: improve html, save to SQL, pagination
# 2012-04-18, Filip H.F. "FiXato" Slagter <fixato+weechat+urlserver@gmail.com>:
#     version 0.9: add options "http_autostart", "http_port_display"
#                  "url_min_length" can now be set to -1 to auto-detect minimal url length
#                  Also, if port is 80 now, :80 will no longer be added to the shortened url.
# 2012-04-17, Filip H.F. "FiXato" Slagter <fixato+weechat+urlserver@gmail.com>:
#     version 0.8: add more CSS support by adding options "http_fg_color", "http_css_url",
#                  and "http_title", add descriptive classes to most html elements.
#                  See https://raw.github.com/FiXato/weechat_scripts/master/urlserver/sample.css
#                  for a sample css file that can be used for http_css_url
# 2012-04-11, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.7: fix truncated HTML page (thanks to xt), fix base64 decoding with Python 3.x
# 2012-01-19, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.6: add option "http_hostname_display"
# 2012-01-03, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.5: make script compatible with Python 3.x
# 2011-10-31, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.4: add options "http_embed_youtube_size" and "http_bg_color",
#                  add extensions jpeg/bmp/svg for embedded images
# 2011-10-30, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.3: escape HTML chars for page with list of URLs, add option
#                  "http_prefix_suffix", disable highlights on urlserver buffer
# 2011-10-30, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.2: fix error on loading of file "urlserver_list.txt" when it is empty
# 2011-10-30, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.1: initial release
#

SCRIPT_NAME    = 'urlserver'
SCRIPT_AUTHOR  = 'Sebastien Helleu <flashcode@flashtux.org>'
SCRIPT_VERSION = '10'
SCRIPT_LICENSE = 'GPL3'
SCRIPT_DESC    = 'Shorten URLs with own HTTP server'

SCRIPT_COMMAND = 'urlserver'
SCRIPT_BUFFER  = 'urlserver'

import_ok = True

try:
    import weechat
except ImportError:
    print('This script must be run under WeeChat.')
    print('Get WeeChat now at: http://www.weechat.org/')
    import_ok = False

try:
    import sys, os, string, time, datetime, socket, re, base64, cgi, sqlite3, urlparse, urllib
except ImportError as message:
    print('Missing package(s) for %s: %s' % (SCRIPT_NAME, message))
    import_ok = False

def regexp(expr, item):
    reg = re.compile(expr)
    return reg.search(item) is not None


# regex are from urlbar.py, written by xt
url_octet = r'(?:2(?:[0-4]\d|5[0-5])|1\d\d|\d{1,2})'
url_ipaddr = r'%s(?:\.%s){3}' % (url_octet, url_octet)
url_label = r'[0-9a-z][-0-9a-z]*[0-9a-z]?'
url_domain = r'%s(?:\.%s)*\.[a-z][-0-9a-z]*[a-z]?' % (url_label, url_label)

class urldb(object):

    def __init__(self):
        filename = os.path.join(weechat.info_get('weechat_dir', ''), 'urlserver.sqlite3')
        self.conn = sqlite3.connect(filename)
        self.cursor = self.conn.cursor()
        self.conn.create_function("REGEXP", 2, regexp)
        #weechat.prnt('', '%surlserver: error reading database "%s"' % (weechat.prefix('error'), filename))
        try:
            self.cursor.execute('''CREATE TABLE urls
                             (number integer PRIMARY KEY AUTOINCREMENT,
                             time integer,
                             nick text,
                             buffer_name text,
                             url text,
                             message text,
                             prefix text)''')
            self.conn.commit()
        except sqlite3.OperationalError, e:
            # Table already exists
            pass

    def items(self, order_by='time', search='', page=1, amount=100):
        offset = page * amount - amount
        if urlserver_settings['msg_ignore_dup_urls'] == 'on':
            distinct = 'GROUP BY url'
        else:
            distinct = ''
        if search:
            search ='''
            WHERE
                buffer_name REGEXP '%s'
            OR
                url REGEXP '%s'
            OR
                message REGEXP '%s'
            OR
                nick REGEXP '%s'
                    ''' %(search, search, search, search)
        sql ='''
            SELECT
            url, number, time, nick, buffer_name, message, prefix
            FROM urls
            %s
            %s
            ORDER BY %s desc
            LIMIT %s OFFSET %s''' %(search, distinct, order_by, amount, offset)
        weechat.prnt('', 'urlserver: SQL: %s' % sql)
        execute = self.cursor.execute(sql)
        return self.cursor.fetchall()

    def get(self, number):
        execute = self.cursor.execute('''
            SELECT * FROM urls WHERE number = "%s"''' %number)
        row = self.cursor.fetchone()
        return row

    def insert(self, time, nick, buffer_name, url, message, prefix):
        nick = nick.decode('UTF-8')
        buffer_name = buffer_name.decode('UTF-8')
        url = url.decode('UTF-8')
        message = message.decode('UTF-8')
        execute = self.cursor.execute('''
            INSERT INTO urls
            VALUES (NULL, ?, ?, ?, ?, ?, ?)''',
            (time, nick, buffer_name, url, message, prefix))
        self.conn.commit()
        return self.cursor.lastrowid

    def close(self):
        self.conn.commit()
        self.cursor.close()
        self.conn.close()

    @property
    def rowcount(self):
        return self.cursor.rowcount

urlserver = {
    'socket'        : None,
    'hook_fd'       : None,
    'regex'         : re.compile(r'(\w+://(?:%s|%s)(?::\d+)?(?:/[^\])>\s]*)?)' % (url_domain, url_ipaddr), re.IGNORECASE),
    'buffer'        : '',
}

# script options
urlserver_settings_default = {
    # HTTP server settings
    'http_autostart'     : ('on', 'start the built-in HTTP server automatically)'),
    'http_hostname'      : ('', 'force hostname/IP in bind of socket (empty value = auto-detect current hostname)'),
    'http_hostname_display': ('', 'display this hostname in shortened URLs'),
    'http_port'          : ('', 'force port for listening (empty value = find a random free port)'),
    'http_port_display'  : ('', 'display this port in shortened URLs. Useful if you forward a different external port to the internal port'),
    'http_allowed_ips'   : ('', 'regex for IPs allowed to use server (example: "^(123.45.67.89|192.160.*)$")'),
    'http_auth'          : ('', 'login and password (format: "login:password") required to access to page with list of URLs'),
    'http_url_prefix'    : ('', 'prefix to add in URLs to prevent external people to scan your URLs (for example: prefix "xx" will give URL: http://host.com:1234/xx/8)'),
    'http_bg_color'      : ('#f4f4f4', 'background color for HTML page'),
    'http_fg_color'      : ('#000', 'foreground color for HTML page'),
    'http_css_url'       : ('', 'URL of external Cascading Style Sheet to add (BE CAREFUL: the HTTP referer will be sent to site hosting CSS file!) (empty value = use default embedded CSS)'),
    'http_embed_image'   : ('off', 'embed images in HTML page (BE CAREFUL: the HTTP referer will be sent to site hosting image!)'),
    'http_embed_youtube' : ('off', 'embed youtube videos in HTML page (BE CAREFUL: the HTTP referer will be sent to youtube!)'),
    'http_embed_youtube_size': ('480*350', 'size for embedded youtube video, format is "xxx*yyy"'),
    'http_prefix_suffix' : (' ', 'suffix displayed between prefix and message in HTML page'),
    'http_title'         : ('WeeChat URLs', 'title of the HTML page'),
    # message filter settings
    'msg_ignore_buffers' : ('core.weechat,python.grep', 'comma-separated list (without spaces) of buffers to ignore (full name like "irc.freenode.#weechat")'),
    'msg_ignore_tags'    : ('irc_quit,irc_part,notify_none', 'comma-separated list (without spaces) of tags (or beginning of tags) to ignore (for example, use "notify_none" to ignore self messages or "nick_weebot" to ignore messages from nick "weebot")'),
    'msg_require_tags'   : ('nick_', 'comma-separated list (without spaces) of tags (or beginning of tags) required to shorten URLs (for example "nick_" to shorten URLs only in messages from other users)'),
    'msg_ignore_regex'   : ('', 'ignore messages matching this regex'),
    'msg_ignore_dup_urls': ('off', 'ignore duplicated URLs (do not show an URL twice, will make the script slower)'),
    # display settings
    'color'              : ('darkgray', 'color for urls displayed'),
    'display_urls'       : ('on', 'display URLs below messages'),
    'url_min_length'     : ('0', 'minimum length for an URL to be shortened (0 = shorten all URLs, -1 = detect length based on shorten URL)'),
    'urls_amount'        : ('50', 'number of URLs to keep in memory (and in file when script is not loaded)'),
    'buffer_short_name'  : ('off', 'use buffer short name on dedicated buffer'),
    'debug'              : ('off', 'print some debug messages'),
}
urlserver_settings = {}

def base64_decode(s):
    if sys.version_info >= (3,):
        # python 3.x
        return base64.b64decode(s.encode('utf-8'))
    else:
        # python 2.x
        return base64.b64decode(s)

def base62_encode(number):
    """Encode a number in base62 (all digits + a-z + A-Z)."""
    base62chars = string.digits + string.ascii_letters
    l = []
    while number > 0:
        remainder = number % 62
        number = number // 62
        l.insert(0, base62chars[remainder])
    return ''.join(l) or '0'

def base62_decode(str_value):
    """Decode a base62 string (all digits + a-z + A-Z) to a number."""
    base62chars = string.digits + string.ascii_letters
    return sum([base62chars.index(char) * (62 ** (len(str_value) - index - 1)) for index, char in enumerate(str_value)])

def urlserver_short_url(number):
    """Return short URL with number."""
    global urlserver_settings
    hostname = urlserver_settings['http_hostname_display'] or urlserver_settings['http_hostname'] or socket.getfqdn()

    # If the built-in HTTP server isn't running, default to port from settings
    port = urlserver_settings['http_port']
    if len(urlserver_settings['http_port_display']) > 0:
        port = urlserver_settings['http_port_display']
    elif urlserver['socket']:
        port = urlserver['socket'].getsockname()[1]

    # Don't add :port if the port matches the default port for the http protocol, port 80
    prefixed_port = ':%s' % port
    if prefixed_port == ':80':
        prefixed_port = ''

    prefix = ''
    if urlserver_settings['http_url_prefix']:
        prefix = '%s/' % urlserver_settings['http_url_prefix']
    return 'http://%s%s/%s%s' % (hostname, prefixed_port, prefix, base62_encode(number))

def urlserver_server_reply(conn, code, extra_header, message, mimetype='text/html'):
    """Send a HTTP reply to client."""
    global urlserver_settings

    if extra_header:
        extra_header += '\r\n'
    s = 'HTTP/1.1 %s\r\n' \
        '%s' \
        'Content-Type: %s\r\n' \
        '\r\n' \
        % (code, extra_header, mimetype)# FIXME, len(message))
        #'Content-Length: %d\r\n' \ FIXME // this needs to be calculated after encoding
    msg = None
    if sys.version_info >= (3,):
        # python 3.x
        if type(message) is bytes:
            conn.send(s.encode('utf-8') + message)
            msg = s.encode('utf-8') + message
        else:
            conn.send(s.encode('utf-8') + message.encode('utf-8'))
    else:
        # python 2.x
        msg = s + message
    if urlserver_settings['debug'] == 'on':
        weechat.prnt('', 'urlserver: sending %d bytes' % len(msg))
    if type(msg) == type(u''):
        msg = msg.encode('utf-8')
    conn.sendall(msg)

def urlserver_server_favicon():
    """Return favicon for HTML page."""
    s = u'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH1wgcDwo4MOEy+AAAAB10' \
        'RVh0Q29tbWVudABDcmVhdGVkIHdpdGggVGhlIEdJTVDvZCVuAAADp0lEQVQ4y12TXUxbBRTH/733ttx+XFq+Ci2Ur8AEYSBIosnS+YJhauJY9mQyXfTBh8UEnclm1Gxq' \
        'YoJGfZkzqAkmQ2IicVOcwY1YyMZwWcfXVq2Ulpax3raX2y9ob29v7+31QViIJzkPJyfn//D7/48G+2r+6jzaO9oHFCjPCTkBM7MzF06eOhng/uHMFE2dUopKExthb3cf' \
        '6h4DUAAAar+A3WB/b21l7a3pW9NLPW099Vk+axn9aPRDkROvX3FdiRtpo9LX0XeMJMm/FUW5DQDE3vHSN0t9vhXfy+eGz00hjgk6TZfcWXajlq79ePLyZGLog6Gvm7XN' \
        'nPumO+50HnYAIB8J+P3cMzmL+oVAy1ZdRhdykA4bp6YT5z/79PjaVtDJ+ThxeHCYSOUzWn17eebs2fMvAWgBoCEAIBTiS1cDG81b8azZz/rrT4+f/qWm92D2wUY6H91O' \
        'VfFhvnFkZiQRKRWnNzfj4fn5RSOA0kcM4nwhHRckQRLFwoBx4Ljd3pD3eoKNNkeDoaDTSzIvM2cqz7zLJKsVylphG//ynd8B8ABUCgC8Xn+oxt5W7V2aS99JuANP9th6' \
        '9RtsUlbNjNZkk+5tTwRjmXisK1t5gJR1qsfjDu4K/Mdg7PtPuFSKzEWS6Xi6QTdlau9ZD4Y22EgkI7KxVEZqrVgwveC8nJX08vLKQhSAB4CAPZLJZLjY2fnqYCLBV6ga' \
        'ISuROdP9xRthhnkMeVGtIQijXGo+0JTZEYzXrg8vdB0u8/Yeakj57sWEPRvVCLuzIgg0XdW3fSySdHX4A7N3+a3sH2LOQlNka1ssmmwKP2T1BJkKOJ5ST/hXN50ACAIA' \
        'Pv+2W0+UT2WFrNFkLsmVRP0PxaefNehl5b5nZ8di0OjUGp3d5eCE0fX+18nauh7u+a4jhVcAmKnvrtnrWTY6bKwcrxILUtHe5CVaWtPKE/3ki8s3Lk1aLIiq8NrrD/os' \
        'ZfZIvdVBqWSKkoNzSgYAQ5gZ4bXNQNw0cZF/P8r6fq4zJ9ORkDTXXCdrkNZo+49eon8d41apbYGjZTVlJSmfSdKE3a7cVwBYqopWDEecupYTg+TQny53uK6qkPL8Jcw+' \
        '3sh0LjbL1jZbkbwwEtgmCW2C47X5GhOhXw9oWABhADL12w/qxSIpEz/9mI9JucIsw6hzxaK6tBMyVE9dTWbKrMqb01OoUyXdrQfhAvP2G3S5y1W4CyC5/xF1u63Zy0Z1' \
        'mZ7ejSv5v50OQMnujH8BbzDFpcdRAIIAAAAASUVORK5CYII='
    return base64_decode(s)

def urlserver_server_reply_list(conn, sort='-time', search='', page=1, amount=0):
    """Send list of URLs as HTML page to client."""
    global urlserver, urlserver_settings
    #
    # FIXME need to sqlify sorting
    #if not sort.startswith('-'):
    #    sort = '+%s' % sort
    #if sort[1:] == 'time':
    #    urls = sorted(urlserver['urls'].items())
    #else:
    #    idx = ['time', 'nick', 'buffer'].index(sort[1:])
    #    urls = sorted(urlserver['urls'].items(), key=lambda url: url[1][idx].lower())
    #if sort.startswith('-'):
    #    urls.reverse()
    sortkey = { '-': ('', '&uarr;'), '+': ('-', '&darr;') }
    prefix = ''
    content = ''
    if urlserver_settings['http_url_prefix']:
        prefix = '%s/' % urlserver_settings['http_url_prefix']
    for column, defaultsort in (('time', '-'), ('nick', ''), ('buffer', '')):
        if sort[1:] == column:
            content += '<div class="sortable sorted_by %s_header"><a href="/%s?sort=%s%s">%s</a> %s</div>' % (column, prefix, sortkey[sort[0]][0], column, column.capitalize(), sortkey[sort[0]][1])
        else:
            content += '<div class="sortable %s_header"><a class="sort_link" href="/%s?sort=%s%s">%s</a></div>' % (column, prefix, defaultsort, column, column.capitalize())

    content += '<div class="sortable"><form method="get"><input type="text" name="search" value="%s" placeholder="Search"></input></form></div>' %search

    amount = int(amount)
    if not amount:
        amount = int(urlserver_settings['urls_amount'])
    try:
        page = int(page)
    except:
        page = 1
    urls = urlserver['urls'].items(search=search, page=page, amount=amount)
    content = ['''<ul class="urls">
        <li class="bar">
            <h1><a href="/%s">%s</a>
            <span class="small">Showing %s URLs</span>
            <span>%s</span>
        </li>''' %(prefix, urlserver_settings['http_title'], len(urls), content) ]
    for item in urls:
        url = item[0]
        key = item[1]
        timestamp = item[2]
        nick = item[3]
        time = datetime.datetime.fromtimestamp(timestamp)
        buffer_name = item[4]
        if not nick: # Message without nick tag set, use prefix instead
            nick = item[6]

        obj = ''
        message = cgi.escape(item[5].replace(url, '\x01\x02\x03\x04')).split('\t', 1)
        strjoin = ' %s ' % urlserver_settings['http_prefix_suffix'].replace(' ', '&nbsp;')
        message = strjoin.join(message).replace('\x01\x02\x03\x04', '<a href="%s" title="%s">%s</a>' % (urlserver_short_url(key), url, url))
        if urlserver_settings['http_embed_image'] == 'on' and url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg')):
            obj = '<div class="obj"><img src="%s" title="%s" alt="%s"></div>' % (url, url, url)
        elif urlserver_settings['http_embed_youtube'] == 'on' and 'youtube.com/' in url:
            m = re.search('v=([\w\d]+)', url)
            if m:
                yid = m.group(1)
                try:
                    size = urlserver_settings['http_embed_youtube_size'].split('*')
                    width = int(size[0])
                    height = int(size[1])
                except:
                    width = 480
                    height = 350
                obj = '<div class="obj youtube"><iframe id="%s" type="text/html" width="%d" height="%d" ' \
                    'src="http://www.youtube.com/embed/%s?enablejsapi=1"></iframe></div>' % (yid, width, height, yid)
        content.append('<li class="url">')
        content.append('<h1>%s <span>%s</span>   <span class="small">%s</span></h1>%s %s' %(nick, buffer_name, time, message, obj))
        content.append('</li>')
    attrs = {
            'amount': amount,
            'search': search,
            'page': page+1,
        }
    content.append('<li><a id="nextpage" href="?%s" rel="next" accesskey="n">Next page</a></li>' %urllib.urlencode(attrs))
    content  = '\n'.join(content) + '\n</ul>'
    if len(urlserver_settings['http_css_url']) > 0:
        css = '<link rel="stylesheet" type="text/css" href="%s" />' % urlserver_settings['http_css_url']
    else:
        css = ''
    html = '''<!DOCTYPE html>
    <html lang="en">
        <head>
        <title>%s</title>
        <meta http-equiv="content-type" content="text/html; charset=utf-8" />
        <link rel="next" href="?page=%s">
        <script type="text/javascript">
            var nr = 2;
            var scroll = function(event) {
                if (event.keyCode == 32 || event.keyCode == 34  || event.charCode == 32 || event.charCode == 34) {
                   e = document.querySelector('li:nth-child('+nr+++')')
                   if (e) {
                        e.scrollIntoView(true);
                        Array.prototype.forEach.call(document.querySelectorAll('li'), function(li) {
                            li.classList.add('faded');
                        });
                        e.classList.remove('faded')
                   }else{
                        window.location = document.querySelector('#nextpage').href;
                    }
                   event.preventDefault();
                   return false;
                }
            }
        </script>
        <style type="text/css" media="screen">
        <!--
          html {
            font-family: "Helvetica Neue", Arial, Helvetica;
            background: #ddd;
            font-size: 13px;
            line-height: 1em;
            color: #333;
          }
          a {
            color: #00a5f0;
            text-decoration: none;
          }
          h1 {
              color: #222;
              font-size: 18px;
              font-weight: normal;
          }
          span {
            color: #999;
            font-size: 13px;
          }
          input {
            width: 120px;
            padding: 4px 9px;
            margin: 0px 2px 0 0;
            box-shadow: 2px 2px 3px #ccc inset;
            -webkit-border-radius: 15px;
            -moz-border-radius: 15px;
            -o-border-radius: 15px;
            border-radius: 15px;
            outline: none;
          }
          .sortable {
            float: right;
            padding: 1em;
          }
          .small {
            font-size: 9px;
          }
          .faded {
            opacity: 0.3;
          }
          .bar {
              background-color: #F4F4F4;
              border-radius: 5px 5px 0 0;
              -webkit-border-radius: 5px 5px 0 0;
              -moz-border-radius: 5px 5px 0 0;
              height: 43px;
              overflow: hidden;
              box-shadow: 0 1px #fff inset, 0 -1px #ddd inset;
              -moz-box-shadow: 0 1px #fff inset, 0 -1px #ddd inset;
              -webkit-box-shadow: 0 1px #fff inset, 0 -1px #ddd inset;
          }
          ul {
            width: auto;
          }
          img { max-width: 100%%; }
          li { list-style: none;
               background: white;
               padding: 1em;
          }
          li:nth-child(even) {background: #f9f9f9}
          div.obj { margin-top: 1em; }
        -->
        </style>
        %s
        </head>
        <body onkeypress="scroll(event)">
            %s
        </body>
        </html>''' % (urlserver_settings['http_title'], page+1, css, content)
    urlserver_server_reply(conn, '200 OK', '', html)

def urlserver_server_fd_cb(data, fd):
    """Callback for server socket."""
    global urlserver, urlserver_settings
    if not urlserver['socket']:
        return weechat.WEECHAT_RC_OK
    conn, addr = urlserver['socket'].accept()
    if urlserver_settings['debug'] == 'on':
        weechat.prnt('', 'urlserver: connection from %s' % str(addr))
    if urlserver_settings['http_allowed_ips'] and not re.match(urlserver_settings['http_allowed_ips'], addr[0]):
        if urlserver_settings['debug'] == 'on':
            weechat.prnt('', 'urlserver: IP not allowed')
        conn.close()
        return weechat.WEECHAT_RC_OK
    data = None
    try:
        conn.settimeout(0.3)
        data = conn.recv(4096).decode('utf-8')
        data = data.replace('\r\n', '\n')
    except:
        return weechat.WEECHAT_RC_OK
    replysent = False
    sort = '-time'
    search = ''
    m = re.search('^GET /(.*) HTTP/.*$', data, re.MULTILINE)
    if m:
        url = m.group(1)
        url = urlparse.urlparse(url)
        path = url.path
        if urlserver_settings['debug'] == 'on':
            weechat.prnt('', 'urlserver: %s' % m.group(0))
        if url.path == 'favicon.ico':
            extra = 'Date: Sat, 27 Sep 2003 00:00:00 GMT\r\n' \
                    'Last-Modified: Sat, 27 Sep 2003 00:00:00 GMT\r\n' \
                    'Expires: Wed, 15 Nov 2100 00:00:00 GMT\r\n'
            urlserver_server_reply(conn, '304 Not Modified', extra,
                                   urlserver_server_favicon(), mimetype='image/x-icon')
            replysent = True
        else:
            # check if prefix is ok (if prefix defined in settings)
            prefixok = True
            if urlserver_settings['http_url_prefix']:
                if url.path.startswith(urlserver_settings['http_url_prefix']):
                    path = path[len(urlserver_settings['http_url_prefix'])+1:]
                else:
                    prefixok = False
            if prefixok: # prefix ok, go on with url
                kwargs = dict(urlparse.parse_qsl(url.query))
                if len(path) > 1:
                    # short url, read base62 key and redirect to page
                    number = -1
                    try:
                        number = base62_decode(path)
                    except:
                        pass
                    if number >= 0:
                        # no redirection with "Location:" because it sends HTTP referer
                        #conn.send('HTTP/1.1 302 Found\nLocation: %s\n' % urlserver['urls'][number][2])
                        urlserver_server_reply(conn, '200 OK', '',
                                               '<meta http-equiv="refresh" content="0; url=%s">' % urlserver['urls'].get(number)[4])
                        replysent = True
                else: # page with list of urls
                    authok = True
                    if urlserver_settings['http_auth']:
                        auth = re.search('^Authorization: Basic (\S+)$', data, re.MULTILINE)
                        if not auth or base64_decode(auth.group(1)).decode('utf-8') != urlserver_settings['http_auth']:
                            authok = False
                    if authok:
                        urlserver_server_reply_list(conn, **kwargs)
                    else:
                        urlserver_server_reply(conn, '401 Authorization required',
                                               'WWW-Authenticate: Basic realm="%s"' % SCRIPT_NAME, '')
                    replysent = True
    if not replysent:
        urlserver_server_reply(conn,
                               '404 Not found', '',
                               '<html>\n'
                               '<head><title>Page not found</title></head>\n'
                               '<body><h1>Page not found</h1></body>\n'
                               '</html>')
    conn.close()
    return weechat.WEECHAT_RC_OK

def urlserver_server_status():
    """Display status of server."""
    global urlserver
    if urlserver['socket']:
        host, port = urlserver['socket'].getsockname()
        user = urlserver_settings['http_auth']
        if user:
            user = user.split(':')[0]+'@'
        prefix = urlserver_settings['http_url_prefix']
        weechat.prnt('', 'URL server serving requests at http://%s%s:%s/%s' % (user, host, port, prefix))
    else:
        weechat.prnt('', 'URL server not running')

def urlserver_server_start():
    """Start mini HTTP server."""
    global urlserver, urlserver_settings
    if urlserver['socket']:
        weechat.prnt('', 'URL server already running')
        return
    port = 0
    try:
        port = int(urlserver_settings['http_port'])
    except:
        port = 0
    urlserver['socket'] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    urlserver['socket'].setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        urlserver['socket'].bind((urlserver_settings['http_hostname'] or socket.getfqdn(), port))
    except Exception as e:
        weechat.prnt('', '%sBind error: %s' % (weechat.prefix('error'), e))
        urlserver['socket'] = None
        urlserver_server_status()
        return
    urlserver['socket'].listen(5)
    urlserver['hook_fd'] = weechat.hook_fd(urlserver['socket'].fileno(), 1, 0, 0, 'urlserver_server_fd_cb', '')
    urlserver_server_status()

def urlserver_server_stop():
    """Stop mini HTTP server."""
    global urlserver
    if urlserver['socket'] or urlserver['hook_fd']:
        if urlserver['socket']:
            urlserver['socket'].close()
            urlserver['socket'] = None
        if urlserver['hook_fd']:
            weechat.unhook(urlserver['hook_fd'])
            urlserver['hook_fd'] = None
        weechat.prnt('', 'URL server stopped')

def urlserver_server_restart():
    """Restart mini HTTP server."""
    urlserver_server_stop()
    urlserver_server_start()

def urlserver_display_url_detail(key):
    global urlserver
    url = urlserver['urls'].get(key)
    nick = url[1]
    if nick:
        nick += ' @ '
    weechat.prnt_date_tags(urlserver['buffer'], 0, 'notify_none',
                           '%s, %s%s%s%s: %s%s%s -> %s' % (url[0],
                                                           nick,
                                                           weechat.color('chat_buffer'),
                                                           url[2],
                                                           weechat.color('reset'),
                                                           weechat.color(urlserver_settings['color']),
                                                           urlserver_short_url(key),
                                                           weechat.color('reset'),
                                                           url[3]))

def urlserver_buffer_input_cb(data, buffer, input_data):
    if input_data in ('q', 'Q'):
        weechat.buffer_close(buffer)
    return weechat.WEECHAT_RC_OK

def urlserver_buffer_close_cb(data, buffer):
    global urlserver
    urlserver['buffer'] = ''
    return weechat.WEECHAT_RC_OK

def urlserver_open_buffer():
    global urlserver, urlserver_settings
    if not urlserver['buffer']:
        urlserver['buffer'] = weechat.buffer_new(SCRIPT_BUFFER,
                                                 'urlserver_buffer_input_cb', '',
                                                 'urlserver_buffer_close_cb', '')
    if urlserver['buffer']:
        weechat.buffer_set(urlserver['buffer'], 'title', 'urlserver')
        weechat.buffer_set(urlserver['buffer'], 'localvar_set_no_log', '1')
        weechat.buffer_set(urlserver['buffer'], 'time_for_each_line', '0')
        weechat.buffer_set(urlserver['buffer'], 'print_hooks_enabled', '0')
        weechat.buffer_clear(urlserver['buffer'])
        urls = urlserver['urls'].items()
        for url in urls:
            key = url[0]
            urlserver_display_url_detail(key)
        weechat.buffer_set(urlserver['buffer'], 'display', '1')

def urlserver_cmd_cb(data, buffer, args):
    """The /urlserver command."""
    global urlserver
    if args == 'start':
        urlserver_server_start()
    elif args == 'restart':
        urlserver_server_restart()
    elif args == 'stop':
        urlserver_server_stop()
    elif args == 'status':
        urlserver_server_status()
    elif args == 'clear':
        #urlserver['urls'] = {}
        #urlserver['number'] = 0
        #weechat.prnt('', 'urlserver: list cleared')
        weechat.prnt('', 'urlserver: clearing not implemented')
    else:
        urlserver_open_buffer()
    return weechat.WEECHAT_RC_OK

def urlserver_print_cb(data, buffer, time, tags, displayed, highlight, prefix, message):
    """Callback for messages printed in buffers."""
    global urlserver, urlserver_settings

    buffer_full_name = '%s.%s' % (weechat.buffer_get_string(buffer, 'plugin'), weechat.buffer_get_string(buffer, 'name'))
    if urlserver_settings['buffer_short_name'] == 'on':
        buffer_name = weechat.buffer_get_string(buffer, 'short_name')
    else:
        buffer_name = buffer_full_name

    listtags = tags.split(',')

    # skip ignored buffers
    if urlserver_settings['msg_ignore_buffers']:
        if buffer_full_name in urlserver_settings['msg_ignore_buffers'].split(','):
            return weechat.WEECHAT_RC_OK

    # skip ignored tags
    if urlserver_settings['msg_ignore_tags']:
        for itag in urlserver_settings['msg_ignore_tags'].split(','):
            for tag in listtags:
                if tag.startswith(itag):
                    return weechat.WEECHAT_RC_OK

    # exit if a required tag is missing
    if urlserver_settings['msg_require_tags']:
        for rtag in urlserver_settings['msg_require_tags'].split(','):
            tagfound = False
            for tag in listtags:
                if tag.startswith(rtag):
                    tagfound = True
                    break
            if not tagfound:
                return weechat.WEECHAT_RC_OK

    # ignore message is matching the "msg_ignore_regex"
    if urlserver_settings['msg_ignore_regex']:
        if re.search(urlserver_settings['msg_ignore_regex'], prefix + '\t' + message):
            return weechat.WEECHAT_RC_OK

    # extract nick from tags
    nick = ''
    for tag in listtags:
        if tag.startswith('nick_'):
            nick = tag[5:]
            break

    # get URL min length
    min_length = 0
    try:
        min_length = int(urlserver_settings['url_min_length'])
        # Detect the minimum length based on shorten url length
        if min_length == -1:
            min_length = len(urlserver_short_url(urlserver['number'])) + 1
    except:
        min_length = 0

    # shorten URL(s) in message
    for url in urlserver['regex'].findall(message):
        if len(url) >= min_length:
            number = urlserver['urls'].insert(time, nick, buffer_name, url, message, prefix)
            if urlserver_settings['display_urls'] == 'on':
                weechat.prnt_date_tags(buffer, 0, 'no_log,notify_none', '%s%s' % (weechat.color(urlserver_settings['color']), urlserver_short_url(number)))
            if urlserver['buffer']:
                urlserver_display_url_detail(number)

    return weechat.WEECHAT_RC_OK

def urlserver_config_cb(data, option, value):
    """Called when a script option is changed."""
    global urlserver_settings
    pos = option.rfind('.')
    if pos > 0:
        name = option[pos+1:]
        if name in urlserver_settings:
            if name == 'http_allowed_ips':
                urlserver_settings[name] = re.compile(value)
            else:
                urlserver_settings[name] = value
                if name in ('http_hostname', 'http_port'):
                    urlserver_server_restart()
                    # Don't restart if autostart is disabled and server isn't already running
                    if urlserver_settings['http_autostart'] == 'on' or urlserver['socket']:
                        urlserver_server_restart()
    return weechat.WEECHAT_RC_OK


def urlserver_write_urls():
    """Write file with URLs."""
    global urlserver
    urlserver['urls'].close()

def urlserver_end():
    """Script unloaded (oh no, why?)"""
    urlserver_server_stop()
    urlserver_write_urls()
    return weechat.WEECHAT_RC_OK

if __name__ == '__main__' and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                        SCRIPT_DESC, 'urlserver_end', ''):
        # set default settings
        version = weechat.info_get('version_number', '') or 0
        for option, value in urlserver_settings_default.items():
            if weechat.config_is_set_plugin(option):
                urlserver_settings[option] = weechat.config_get_plugin(option)
            else:
                weechat.config_set_plugin(option, value[0])
                urlserver_settings[option] = value[0]
            if int(version) >= 0x00030500:
                weechat.config_set_desc_plugin(option, '%s (default: "%s")' % (value[1], value[0]))

        # detect config changes
        weechat.hook_config('plugins.var.python.%s.*' % SCRIPT_NAME, 'urlserver_config_cb', '')

        # add command
        weechat.hook_command(SCRIPT_COMMAND, SCRIPT_DESC, 'start|restart|stop|status || clear',
                             '  start: start server\n'
                             'restart: restart server\n'
                             '   stop: stop server\n'
                             ' status: display status of server\n'
                             '  clear: remove all URLs from list\n\n'
                             'Without argument, this command opens new buffer with list of URLs.\n\n'
                             'Initial setup:\n'
                             '  - by default, script will listen on a random free port, you can force a port with:\n'
                             '      /set plugins.var.python.urlserver.http_port "1234"\n'
                             '  - you can force an IP or custom hostname with:\n'
                             '      /set plugins.var.python.urlserver.http_hostname "111.22.33.44"\n'
                             '  - it is strongly recommended to restrict IPs allowed and/or use auth, for example:\n'
                             '      /set plugins.var.python.urlserver.http_allowed_ips "^(123.45.67.89|192.160.*)$"\n'
                             '      /set plugins.var.python.urlserver.http_auth "user:password"\n'
                             '  - if you do not like the default HTML formatting, you can override the CSS:\n'
                             '      /set plugins.var.python.urlserver.http_css_url "http://example.com/sample.css"\n'
                             '      See https://raw.github.com/FiXato/weechat_scripts/master/urlserver/sample.css\n'
                             '  - don\'t like the built-in HTTP server to start automatically? Disable it:\n'
                             '      /set plugins.var.python.urlserver.http_autostart "off"\n'
                             '  - have external port 80 forwarded to your internal server port? Remove :port with:\n'
                             '      /set plugins.var.python.urlserver.http_port_display "80"\n'
                             '\n'
                             'Tip: use URL without key at the end to display list of all URLs in your browser.',
                             'start|restart|stop|status|clear', 'urlserver_cmd_cb', '')

        # start mini HTTP server
        if urlserver_settings['http_autostart'] == 'on':
            # start mini HTTP server
            urlserver_server_start()

        # init db
        urlserver['urls'] = urldb()

        # catch URLs in buffers
        weechat.hook_print("", "", "://", 1, "urlserver_print_cb", "")

        # search buffer
        urlserver['buffer'] = weechat.buffer_search('python', SCRIPT_BUFFER)
