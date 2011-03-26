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
# smartbox (smartbox.py)
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
import system
import samba, sbmysql, sbapache, sbphp, rsnapshot, sbdjango, sbpexpect, utilapps, raid, sbwikidbase
import smartbox.remotebackup
import controlpanel
import interface
import smartbox
import smartbox.ssh
import smartbox.network
from nbdebug import *

DEFAULT_DOMAIN = "MYDOMAIN"
DEFAULT_ADMIN_PASS = "smartbox"

CRON_TARGET = "/etc/cron.d/smartbox"

# For the progress bar.
NO_INSTALLATION_STEPS = 36
SMARTBOX_SSH_PORT = 8520
#SMARTBOX_SSH_PORT = 22

PASSWORD_FILE = "/etc/smartbox.passwd"

def install(upgrade=False) :
  
  debugOutput("Installing smartbox")

  interface.startProgress("%s and configuring Smartbox" % (upgrade and "Upgrading" or "Installing"), noSteps=NO_INSTALLATION_STEPS)

  interface.updateProgress("Installing boot records on raid devices"); raid.updateGrub()
  
  interface.updateProgress("Installing pexpect"); sbpexpect.install()
  interface.updateProgress("Installing utilities"); utilapps.install()
  
  # Add the smartbox ssh port
  smartbox.ssh.addSSHPort(SMARTBOX_SSH_PORT)
  
  if not upgrade :
    interface.updateProgress("Installing samba"); samba.install(domain=DEFAULT_DOMAIN)
  
  interface.updateProgress("Installing internal backup system"); rsnapshot.install(backupSources=[samba.SAMBA_USERS_PATH, samba.SAMBA_SHARES_PATH])
  interface.updateProgress("Installing external backup system"); smartbox.remotebackup.install()
  
  #sbmysql.install()
  sbapache.install()
  #sbphp.install()
  
  sbdjango.install()

  #interface.updateProgress("Installing groupware: wikidbase"); sbwikidbase.install()

  interface.updateProgress("Installing control panel"); controlpanel.install()

  # Set the default admin password.
  if not upgrade :
    setAdminPassword(DEFAULT_ADMIN_PASS)


  # Install the cron file.
  installCronScript()

  interface.updateProgress("Completed", 100)
  interface.stopProgress()
  

def getSambaRootPass() :
 
  password = interface.prompt("Set a password for the smartbox network Administrator", password=True)
  cPassword = interface.prompt("Retype password for the network Administrator", password=True)
  if password != cPassword :
    interface.abort("The passwords do not match.")
  return password


def getUsers() :
  
  sambaUsers = samba.getUsers()
  systemUsers = system.getUserDetails()

  users = {}

  for username in sambaUsers :
    
    if username in ["root"] :
      continue
    
    users[username] = systemUsers[username]

  return users


def addUser(username, password, name, systemOnly=False) :
  
  system.addUser(username, password, name)
  if not systemOnly :
    samba.addUser(username, password)


def setAdminPassword(password) :
  # Set samba admin password
  samba.setPassword("root", password)
  # Set web interface admin password
  system.run("htpasswd -bc %s '%s' '%s'" % (PASSWORD_FILE, "Administrator", password))
  system.run("chgrp www-data '%s'" % PASSWORD_FILE)
  system.run("chmod 740 '%s'" % PASSWORD_FILE)
  

def setUserDetails(username, name=None, password=None, aliases=None) :
  debugOutput("Setting details for %s name %s password %s" % (username, name, password))

  system.updateUser(username, name=name, password=password)
  if password and username in samba.getUsers() :
    samba.setPassword(username, password)


def deleteUser(username) :

  # For sanity's sake!
  if username.lower() in ["root","administrator"] :
    return

  if username in samba.getUsers() :
    samba.deleteUser(username)
  system.deleteUser(username)


def installCronScript() :
  debugOutput("Debug install cron script.")
  from pkg_resources import resource_filename
  cronConfig = system.readFromFile(resource_filename(smartbox.__name__, os.path.join("resources","smartbox-cron")))
  system.writeToFile(CRON_TARGET, cronConfig)


def restart() :
  """Restarts networking and samba"""
  smartbox.network.restart()
  smartbox.samba.restart()
