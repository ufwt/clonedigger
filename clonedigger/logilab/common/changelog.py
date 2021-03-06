# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
"""Manipulation of upstream change log files

The upstream change log files format handled is simpler than the one
often used such as those generated by the default Emacs changelog mode.

Sample ChangeLog format:
------------------------------------------------------------
Change log for project Yoo
==========================

 --
    * add a new functionnality

2002-02-01 -- 0.1.1
    * fix bug #435454
    * fix bug #434356
    
2002-01-01 -- 0.1
    * initial release
    
------------------------------------------------------------

There is 3 entries in this change log, one for each released version and one
for the next version (i.e. the current entry).
Each entry contains a set of messages corresponding to changes done in this
release.
All the non empty lines before the first entry are considered as the change
log title.

:author:    Logilab
:copyright: 2003-2008 LOGILAB S.A. (Paris, FRANCE)
:contact:   http://www.logilab.fr/ -- mailto:python-projects@logilab.org
"""
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import *
from builtins import object

import sys
from stat import S_IWRITE

from clonedigger.logilab.common.fileutils import ensure_fs_mode

BULLET = '*'
INDENT = '    '

class NoEntry(Exception):
    """raised when we are unable to find an entry"""

class EntryNotFound(Exception):
    """raised when we are unable to find a given entry"""

class Version(tuple):
    """simple class to handle soft version number has a tuple while
    correctly printing it as X.Y.Z
    """
    def __new__(klass, versionstr):
        if isinstance(versionstr, str):
            parsed = [int(i) for i in versionstr.split('.')]
        else:
            parsed = versionstr
        return tuple.__new__(klass, parsed)
        
    def __str__(self):
        return '.'.join([str(i) for i in self])

# upstream change log #########################################################

class ChangeLogEntry(object):
    """a change log entry, ie a set of messages associated to a version and
    its release date
    """
    version_class = Version
    
    def __init__(self, date=None, version=None, **kwargs):
        self.__dict__.update(kwargs)
        if version:
            self.version = self.version_class(version)
        else:
            self.version = None
        self.date = date
        self.messages = []
        
    def add_message(self, msg):
        """add a new message"""
        self.messages.append([msg])

    def complete_latest_message(self, msg_suite):
        """complete the latest added message
        """
        if not self.messages:
            print('Ignoring %r (unexpected format)' % msg_suite, file=sys.stderr)
        self.messages[-1].append(msg_suite)

    def write(self, stream=sys.stdout):
        """write the entry to file """
        stream.write('%s  --  %s\n' % (self.date or '', self.version or ''))
        for msg in self.messages:
            stream.write('%s%s %s\n' % (INDENT, BULLET, msg[0]))
            stream.write(''.join(msg[1:]))


class ChangeLog(object):
    """object representation of a whole ChangeLog file"""
    
    entry_class = ChangeLogEntry
    
    def __init__(self, changelog_file, title=''):
        self.file = changelog_file
        self.title = title
        self.additional_content = ''
        self.entries = []
        self.load()

    def __repr__(self):
        return '<ChangeLog %s at %s (%s entries)>' % (self.file, id(self),
                                                      len(self.entries))
    
    def add_entry(self, entry):
        """add a new entry to the change log"""
        self.entries.append(entry)

    def get_entry(self, version='', create=None):
        """ return a given changelog entry
        if version is omited, return the current entry 
        """
        if not self.entries:
            if version or not create:
                raise NoEntry()
            self.entries.append(self.entry_class())
        if not version:
            if self.entries[0].version and create is not None:
                self.entries.insert(0, self.entry_class())
            return self.entries[0]
        version = self.version_class(version)
        for entry in self.entries:
            if entry.version == version:
                return entry
        raise EntryNotFound()

    def add(self, msg, create=None):
        """add a new message to the latest opened entry"""
        entry = self.get_entry(create=create)
        entry.add_message(msg)
    
    def load(self):
        """ read a logilab's ChangeLog from file """
        try:
            stream = open(self.file)
        except IOError:
            return
        last = None
        for line in stream.readlines():
            sline = line.strip()
            words = sline.split()
            if len(words) == 1 and words[0] == '--':
                last = self.entry_class()
                self.add_entry(last)
            elif len(words) == 3 and words[1] == '--':
                last = self.entry_class(words[0], words[2])
                self.add_entry(last)
            elif last is None:
                if not sline:
                    continue
                self.title = '%s%s' % (self.title, line)
            elif sline and sline[0] == BULLET:
                last.add_message(sline[1:].strip())
            elif last.messages:
                last.complete_latest_message(line)
            else:
                self.additional_content += line
        stream.close()
        
    def format_title(self):
        return '%s\n\n' % self.title.strip()
    
    def save(self):
        """write back change log"""
        ensure_fs_mode(self.file, S_IWRITE)
        self.write(open(self.file, 'w'))
            
    def write(self, stream=sys.stdout):
        """write changelog to stream"""
        stream.write(self.format_title())
        for entry in self.entries:
            entry.write(stream)
