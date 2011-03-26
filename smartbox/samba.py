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
# samba (samba.py)
# ----------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import os
import popen2
import re
import grp
import datetime
import interface, system, smartbox, apt
import smartbox.settings
from nbdebug import *

SAMBA_HOME = "/home/samba"
SAMBA_USERS_PATH = "/users"
SAMBA_SHARES_PATH = "/shares"

SAMBA_CONFIG = "/etc/samba/smb.conf"
SHARE_GROUP_PREFIX = "sbgroup"

NETBIOS_CHECK_TIMEOUT = 3 * 60

EXCLUDE_SHARES = [
  "profile",
  "homes",
  "global",
  "printers",
  "netlogon",
  "backups",
]


def install(domain) :
  
  if isInstalled() :
    return
  
  debugOutput("Installing samba")
  
  apt.install("samba samba-common libcupsys2 libkrb53 winbind smbclient")
 
  interface.updateProgress();
 
  sambaConfig = _createConfig(domain)
  debugOutput(sambaConfig)
  # XXX: Warning, what if samba file exists.
  system.writeToConfigFile(SAMBA_CONFIG, sambaConfig)
  
  system.run("""mkdir -p "%s" """ % SAMBA_HOME)
  system.run("""mkdir -p "%s/netlogon" """ % SAMBA_HOME)
  system.run("""mkdir -p "%s/profiles" """ % SAMBA_HOME)
  system.run("""mkdir -p "%s/data" """ % SAMBA_HOME)
  system.run("""mkdir -p "%s" """ % SAMBA_USERS_PATH)
  system.run("""mkdir -p "%s" """ % SAMBA_SHARES_PATH)
  system.run("""mkdir -p /var/spool/samba""", exitOnFail=False)
  system.run("""chmod 777 /var/spool/samba/""")
  system.run("""chmod 770 "%s/profiles" """ % SAMBA_HOME)
  system.run("""chmod 770 "%s/netlogon" """ % SAMBA_HOME)
  system.run("""chmod 775 "%s" """ % SAMBA_USERS_PATH)
  system.run("""chown -R root:users "%s/" || chmod -R 771 "%s/" """ % (SAMBA_HOME, SAMBA_HOME))

  interface.updateProgress();
  
  restart()

  interface.updateProgress();
  
  nsswitchString = system.readFromFile("/etc/nsswitch.conf")
  onsswitchString = nsswitchString
  nsswitchString = nsswitchString.replace("files dns","files wins dns")
  if nsswitchString != onsswitchString :
    system.writeToConfigFile("/etc/nsswitch.conf", nsswitchString)

  system.run("net groupmap add ntgroup='Domain Admins' unixgroup=root")
  system.run("net groupmap add ntgroup='Domain Users' unixgroup=users")
  system.run("net groupmap add ntgroup='Domain Guests' unixgroup=nogroup")

  # TODO: Check this has not been done.
  system.run("echo 'root = Administrator' > /etc/samba/smbusers")
  
  interface.updateProgress();
  
  # Add a default share that all users can access.
  if not "Files" in getShares() :
    addShare("Files")


def isInstalled() :
  return os.path.exists(SAMBA_CONFIG)


def addSambaUser(username, password) :
  
  expects = [  
    ["New SMB password:", password],
    ["Retype new SMB password:", password],
    [".*", None],
  ]
  system.expect("""smbpasswd -a %s""" % username, expects)

  restart()

def setPassword(username, password) :
  addSambaUser(username, password)

def addUser(username, password) :
  
  addSambaUser(username, password)

  # Add a directory for the user.
  userDir = os.path.join(SAMBA_USERS_PATH, username)
  system.run("""mkdir -p "%s" """ % userDir)
  system.run("""chown %s "%s" """ % (username, userDir))
  system.run("""chgrp %s "%s" """ % ("users", userDir))
  system.run("""chmod 700 "%s" """ % userDir)

def deleteUser(username) :
  
  if username not in getUsers() :
    return

  userDir = os.path.join(SAMBA_USERS_PATH, username)
  profileDir = os.path.join(SAMBA_HOME, "profiles", username)
  system.run("""smbpasswd -x "%s" """ % username)
  system.run("""rm -rf "%s" """ % userDir)
  system.run("""rm -rf "%s" """ % profileDir)


def addShare(share, group=None, description=None, public=False) :
  debugOutput("Adding Samba share '%s'" % (share))
 
  if not group : group = groupNameFromShare(share)

  sharePath = os.path.join(SAMBA_SHARES_PATH, share)
 
  if share in getShares():
    if not smartbox.options.testRun :
      interface.abort("The share '%s' exists or has been defined already" % sharePath)
 
  if group not in system.readFromFile("/etc/group") :
    system.addGroup(group)
 
  if not os.path.exists(sharePath) :
    system.run("""mkdir -p "%s" """ % sharePath, exitOnFail = False)
  system.run("""chgrp %s "%s" """ % (group, sharePath))
  system.run("""chmod 6770 "%s" """ % sharePath)

  shareConfig = _createShareConfig(share, sharePath, group, description)
  
  sambaConfig = system.readFromFile(SAMBA_CONFIG)
  sambaConfig += "\n\n%s" % shareConfig
  
  sambaConfig = setShareDetails(share, description, public=public, sambaConfig=sambaConfig)
   
  system.writeToConfigFile("/etc/samba/smb.conf",sambaConfig)
 
  restart()

def deleteShare(shareName) :
  debugOutput("Deleting share %s" % shareName)

  if shareName not in getShares() :
    return

  group = groupNameFromShare(shareName)
  sharePath = os.path.join(SAMBA_SHARES_PATH, shareName)
  system.run("""rm -rf "%s" """ % sharePath, exitOnFail=False)
  system.run("""delgroup "%s" """ % group, exitOnFail=False)
  
  # Remove smb.conf entry
  sambaConfig = system.readFromFile(SAMBA_CONFIG)
  match = re.search(r"\[%s\][^[]+" % shareName, sambaConfig, re.DOTALL)
  if match :
    sambaConfig = sambaConfig.replace(match.group(0),"").strip()
    system.writeToFile(SAMBA_CONFIG, sambaConfig)
    restart()
  

def setShareDetails(shareName, description, public=False, sambaConfig=None) :
  debugOutput("Setting share details for %s" % shareName)

  if not sambaConfig and shareName not in getShares() :
    return
 
  # Get the group name of this share.
  shareGroup = groupNameFromShare(shareName)
  
  if not sambaConfig :
    sambaConfig = system.readFromFile(SAMBA_CONFIG)
    saveConfig = True
  else :
    saveConfig = False

  # Update the comment field
  newSambaConfig = surgicalConfigSet(sambaConfig, shareName, "comment", description)
  
  # Update guest access to the share
  # TODO: guest only, valid users
  if public :
    newSambaConfig = surgicalConfigSet(newSambaConfig, shareName, "valid users", "")
    newSambaConfig = surgicalConfigSet(newSambaConfig, shareName, "guest ok", "yes")
    newSambaConfig = surgicalConfigSet(newSambaConfig, shareName, "guest only", "yes")
    if not system.isUserInGroup("nobody", shareGroup) :
      system.addUserToGroup("nobody", shareGroup)
  else :
    newSambaConfig = surgicalConfigSet(newSambaConfig, shareName, "valid users", "@%s root" % shareGroup)
    newSambaConfig = surgicalConfigSet(newSambaConfig, shareName, "guest ok", "no")
    newSambaConfig = surgicalConfigSet(newSambaConfig, shareName, "guest only", "no")
    if system.isUserInGroup("nobody", shareGroup) :
      system.removeUserFromGroup("nobody", shareGroup)
  
  if saveConfig :
    if newSambaConfig != sambaConfig :
      system.writeToFile(SAMBA_CONFIG, newSambaConfig)
      restart()
  else :
    return newSambaConfig


def getConfig() :
  import ConfigParser
  config = ConfigParser.ConfigParser()
  config.read(SAMBA_CONFIG)
  return config


def getShares():
  debugOutput("Getting shares")
  shares = {}
  config = getConfig()
  for section in config.sections() :
    if section.lower() in EXCLUDE_SHARES :
      continue
    shares[section] = dict(config.items(section))
    shares[section]["name"] = section
    # XXX: Need to do this until we get expr tag to work
    shares[section]["public"] = "guest ok" in shares[section] and shares[section]["guest ok"].lower() == "yes" and True or False
  return shares

def changePassword(username, password) : pass

def restart() :
  system.run("/etc/init.d/samba restart")


def getUsers() :

  debugOutput("Getting samba users.")

  childProcess = popen2.Popen4("pdbedit -w -L")
  userOutput = childProcess.fromchild.read()
  result = childProcess.wait()

  if result != 0 : return []
 
  debugOutput(userOutput)

  users = []

  for match in re.finditer(r"""^(?P<username>[^:]+):.*\[U.*$""", userOutput, re.MULTILINE) :
    debugOutput(match.groupdict())
    user = match.groupdict()["username"]
    users.append(user)
    
  return users


def _createConfig(domainName) :
  
  from pkg_resources import resource_filename
  templateFile = resource_filename(smartbox.__name__, os.path.join("resources","smb.conf.template"))

  sambaConfig = open(templateFile,"r").read()
  sambaConfig = sambaConfig.replace("WORKGROUP",domainName)
  sambaConfig = sambaConfig.replace("NETLOGON_PATH",os.path.join(SAMBA_HOME, "netlogon"))
  sambaConfig = sambaConfig.replace("HOMES_PATH",os.path.join(SAMBA_USERS_PATH, "%S"))
  sambaConfig = sambaConfig.replace("PROFILES_PATH",os.path.join(SAMBA_HOME, "profiles"))
  sambaConfig = sambaConfig.replace("SMARTBOX_SCRIPT","smartbox")
   
  return sambaConfig

def groupNameFromShare(shareName) :
  return "%s%s" % (SHARE_GROUP_PREFIX, shareName.lower().replace(" ",""))

def _createShareConfig(share, sharePath, group, description=None) :

  from pkg_resources import resource_filename
  templateFile = resource_filename(smartbox.__name__, os.path.join("resources","sambashare.conf.template"))

  shareConfig = open(templateFile,"r").read()
  shareConfig = shareConfig.replace("SHARE",share)
  shareConfig = shareConfig.replace("COMMENT",description or "")
  shareConfig = shareConfig.replace("PATH",sharePath)

  return shareConfig


def getSharePermission(username, shareName) :
  if shareName not in getShares() :
    return False

  sharePath = os.path.join(SAMBA_SHARES_PATH, shareName)
  shareGroup = grp.getgrgid(os.stat(sharePath).st_gid)
  debugOutput("shareGroup %s" % shareGroup)
  return username in shareGroup.gr_mem


def setSharePermission(username, shareName, permission) :
  debugOutput("")
  if shareName not in getShares() :
    return

  curPermission = getSharePermission(username, shareName)
  if curPermission == permission :
    return
  
  sharePath = os.path.join(SAMBA_SHARES_PATH, shareName)
  shareGroup = grp.getgrgid(os.stat(sharePath).st_gid)
  
  # Add the user to the share's group.
  if permission == True :
    system.addUserToGroup(username, shareGroup.gr_name)
  else :
    system.removeUserFromGroup(username, shareGroup.gr_name)

  # Make sure samba uses up-to-date group info by restarting it
  restart()
    
def getDomain() :
 
  config = getConfig()
  try :
    return dict(config.items("global"))["workgroup"]
  except :
    return "ERROR"

def setDomain(domain) :
  if domain == getDomain() :
    return
  sambaConfig = system.readFromFile(SAMBA_CONFIG)
  sambaConfig = surgicalConfigSet(sambaConfig, "global","workgroup",domain)
  debugOutput(sambaConfig)
  system.writeToFile(SAMBA_CONFIG, sambaConfig)
  restart()


def generateLogonScript() :
 
  import socket

  try :
    username = smartbox.options.args[-1]
  except :
    interface.abort("You must enter a username to generate a login script.")
  
  debugOutput("Generating logon.bat for '%s'." % username)

  hostName = socket.gethostname()

  loginScript = "echo off\nnet use /persistent:no\n"

  shareFolder = SAMBA_SHARES_PATH
  for share in os.listdir(shareFolder) :
    sharePath = os.path.join(shareFolder, share)
    debugOutput("Checking permissions on '%s' " % sharePath)
    try :
      shareGroup = grp.getgrgid(os.stat(sharePath).st_gid)
      debugOutput("shareGroup: %s members %s" % (shareGroup, shareGroup.gr_mem))
      if username in shareGroup.gr_mem or shareGroup.gr_name == "users":
        loginScript += """net use * "\\\\%s\\%s"\n""" % (hostName, share)
    except :
      pass

  # Add the backup share
  loginScript += """net use * "\\\\%s\\%s"\n""" % (hostName, "backups")

  debugOutput(loginScript)
  
  # Use DOS file endings.
  loginScript = loginScript.replace("\n","\r\n")
  scriptFile = os.path.join(SAMBA_HOME, "netlogon", "%s.bat" % username)
  system.writeToFile(scriptFile, loginScript)
  
  system.run("""chown "%s" "%s" """ % (username, scriptFile))
  system.run("""chgrp "%s" "%s" """ % ("users", scriptFile))
  system.run("""chmod 700 "%s" """ % scriptFile)


def checkNmbd() :
  """Re-starts samba if nmbd has stopped.  I find this sometimes happens when a network connection is dropped to the server."""
  
  debugOutput("Checking nmbd")
  
  lastCheckTime = smartbox.settings.get("last netbios restart", None)
 
  debugOutput("lastCheckTime %s" % lastCheckTime)

  if lastCheckTime and (datetime.datetime.now() - lastCheckTime).seconds < NETBIOS_CHECK_TIMEOUT :
    debugOutput("We have restarted samba recently, so leave this.")
    return

  # Look at the listening processes
  listeningApps = smartbox.system.getCommandOutput("netstat -lp")
  debugOutput(listeningApps)
  if "smbd" not in listeningApps :
    debugOutput("Samba is not running anyway")
    return

  if "netbios-ns" in listeningApps :
    debugOutput("netbios is running okay")
    return

  # Samba is there but netbios is not, so restart samba
  debugOutput("Samba is running but netbios is not, restarting samba.")
  restart()
  smartbox.settings.set("last netbios restart", datetime.datetime.now())  


#
# Useful methods.
#

def surgicalConfigSet(configString, section, attribute, value) :
  
  # Look for the section in the config string.
  match = re.search(r"\[%s\][^[]+" % section, configString, re.DOTALL)
  if match :

    matchString = match.group(0)
    newConfigLine = "%s = %s" % (attribute, value)
    newSectionString = matchString

    # Try to replace the line and fallback by adding the new attribute.
    if attribute not in newSectionString :
      newSectionString += "%s\n" % newConfigLine
    else :  
      newSectionString = re.sub("%s\s*=.*" % attribute, newConfigLine, matchString)
    
    # If this caused a change, substitute the new section config.
    if newSectionString != matchString :
      configString = configString.replace(matchString, newSectionString)
  
  return configString
