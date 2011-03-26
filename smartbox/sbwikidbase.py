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
# sbwikidbase (sbwikidbase.py)
# ----------------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import os
import time
from pkg_resources import resource_string
import system, interface, apt, sbdjango
from nbdebug import *

WB_PATH = "/var/wikidbase"
URL_PREFIX = "wikidbase"
HOST = "0.0.0.0"
PORT = "8888"

DEFAULT_ADMIN_CREDENTIALS = ["admin","wikidbase", "admin@email.com"]

"""You just installed Django's auth system, which means you don't have any superusers defined.
Would you like to create one now? (yes/no): yes
Username (Leave blank to use 'root'): admin
E-mail address: admin@admin.com
Password: 
Password (again): 
Superuser created successfully.
"""

def install() :
  debugOutput("Installing")
  system.run("sudo easy_install -f http://www.nickblundell.org.uk/packages --upgrade wikidbase")
  # Create a suitable settings file and a place for the db with www-data access
  uploadsPath = os.path.join(WB_PATH, "files")
  # XXX: pops up no module named wikidbase
  wbSettings = getSettingsData() 
  settingsFile = os.path.join(WB_PATH, "settings.py")
  databasePath = os.path.join(WB_PATH, "wbdata.db")
  cacheTable = "wbcache"
  
  # XXX: Adding these to end will cause settings.py logic to fail.
  # Set settings.
  wbSettings += """
DATABASE_ENGINE = "sqlite3"
DATABASE_NAME="%s"
CACHE_BACKEND="db://%s"
UPLOAD_FOLDER="%s"
  """ % (databasePath, cacheTable, uploadsPath)

  # Create folders and set permissions.
  system.run("mkdir -p '%s'" % uploadsPath)
  system.writeToFile(settingsFile, wbSettings)
  system.run("chgrp -R www-data '%s'" % WB_PATH)
  system.run("chmod -R g+rwx '%s'" % WB_PATH)
  
  # Initialise app
  sbdjango.initialiseApp("settings",DEFAULT_ADMIN_CREDENTIALS[0], DEFAULT_ADMIN_CREDENTIALS[1], DEFAULT_ADMIN_CREDENTIALS[2], pythonPath=WB_PATH, cacheTable=cacheTable)

  # Do mod_python setup
  apt.install("libapache2-mod-python")
  # Get mod_python

def start():
  # XXX: As root, this is not safe: eventually will use mod_python.
  sbdjango.startServer("settings", HOST, PORT, pythonPath=WB_PATH)

def stop():
  sbdjango.stopServer(HOST, PORT)

def getSettingsData() :
  # TODO: Must find a better way to do this.
  time.sleep(2)
  
  packages = os.listdir("/usr/lib/python2.4/site-packages/")
  wbPath = None
  for package in packages :
    if package.startswith("wikidbase") :
      wbPath = os.path.join("/usr/lib/python2.4/site-packages/", package)
      break
  
  if not wbPath :
    raise Exception("Cannot find wikidbase installation path")

  settingsFile = os.path.join(wbPath, "wikidbase", "settings.py")
  debugOutput("settingsFile: %s" % settingsFile)
  return open(settingsFile,"r").read()
  
  
  
  #
  # DOH!
  #
  
  #resource_string("wikidbase","settings.py") # This seems to fail imediately after doing easy_install wikidbase, must have to refesh import path or something.
  import imp
  result = imp.find_module("wikidbase")
  if result and result[1] :
    wbPath = result[1]
  else :
    raise Exception("Cannot find wikidbase installation path")
  
  settingsFile = os.path.join(wbPath, "settings.py")
  debugOutput("settingsFile: %s" % settingsFile)
  return open(settingsFile,"r").read()
  
  

if __name__ == "__main__" :

  debugOutput("Testing")
  install()
  sbdjango.startServer("settings", "0.0.0.0", 8383, WB_PATH, block=True)
