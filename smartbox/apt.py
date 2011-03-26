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
# apt (apt.py)
# ------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import re
import system
from nbdebug import *

APT_SOURCES = "/etc/apt/sources.list"


def prepareSystem():
  
  debugOutput("Configuring the Apt package manager")
  aptSources = system.readFromFile(APT_SOURCES).lower()
  originalSources = aptSources

  aptSources = re.compile("^\s*deb cdrom", re.MULTILINE).sub("#deb cdrom", aptSources)
  aptSources = re.compile("^#\s*deb http", re.MULTILINE).sub("deb http", aptSources)
  aptSources = re.compile("^#\s*deb-src http", re.MULTILINE).sub("deb-src http", aptSources)
  
  if aptSources != originalSources :
    debugOutput("Updating sources.")
    print "Preparing the system"
    system.writeToConfigFile(APT_SOURCES, aptSources)
    update()
  else :
    debugOutput("Package sources do not need updating.")


def install(packages) :
  debugOutput("Installing packages: '%s'" % packages)
  system.run("apt-get install -y %s" % packages)


def isInstalled(package) :
  output = os.popen4("dpkg -s %s" % package)[1].read()
  debugOutput(output.lower())
  return "package: %s" % package.lower() in output.lower()


def update() :
  system.run("apt-get -y update")


def upgrade() :
  system.run("apt-get -y upgrade")
