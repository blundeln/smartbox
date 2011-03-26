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
# sbphp (sbphp.py)
# ----------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import system, sbapache, interface, apt
from nbdebug import *

def install() :
  debugOutput("Installing")
  if apt.isInstalled("php4") :
    debugOutput("php4 is installed")

  interface.updateProgress("Install php4")

  apt.install("php4 libapache2-mod-php4 php4-mysql")

  configure()

def configure() :
  # Enable mysql extensions.
  phpConfigFile = "/etc/php4/apache2/php.ini"
  phpConfig = system.readFromFile(phpConfigFile)

  phpConfig = phpConfig.replace(";extension=mysql.so","extension=mysql.so")

  system.writeToConfigFile(phpConfigFile, phpConfig)

  # TODO: Boost php memory.

  sbapache.restart()
