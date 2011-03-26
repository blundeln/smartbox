#
# Copyright (C) 2007 Nick Blundell.
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
# utilapps (utilapps.py)
# ----------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import interface, apt
from nbdebug import *

APPS = [
  "ssh",
  "screen",
  "htop",
  "sysv-rc-conf",
  "beep",
  "timeout",
  "fakeroot",
  "python-pysqlite2",
  "python-crypto",
  "openssl",
]

def install() :
  if isInstalled() :
    return
  
  debugOutput("Installing utils")
  
  for app in APPS :
    interface.updateProgress(); apt.install(app)

def isInstalled() :
  for app in APPS :
    if not apt.isInstalled(app) :
      return False
  return True
