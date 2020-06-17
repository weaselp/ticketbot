###
# Copyright (c) 2013, 2014, 2015, 2016, 2020 Peter Palfrader <peter@palfrader.org>
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
    """A base for most ticket information providers."""
    minRepeat = 1800
    defaultRE = '(?<!\w)#([0-9]{4,})(?:(?=\W)|$)'
    debugChannels = ['#*-test']

    def __init__(self, name, fixup=None, prefix=None, default_re=None, postfix=None, status_finder=None):
        """Constructs a base base information provider.

        Child classes are then expected to implement _gettitle().

        :param name A name for this provider that identifies it for logging purposes.
        :param fixup A function that takes a ticketnumber, string (the title), and maybe an extra keyworad
                     and returns another string we like better for printing.
                     This is a more powerful solution than just setting
                     prefix/postfix.  If prefix/postfix are given, and a fixup,
                     prefix/postfix is done after.
        :param prefix A string to add to the front of the text we print.
                      If no default_re is provided, we built one from
                      prefix#<bugnumber>.
        :param postfix A format string to append to the text we print.  The one
                       %s in the string is passed the ticketnumber.
        :param status_finder A function (taking ticketnumber, *args, **kwargs)
                            which provides a ticket's status to add to the
                            title.  One of the kwargs is "extra" and holds
                            the dict returned from _gettitle() if it was a dict.
        :param default_re A regex to match.  Should have one matched group that is
                          the ticketnumber.  If it has more than one group,
                          then ticketnumbers are tuples, and the gettitle() and
                          fixup need to handle this in the derived class.
        """
        self.name = name
        self.fixup = fixup
        self.prefix = prefix
        self.postfix = postfix
        self.status_finder = status_finder
        if default_re is None and self.prefix is not None:
            self.re = r'(?i)(?<!\w)'+self.prefix+r'#([0-9]{2,})(?:(?=\W)|$)'
        else:
            self.re = default_re
        self.channels = {}
        self.lastSent = {}

    def fixup_title(self, title, ticketnumber, *args, **kwargs):
        """Cleans up title for printing:
           Replaces multiple-whitespaces with a single space, adds prefix and
           postfix and then calls the user-supplied fixup function if
           provided."""

        title = re.sub('\s+', ' ', title).strip()

        if self.fixup is not None:
            title = self.fixup(ticketnumber, title, *args, **kwargs)

        if self.prefix is not None:
            title = self.prefix + title
        if self.postfix is not None:
            title = title + self.postfix%(ticketnumber)

        return title

    def _gettitle(self, ticketnumber, *args, **kwargs):
        """Return a string for ticketnumber, or a dict with at least
           a 'title' element that is a string.
           The dict is then handed to status_finder to provide extra info.

        Should be overridden by descendants.
        """
        assert(False)

    def __getitem__(self, ticketnumber):
        """Get information about ticket ticketnumber.  Ticketnumber
           usually is a string, but it does not have to.

           If it is not a string, then the dict is passed on to
           gettitle and fixup as an 'extra' keyword.
           """
        title = self._gettitle(ticketnumber)

        kwargs = {}
        if isinstance(title, dict):
            kwargs['extra'] = title
            title = title['title']
        assert isinstance(title, str)

        title = self.fixup_title(title, ticketnumber, **kwargs)

        if self.status_finder is not None:
            status = self.status_finder(ticketnumber, **kwargs)
            if status is not None:
                title = "%s - [%s]" % (title, status)

        return title

    def matches(self, msg):
        """Return all matches (from re.findall) of this provider for this msg."""
        if self.re is None: return []

        return re.findall(self.re, msg)

    def addChannel(self, channel, regex=None, default=False):
        """Adds a dedicated trigger regex for this provider for a channel.

        If default is set, this provider will match on #nnnn in this channel.
        At most one provider should be the default provider in any channel."""
        if channel in self.channels:
            log.warning("[%s] re-adding %s"%(self.name, channel))
        self.channels[channel] = { 're': regex, 'default': default }

    def _do_log(self, tgt):
        for d in self.debugChannels:
            if fnmatch.fnmatch(tgt, d):
                return True
        return False

    def doPrivmsg(self, tgt, msg):
        """Handle msg for channel/target tgt.

        This collects all the matches from the default_re and any channel
        specific matches (default or channel specific regex).

        Then it goes through all the matches, collects the information and
        sends it to the target.
        """

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
        if len(matches) >= 4:
            log.debug("[%s] skipping because too many matches (%d)"%(len(matches),))
            return
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

def TracStatusExtractor(ticketnumber, extra):
    """Extracts the status of a trac ticket from the bugnumber and soup (as returned by gettitle)
    """
    span = extra['soup'].find_all('span', {'class' : 'trac-status'})
    if span:
        return span[0].a.get_text()
    else:
        return None

def GitLabStatusExtractor(ticketnumber, extra):
    """Extracts the status of a gitlab issue from the (path, bugnumber) and soup (as returned by gettitle)
    """
    page_header = extra['soup'].find_all('div', {'class': 'detail-page-header'})
    if len(page_header) != 1: return None
    page_header = page_header[0]

    visible_box = [box for box in page_header.find_all('div', {'class': 'status-box'}) if not 'hidden' in box['class']]
    if len(visible_box) != 1: return None
    visible_box = visible_box[0]

    return visible_box.get_text().strip()

class TicketHtmlTitleProvider(BaseProvider):
    """A ticket information provider that extracts the title
       tag from html pages at $url$ticketnumber."""

    def __init__(self, name, url, *args, **kwargs):
        """Constructs a ticket html title provider.

        :param url The base url where to find tickets.  The document at
                   ${url}${ticketnumber} should have the appropriate title.
        """
        BaseProvider.__init__(self, name, *args, **kwargs)
        self.url = url

    def _gettitle(self, ticketnumber, url=None):
        """Get the html title from the url given in the class or overridden on call."""
        try:
            response = urllib.request.urlopen('%s%s'%(url or self.url, ticketnumber))
        except urllib.error.HTTPError as e:
            raise IndexError(e)

        data = response.read()

        charset = response.info().get_content_charset()
        if charset: data = data.decode(charset)

        soup = BeautifulSoup(data, 'html.parser')
        title = soup.title.string

        res = {}
        res['title'] = title
        res['soup'] = soup
        return res


class GitlabTitleProvider(TicketHtmlTitleProvider):
    """A ticket information provider that extracts the title
       tag from GitLab issues at $url/$path/-/issues/$ticketnumber."""

    def __init__(self, name, url, *args, **kwargs):
        """Constructs a gitlab title provider.

           If fixup is not provided, we use a gitlab specific one.
        """
        if 'fixup' not in kwargs:
            kwargs['fixup'] = GitlabTitleProvider.gitlab_fixup

        TicketHtmlTitleProvider.__init__(self, name, url, *args, **kwargs)

    @staticmethod
    def gitlab_fixup(ticketnumber, title, extra):
        """Constructs the string given all the info from _gettitle
        """
        m = re.match('(.*?)\s*(?:\(#[0-9]+\)) \S{1,2} Issues \S{1,2} .+(?: / .+) \S{1,2} GitLab$', title)
        if m and len(m.groups()) > 0: title = m.group(1)

        # the url and ticketnumber can be added via a postfix, we do not need it here
        #res = '%s#%s: %s - %s%s'%(extra['path'], extra['ticketnumber'], title, extra['url'], extra['ticketnumber'])
        res = '%s#%s: %s'%(extra['path'], extra['ticketnumber'], title)
        return res

    def _gettitle(self, ticketnumber):
        path, ticketnumber = ticketnumber
        url = '%s%s/-/issues/' % (self.url, path)
        res = super()._gettitle(ticketnumber, url=url)
        res['url'] = url
        res['path'] = path
        res['ticketnumber'] = ticketnumber
        return res

class TorProposalProvider(BaseProvider):
    """Get information on tor proposals from gitweb.torproject.org"""

    def __init__(self, name, *args, **kwargs):
        BaseProvider.__init__(self, name, *args, **kwargs)

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

        charset = response.info().get_content_charset()
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
    def __init__(self, name, rtconfigpath, *args, **kwargs):
        """Constructs a RT title provider.

        Uses the command line 'rt' client.

        :param rtconfigpath Path to a config for the RT containing server
                            url, user, and passwd.  This path is passed
                            on to 'rt' as in an RTCONFIG environment variable.
        """
        BaseProvider.__init__(self, name, *args, **kwargs)

        self.rtrc = os.path.abspath( os.path.expanduser( rtconfigpath) )

    def _gettitle(self, ticketnumber):
        ticketnumber = int(ticketnumber)
        try:
            rtclientouput = subprocess.check_output(['rt', 'ls', '-i', str(ticketnumber), '-s'], env={ 'RTCONFIG': self.rtrc } )
        except subprocess.CalledProcessError as e:
            raise IndexError(e)

        title = rtclientouput.decode('utf-8').split('\n')[0]

        if title == "No matching results.":
            raise IndexError(title)

        return title

class ReGroupFixup:
    """A callable object that extracts a more appropriate string from ticket info

    Given a ticket string and a ticket number, returns #<number>: #<x>,
    where x is the first match group of the regex on the given string,
    or the given string if no match (group) exists.
    """

    def __init__(self, groupre):
        self.groupre = groupre

    def __call__(self, i, x, extra=None):
        m = re.match(self.groupre, x)
        if m and len(m.groups()) > 0: x = m.group(1)
        return "#%s: %s"%(i, x)

# vim:set shiftwidth=4 softtabstop=4 expandtab:
