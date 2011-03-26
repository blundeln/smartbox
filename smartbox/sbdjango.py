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
# sbdjango (sbdjango.py)
# ----------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import system, interface, apt
from nbdebug import *

def install() :
  debugOutput("Installing")

  interface.updateProgress("Installing django")
  
  system.downloadUncompressInstall("http://media.djangoproject.com/releases/0.96/Django-0.96.tar.gz","cd Django-0.96 && python setup.py install")
  interface.updateProgress("")
  apt.install("libapache2-mod-python")
  interface.updateProgress("")
  apt.install("python-mysqldb")

def configure() :
  pass

def initialiseApp(settingsModule, user, password, email, pythonPath=None, cacheTable=None) :
  
  syncdbEvents = {
    "yes/no":"yes\n",
    "Username":"%s\n" % user,
    "E-mail address":"%s\n" % email,
    "Password":"%s\n" % password,
  }
  system.runExpect("django-admin.py %s --settings='%s' syncdb" % (pythonPath and "--pythonpath='%s'" % (pythonPath) or "", settingsModule), events=syncdbEvents, timeout=60)
  
  # Create cache table
  if cacheTable :
    # XXX: really we should not run this if the db file has content.
    try :
      system.run("django-admin.py %s --settings='%s' createcachetable %s" % (pythonPath and "--pythonpath='%s'" % (pythonPath) or "", settingsModule, cacheTable))
    except :
      pass


def startServer(settingsModule, host, port, pythonPath=None, block=False) :
 
  command = "django-admin.py %s --settings='%s' runserver %s:%s" % (pythonPath and "--pythonpath='%s'" % (pythonPath) or "", settingsModule, host, port)
  if not block :
    command += " 1>/dev/null 2>/dev/null &"
  system.run(command)


def stopServer(host, port) :
  
  system.run("""pkill -f 'runserver %s:%s'""" % (host, port), exitOnFail=False)
