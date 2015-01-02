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
    def _setup_providers(self):
        p = []
        p.append( h.TicketHtmlTitleProvider( 'trac.torproject.org',
            'https://trac.torproject.org/projects/tor/ticket/',
            h.ReGroupFixup('.*?\((.*)\).*? Tor Bug Tracker & Wiki$'),
            prefix='tor',
            postfix=' - https://bugs.torproject.org/%s',
            default_re=r'(?<!\w)(?:[tT]or#|https://trac.torproject.org/projects/tor/ticket/)([0-9]{4,})(?:(?=\W)|$)'
            ))
        p.append( h.TorProposalProvider( 'proposal.torproject.org',
            fixup=lambda i,x: "Prop#%s: %s"%(i,x) ))
        p.append( h.TicketHtmlTitleProvider( 'github.com-tor-ooni-probe-pull',
            'https://github.com/TheTorProject/ooni-probe/pull/',
            h.ReGroupFixup('.*?(.*) . Pull Request #[0-9]+ . TheTorProject/ooni-probe . GitHub$'),
            prefix='github-OONI-PR'
            ))
        p.append( h.TicketHtmlTitleProvider( 'bugs.debian.org',
            'http://bugs.debian.org/cgi-bin/bugreport.cgi?bug=',
            h.ReGroupFixup('#[0-9]+ - (.*) - Debian Bug report logs$'),
            prefix='Debian',
            postfix=' - https://bugs.debian.org/%s',
            default_re=r'(?i)(?<!\w)Deb(?:ian)?#([0-9]{3,})(?:(?=\W)|$)'
            ))
        p.append( h.TicketRTProvider( 'rt.debian.org',
            '~/.rtrc-debian',
            h.ReGroupFixup('[0-9]+: *(.*)$'),
            prefix='DebianRT',
            ))
        p.append( h.TicketHtmlTitleProvider( 'bts.grml.org',
            'http://bts.grml.org/grml/issue',
            h.ReGroupFixup('Issue [0-9]+: (.*) - GRML issue tracker$'),
            prefix='GRML'
            ))
        p.append( h.TicketHtmlTitleProvider( 'munin-monitoring.org',
            'http://munin-monitoring.org/ticket/',
            h.ReGroupFixup('.*?\((.*)\).*? Munin$'),
            prefix='munin'
            ))
        p.append( h.TicketHtmlTitleProvider( 'launchpad.net/ubuntu',
            'https://bugs.launchpad.net/ubuntu/+bug/',
            h.ReGroupFixup('Bug #[0-9]+ .(.*). : Bugs :'),
            prefix='ubuntu'
            ))
        p.append( h.TicketHtmlTitleProvider( 'bugzilla.redhat.com',
            'https://bugzilla.redhat.com/show_bug.cgi?id=',
            h.ReGroupFixup('Bug [0-9]+ . (.*)$'),
            prefix='redhat'
            ))
        p.append( h.TicketHtmlTitleProvider( 'labs.riseup.net',
            'https://labs.riseup.net/code/issues/',
            h.ReGroupFixup('[^#]+#[0-9]+: (.*) - RiseupLabs Code Repository$'),
            prefix='Tails',
            default_re=r'(?<!\w)(?:[tT]ails#|https://labs.riseup.net/code/issues/)([0-9]{4,})(?:(?=\W)|$)'
            ))

        self.providers = {}
        for i in p:
            self.providers[i.name] = i

    #addChannel(self, channel, regex=None, default=False):
    def _setup_channels(self):
        for tor in ('#ooni', '#nottor', '#tor*'):
            self.providers['trac.torproject.org'    ].addChannel(tor, default=True)
            self.providers['proposal.torproject.org'].addChannel(tor, regex='(?<!\w)[Pp]rop#([0-9]+)(?:(?=\W)|$)')

        self.providers['github.com-tor-ooni-probe-pull'].addChannel('#ooni', regex='(?<!\w)(?:PR#|https://github.com/TheTorProject/ooni-probe/pull/)([0-9]+)(?:(?=\W)|$)')

        self.providers['bugs.debian.org'     ].addChannel('#munin', regex='(?<!\w)[dD]#([0-9]{4,})(?:(?=\W)|$)')
        self.providers['launchpad.net/ubuntu'].addChannel('#munin', regex='(?<!\w)[uU]#([0-9]{4,})(?:(?=\W)|$)')
        self.providers['bugzilla.redhat.com' ].addChannel('#munin', regex='(?<!\w)[rR]#([0-9]{4,})(?:(?=\W)|$)')
        self.providers['munin-monitoring.org'].addChannel('#munin', default=True)

        self.providers['labs.riseup.net'].addChannel('#tails*', default=True)

        self.providers['bugs.debian.org'].addChannel('#tor-test', regex='(?<!\w)[dD]#([0-9]{4,})(?:(?=\W)|$)')
        self.providers['bugs.debian.org'].addChannel('#debian-*', default=True);
        self.providers['rt.debian.org'  ].addChannel('#debian-*', regex='(?<!\w)RT#([0-9]+)(?:(?=\W)|$)')

    def __init__(self):
        self._setup_providers()
        self._setup_channels()

# vim:set shiftwidth=4 softtabstop=4 expandtab:
