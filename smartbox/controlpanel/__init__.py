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

from smartbox import system
from nbdebug import *

SB_PATH = "/var/smartbox"

def install() :

  # Enable apache site
  from smartbox import sbapache, sbdjango
  sbapache.setVHost("smartbox", genVHostString())

  # Create folder
  system.run("mkdir -p '%s'" % SB_PATH)

  # Now do syncdb
  sbdjango.initialiseApp("smartbox.controlpanel.settings", "admin", "admin", "admin@admin.com")

def genVHostString() :
  template = """
NameVirtualHost *
<VirtualHost *>
  <Proxy *>
  Order deny,allow
  Allow from all
  </Proxy>

  <Location />
  AuthType Basic
  AuthName "Restricted Access"
  AuthUserFile /etc/smartbox.passwd
  Require user Administrator
  </Location>

  #<Location /wikidbase>
  #  SetHandler python-program
  #  PythonHandler django.core.handlers.modpython
  #  PythonPath "['/var/wikidbase'] + sys.path"
  #  SetEnv DJANGO_SETTINGS_MODULE settings
  #  PythonDebug On
  #  PythonAutoReload On
  #</Location>

ProxyRequests Off
ProxyPass / http://localhost:8000/
ProxyPassReverse / http://localhost:8000/
</VirtualHost>
"""

  vHostString = template

  return vHostString

if __name__ == "__main__" :
  debugOutput("Testing install")
  install()
