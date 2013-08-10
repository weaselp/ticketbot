###
# Copyright (c) 2013, Peter Palfrader <peter@palfrader.org>
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

import BeautifulSoup
import os
import re
import subprocess
import time
import urllib2

class BaseProvider():
    def __init__(self, fixup=None, prefix=None, default_re=None):
        self.fixup = fixup
        self.prefix = prefix
        if default_re is None and self.prefix is not None:
            self.re = r'(?i)(?<!\w)'+self.prefix+r'#([0-9]{2,})(?:(?=\W)|$)'
        else:
            self.re = default_re

    def __getitem__(self, ticketnumber):
        title = self._gettitle(ticketnumber)
        title = re.sub('\s+', ' ', title).strip()

        if self.fixup is not None:
            title = self.fixup(ticketnumber, title)
        if self.prefix is not None:
            title = self.prefix + title

        return title

    def matches(self, msg):
        if self.prefix is None: return

        return re.findall(self.re, msg)

class TicketHtmlTitleProvider(BaseProvider):
    """A ticket information provider that extracts the title
       tag from html pages at $url$ticketnumber."""
    def __init__(self, url, fixup=None, prefix=None, default_re=None):
        """Constructs a ticket html title provider.

        :param url The base url where to find tickets.  The document at
                   ${url}${ticketnumber} should have the appropriate title.
        :param fixup a function that takes a string (the title) and returns
                     another string we like better for printing.
        """
        BaseProvider.__init__(self, fixup, prefix, default_re)

        self.url = url

    def _gettitle(self, ticketnumber):
        try:
            response = urllib2.urlopen('%s%s'%(self.url, ticketnumber))
        except urllib2.HTTPError as e:
            raise IndexError(e)

        data = response.read()

        charset = response.headers.getparam('charset')
        if charset: data = data.decode(charset)

        b = BeautifulSoup.BeautifulSoup(data, convertEntities=BeautifulSoup.BeautifulSoup.HTML_ENTITIES)
        title = b.find('title').contents[0]
        return title

class TorProposalProvider(BaseProvider):
    def __init__(self, fixup=None, prefix=None, default_re=None):
        BaseProvider.__init__(self, fixup, prefix, default_re)

        self.url = 'https://gitweb.torproject.org/torspec.git/blob_plain/HEAD:/proposals/000-index.txt'

        self.expire = 0
        self.data = None
        self.update()

    def update(self):
        if self.expire > time.time(): return

        try:
            response = urllib2.urlopen(self.url)
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
    def __init__(self, rtconfigpath, fixup=None, prefix=None, default_re=None):
        BaseProvider.__init__(self, fixup, prefix, default_re)

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


class TicketChannel():
    """Dispatcher and rate limiter for per-channel ticketing info"""

    def __init__(self, minRepeat=1800):
        self.providers = []
        self.minRepeat = minRepeat
        self.lastSent = {}

    def addProvider(self, regex, provider):
        """Adds provider triggered by regex to this channel"""
        self.providers.append( { 're': regex, 'provider': provider } )

    def doPrivmsg(self, msg):
        for p in self.providers:
            matches = p['provider'].matches(msg)
            if matches is None: matches = []
            if p['re'] is not None: matches += re.findall(p['re'], msg)
            for m in matches:
                try:
                    item = p['provider'][m]
                except IndexError:
                    continue

                if m in self.lastSent and \
                    self.lastSent[m] >= time.time() - self.minRepeat:
                    continue

                self.lastSent[m] = time.time()
                yield item

class ReGroupFixup:
    def __init__(self, groupre):
        self.groupre = groupre

    def __call__(self, i, x):
        m = re.match(self.groupre, x)
        if m and len(m.groups()) > 0: x = m.group(1)
        return "#%s: %s"%(i, x)

# vim:set shiftwidth=4 softtabstop=4 expandtab:
