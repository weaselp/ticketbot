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

import tickethelpers as h
reload(h)

class TicketConfig:
    def _add(self, ch, *args):
        if not ch in self.channels:
            self.channels[ch] = h.TicketChannel()
        self.channels[ch].addProvider(*args)

    def __init__(self):
        self.providers = {}
        self.providers['trac.torproject.org'] = h.TicketHtmlTitleProvider(
            'https://trac.torproject.org/projects/tor/ticket/',
            h.ReGroupFixup('.*?\((.*)\).*? Tor Bug Tracker & Wiki$')
            )
        self.providers['proposal.torproject.org'] = h.TorProposalProvider(
            fixup=lambda i,x: "Prop#%s: %s"%(i,x) )
        self.providers['github.com-tor-ooni-probe-pull'] = h.TicketHtmlTitleProvider(
            'https://github.com/TheTorProject/ooni-probe/pull/',
            h.ReGroupFixup('.*?(.*) . Pull Request #[0-9]+ . TheTorProject/ooni-probe . GitHub$', "PR")
            )
        self.providers['bugs.debian.org'] = h.TicketHtmlTitleProvider(
            'http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=',
            h.ReGroupFixup('#[0-9]+ - (.*) - Debian Bug report logs$')
            )
        self.providers['rt.debian.org'] = h.TicketRTProvider(
            '~/.rtrc-debian',
            h.ReGroupFixup('[0-9]+: *(.*)$', 'RT')
            )
        self.providers['bts.grml.org'] = h.TicketHtmlTitleProvider(
            'http://bts.grml.org/grml/issue',
            h.ReGroupFixup('Issue [0-9]+: (.*) - GRML issue tracker$')
            )
        self.providers['munin-monitoring.org'] = h.TicketHtmlTitleProvider(
            'http://munin-monitoring.org/ticket/',
            h.ReGroupFixup('.*?\((.*)\).*? Munin$')
            )
        self.providers['launchpad.net/ubuntu'] = h.TicketHtmlTitleProvider(
            'https://bugs.launchpad.net/ubuntu/+bug/',
            h.ReGroupFixup('Bug #[0-9]+ "(.*)" : Bugs :')
            )
        self.providers['bugzilla.redhat.com'] = h.TicketHtmlTitleProvider(
            'https://bugzilla.redhat.com/show_bug.cgi?id=',
            h.ReGroupFixup('Bug [0-9]+ .ndash; (.*)$')
            )

        self.channels = {}
        for tor in ('#ooni', '#nottor', '#tor-dev', '#tor'):
            self._add(tor, '(?<!\w)(?:#|https://trac.torproject.org/projects/tor/ticket/)([0-9]{4,})(?:(?=\W)|$)', self.providers['trac.torproject.org'])
            self._add(tor, '(?<!\w)[Pp]rop#([0-9]+)(?:(?=\W)|$)', self.providers['proposal.torproject.org'])

        self._add('#ooni', '(?<!\w)(?:PR#|https://github.com/TheTorProject/ooni-probe/pull/)([0-9]+)(?:(?=\W)|$)', self.providers['github.com-tor-ooni-probe-pull'])

        self._add('#munin', '(?<!\w)[dD](?:eb)?(?:ian)?#([0-9]{4,})(?:(?=\W)|$)', self.providers['bugs.debian.org'])
        self._add('#munin', '(?<!\w)[uU]#([0-9]{4,})(?:(?=\W)|$)', self.providers['launchpad.net/ubuntu'])
        self._add('#munin', '(?<!\w)[rR]#([0-9]{4,})(?:(?=\W)|$)', self.providers['bugzilla.redhat.com'])
        self._add('#munin', '(?<!\w)#([0-9]{4,})(?:(?=\W)|$)', self.providers['munin-monitoring.org'])

        self._add('#tor-test', '(?<!\w)[dD]eb(?:ian)?#([0-9]{4,})(?:(?=\W)|$)', self.providers['bugs.debian.org'])
        self._add('#tor-test', '(?<!\w)#([0-9]{4,})(?:(?=\W)|$)', self.providers['munin-monitoring.org'])

# vim:set shiftwidth=4 softtabstop=4 expandtab:
