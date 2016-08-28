###
# Copyright (c) 2013, 2014, 2015, 2016 Peter Palfrader <peter@palfrader.org>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from bs4 import BeautifulSoup
import os
import re
import subprocess
import time
import urllib.request, urllib.error, urllib.parse
import fnmatch
import supybot.log as log

class BaseProvider(object):
    minRepeat = 1800
    defaultRE = '(?<!\w)#([0-9]{4,})(?:(?=\W)|$)'
    debugChannels = ['#*-test']

    def __init__(self, name, fixup=None, prefix=None, default_re=None, postfix=None):
        self.name = name
        self.fixup = fixup
        self.prefix = prefix
        self.postfix = postfix
        if default_re is None and self.prefix is not None:
            self.re = r'(?i)(?<!\w)'+self.prefix+r'#([0-9]{2,})(?:(?=\W)|$)'
        else:
            self.re = default_re
        self.channels = {}
        self.lastSent = {}

    def __getitem__(self, ticketnumber):
        title = self._gettitle(ticketnumber)
        title = re.sub('\s+', ' ', title).strip()

        if self.fixup is not None:
            title = self.fixup(ticketnumber, title)
        if self.prefix is not None:
            title = self.prefix + title
        if self.postfix is not None:
            title = title + self.postfix%(ticketnumber)

        return title

    def matches(self, msg):
        if self.re is None: return []

        return re.findall(self.re, msg)

    def addChannel(self, channel, regex=None, default=False):
        """Adds a dedicated trigger regex for this provider for a channel"""
        if channel in self.channels:
            log.warning("[%s] re-adding %s"%(self.name, channel))
        self.channels[channel] = { 're': regex, 'default': default }

    def _do_log(self, tgt):
        for d in self.debugChannels:
            if fnmatch.fnmatch(tgt, d):
                return True
        return False

    def doPrivmsg(self, tgt, msg):
        if self._do_log(tgt): log.debug("[%s][%s] in doPrivmsg %s"%(self.name, tgt, msg))
        matches = []
        matches += self.matches(msg)

        for key in self.channels:
            if fnmatch.fnmatch(tgt, key):
                ch = self.channels[key]

                if ch['default']:
                    if self._do_log(tgt): log.debug("[%s][%s] checking default regex for %s: %s %s"%(self.name, tgt, key, self.defaultRE, msg))
                    matches += re.findall(self.defaultRE, msg)
                if ch['re'] is not None:
                    if self._do_log(tgt): log.debug("[%s][%s] checking extra regex for %s: %s %s"%(self.name, tgt, key, ch['re'], msg))
                    matches += re.findall(ch['re'], msg)

        if self._do_log(tgt): log.debug("[%s] matches: %s"%(self.name, matches))
        for m in matches:
            if (tgt,m) in self.lastSent and \
                self.lastSent[(tgt,m)] >= time.time() - self.minRepeat:
                log.debug("[%s][%s] rate limited match %s"%(self.name, tgt, m))
                continue

            try:
                item = self[m]
            except IndexError:
                log.debug("[%s][%s] failed to lookup %s"%(self.name, tgt, m))
                continue

            if self._do_log(tgt): log.debug("[%s][%s] sending for %s: %s"%(self.name, tgt, m, item))
            self.lastSent[(tgt,m)] = time.time()
            yield item


class TicketHtmlTitleProvider(BaseProvider):
    """A ticket information provider that extracts the title
       tag from html pages at $url$ticketnumber."""
    def __init__(self, name, url, fixup=None, prefix=None, default_re=None, postfix=None):
        """Constructs a ticket html title provider.

        :param url The base url where to find tickets.  The document at
                   ${url}${ticketnumber} should have the appropriate title.
        :param fixup a function that takes a string (the title) and returns
                     another string we like better for printing.
        """
        BaseProvider.__init__(self, name, fixup, prefix=prefix, default_re=default_re, postfix=postfix)

        self.url = url

    def _gettitle(self, ticketnumber):
        try:
            response = urllib.request.urlopen('%s%s'%(self.url, ticketnumber))
        except urllib.error.HTTPError as e:
            raise IndexError(e)

        data = response.read()

        charset = response.headers.getparam('charset')
        if charset: data = data.decode(charset)

        soup = BeautifulSoup(data, 'html.parser')
        title = soup.title.string
        return title

class TorProposalProvider(BaseProvider):
    def __init__(self, name, fixup=None, prefix=None, default_re=None, postfix=None):
        BaseProvider.__init__(self, name, fixup,  prefix=prefix, default_re=default_re, postfix=postfix)

        self.url = 'https://gitweb.torproject.org/torspec.git/tree/proposals/000-index.txt'

        self.expire = 0
        self.data = None
        self.update()

    def update(self):
        if self.expire > time.time(): return

        try:
            response = urllib.request.urlopen(self.url)
        except:
            return

        data = response.read()

        charset = response.headers.getparam('charset')
        if charset: data = data.decode(charset)

        self.data = data
        self.expire = time.time() + 7200


    def _gettitle(self, ticketnumber):
        self.update()
        if self.data is None:
            raise IndexError("No proposal index available.")

        m = re.search('^%s\s*(.*)'%(ticketnumber,), self.data, flags=re.MULTILINE)
        if m is None:
            raise IndexError("Proposal not found.")

        title = m.group(1)

        return title

class TicketRTProvider(BaseProvider):
    """A ticket information provider that returns the title
       of a request-tracker ticket."""
    def __init__(self, name, rtconfigpath, fixup=None, prefix=None, default_re=None, postfix=None):
        BaseProvider.__init__(self, name, fixup, prefix=prefix, default_re=default_re, postfix=postfix)

        self.rtrc = os.path.abspath( os.path.expanduser( rtconfigpath) )

    def _gettitle(self, ticketnumber):
        ticketnumber = int(ticketnumber)
        try:
            title = subprocess.check_output(['rt', 'ls', '-i', str(ticketnumber), '-s'], env={ 'RTCONFIG': self.rtrc } )
        except subprocess.CalledProcessError as e:
            raise IndexError(e)
        if title == "No matching results.\n":
            raise IndexError(title)

        return title



class ReGroupFixup:
    def __init__(self, groupre):
        self.groupre = groupre

    def __call__(self, i, x):
        m = re.match(self.groupre, x)
        if m and len(m.groups()) > 0: x = m.group(1)
        return "#%s: %s"%(i, x)

# vim:set shiftwidth=4 softtabstop=4 expandtab:
