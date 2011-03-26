#
# Copyright (C) 2006 Nick Blundell.
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
# 
# The GNU GPL is contained in /usr/doc/copyright/GPL on a Debian
# system and in the file COPYING in the Linux kernel source.
# 
# __init__ (__init__.py)
# ----------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import os

VERSION_PARTS = ("1","0","2")

BASE_VERSION = "%s%s" % (".".join(VERSION_PARTS[0:-1]), VERSION_PARTS[-1] and ".%s" % VERSION_PARTS[-1])
VERSION = BASE_VERSION

COPYRIGHT = "Smartbox %s by Nick Blundell (www.nickblundell.org.uk) 2008" % VERSION

# Global variables
options = args = None

def getOption(option) :
  if options :
    return options.__dict__[option]
  else :
    return None

class Properties :
  def __init__(self) : self.__dict__["properties"] = {}
  def __setattr__(self, name, value) : self.__dict__["properties"][name] = value
  def __getattr__(self, name, default=None) : return name in self.properties and self.properties[name] or default
  def update(self, dictionary) : self.__dict__.update(dictionary)
  def __str__(self) : return str(self.__dict__)

options = Properties()

# Run all commands with sudo.
options.sudo = True
