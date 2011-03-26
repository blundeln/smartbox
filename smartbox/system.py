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
# system (system.py)
# ------------------
#
# Description:
#   Abstraction of the system.
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import os, sys, popen2, shutil, re, time, pwd, grp
import urlparse
import smartbox
import interface, apt, sbpexpect
from nbdebug import *

COMMAND_DELAY = 1
BACKUP_EXT = ".smartbox-%s.bak" % smartbox.VERSION

BEEP_WARNING = [
  [600,100],
  [500,100],
  [400,100],
]

BEEP_WARNING = [
  [300,400],
  [400,400],
  [300,400],
  [400,400],
  [300,400],
  [400,400],
]

class User :
  def __str__(self) :
    return "%s (%s)" % (self.name, self.username)


def autoSudo():

  if os.getuid() != 0 :
    command = "sudo"
    for arg in sys.argv :
      command += " %s" % arg
    print("You are not root: automatically running command with sudo.")
    os.system("%s" % command)
    sys.exit()


def restartApp(app) :
  run("/etc/init.d/%s restart" % app)


def readFromFile(file) :
  debugOutput("Reading from file '%s'" % (file))
  if smartbox.options.testRun :
    if not os.path.exists(file) :
      return ""
  
  assert(os.path.exists(file))
  return open(file, "r").read()


def writeToConfigFile(file, string, mode="w") :
  backupFile = os.path.join(os.path.dirname(file), ".%s%s" % (os.path.basename(file), BACKUP_EXT))
  if not os.path.exists(backupFile) :
    run("cp %s %s" % (file, backupFile))
  writeToFile(file, string, mode)


def writeToFile(file, string, mode="w") :

  sample = string[0:min(35,len(string))]
  sample = ""
  debugOutput("Writing to file '%s': '%s'" % (file, sample))
  if smartbox.options.testRun :
    pass
  else :
    open(file,mode).write(string)


def run(command, exitOnFail = True) :
  result = 0
  debugOutput(command)
  
  logFile = open("/etc/sblog",mode="a"); logFile.write("Running: %s ...\n" % command); logFile.flush()
  
  if smartbox.options.testRun :
    if not smartbox.options.verbose and COMMAND_DELAY :
      time.sleep(COMMAND_DELAY)
  else :
    if smartbox.options.verbose :
      result = os.system(command)
    else :
      childProcess = popen2.Popen4(command)
      childProcess.fromchild.read()
      result = childProcess.wait()
 
  if exitOnFail and result != 0 :
    raise Exception("Command '%s' failed." % command)
  
  return result


def runExpect(command, events, exitOnFail = True, timeout=None) :
  return sbpexpect.runExpect(command, events, exitOnFail, timeout=timeout)

def runCommands(commands) :
  run(commands)


def sed(path, regexes) :

  pathOrig = path + ".original"
  run("cp %s %s" % (path, pathOrig))
  command = "cat %s" % pathOrig
  for regex in regexes :
    command += " | sed '%s'" % regex
  command += " > %s" % path
  run(command)


def addUser(username, password, name=None) :
  passwd = readFromFile("/etc/passwd")
  if passwd.find("%s:" % username) < 0 :
    
    expects = [
      ["Enter new UNIX password: ", password],
      ["Retype new UNIX password: ", password],
      [".*password updated successfully", None],
    ]
    sbpexpect.expect("adduser --force-badname --ingroup users --gecos='%s,,,' %s" % (name or "", username), expects)
  else :
    return False
  return True


def deleteUser(username) :
  run("""deluser --remove-home "%s" """ % username) 


def updateUser(username, name=None, password=None) :
  
  if name :
    run("""chfn -f "%s" %s""" % (name, username))

  if password :
    chp = os.popen("/usr/sbin/chpasswd", 'w')
    chp.write("%s:%s\n" % (username, password))
    chp.close()


def addGroup(group) :
  debugOutput("Adding group %s" % group)
  run("addgroup %s" % group)

def addUserToGroup(username, group) :
  run("""adduser "%s" "%s" """ % (username, group))

def removeUserFromGroup(username, group) :
  run("""deluser "%s" "%s" """ % (username, group))


def getUserDetails() :
  
  users = {}
  
  for pwdUser in pwd.getpwall() :
    user = User()
    user.username = pwdUser[0]
    user.gecos = pwdUser[4] or ""
    user.name = user.gecos.split(",")[0]
    users[user.username] = user

  return users


def isUserInGroup(username, group) :
  groups = getGroupMembership()
  if group not in groups :
    return False
  
  return username in groups[group]

def getGroupMembership() :

  groups = {}

  groupsData = grp.getgrall()
  for groupData in groupsData :
    groups[groupData[0]] = groupData[3]
    
  return groups

def getCommandOutput(command) :
  return os.popen(command,"r").read()

def dirSize(directory, exclude=None):

  command = "du %s --max-depth=0 --bytes" % directory
  if exclude :
    command += " --exclude='%s' " % exclude
  du = os.popen(command,"r").readlines()
  size = int(du[0].split()[0])
  return size


def cd(path=None) :
  global prevPath
  if path :
    prevPath = os.getcwd()
    os.chdir(path)
  elif prevPath :
    os.chdir(prevPath)


def reboot() :
  debugOutput("Rebooting")
  run('reboot')


def shutdown() :
  debugOutput("Shutting down")
  run("poweroff")


def downloadUncompressInstall(source, installCommand=None) :
  debugOutput("source '%s' installCommand '%s'." % (source, installCommand))
  
  package = os.path.basename(source)
  tempDir = "/tmp"
 
  debugOutput("package '%s'" % package)
  
  if package.endswith("tar.gz") :
    uncompressCommand = "tar -xzf"
  else :
    interface.abort("I don't know how to uncompress '%s'."%package)

  if not os.path.exists(os.path.join(tempDir, package)) :
    run("cd %s && wget %s" % (tempDir, source))
  interface.updateProgress()
  run("cd %s && %s %s" % (tempDir, uncompressCommand, os.path.basename(source)))
  interface.updateProgress()
  if installCommand :
    run("cd %s && %s" % (tempDir, installCommand))
  interface.updateProgress()


def expect(command, qas, timeout=None) :
  if timeout :
    return sbpexpect.expect(command, qas, timeout)
  else :  
    return sbpexpect.expect(command, qas)


def getDiskUsage() :
  output = os.popen4("df")[1].read()
  match = re.search("""^\S+\s+(?P<capacity>\d+)\s+(?P<used>\d+).*\s+/$""", output, re.MULTILINE)
  if match :
    debugOutput("Match %s" % match.groupdict())
    return {"used":int(match.groupdict()["used"])*1024, "capacity":int(match.groupdict()["capacity"])*1024}
  
  return None

def beep(sequence=None, delay=None) :
  beepSequence = ""
  if sequence :
    for item in sequence : 
      beepSequence += "-n -f %s -l %s %s" % (item[0],item[1], delay and "-D %s " % delay or "")
    beepSequence = beepSequence.lstrip("-n")
  beepCommand = "beep %s &" % (beepSequence)
  run(beepCommand)


def getDiskDevices() :

  #TODO: Get raid devices and size, get partition info.

  try :
    output = os.popen4("cat /proc/partitions")[1].read()
  except :
    return {}
  debugOutput(output)
  devices = {}
  for match in re.finditer("^\s*\d+\s+\d+\s+(?P<capacity>\d+)\s+(?P<device>[a-zA-Z]+?)\s*$", output, re.MULTILINE) :
    debugOutput(match.groupdict())
    if match.groupdict()["device"] not in devices :
      devices[match.groupdict()["device"]] = int(match.groupdict()["capacity"])
 
  debugOutput("Looking for raid devices")

  # Now add any raid devices
  raidTotalCapacity = 0
  for match in re.finditer("^\s*\d+\s+\d+\s+(?P<capacity>\d+)\s+(?P<device>(md)\d+?)\s*$", output, re.MULTILINE) :
    debugOutput(match.groupdict())
    raidTotalCapacity += int(match.groupdict()["capacity"])
  
  debugOutput("raidTotalCapacity: %s" % raidTotalCapacity)

  if raidTotalCapacity > 0 :
    devices["md"] = raidTotalCapacity

  return devices


def isPartitioned(device) :
  
  # Check the disk has not been partitioned.
  status = os.popen4("sfdisk -d /dev/%s" % device)[1].read()
  debugOutput("partioned status %s" % status)

  # XXX Some better logic is welcome here.
  if "no partitions found" in status.lower() :
    return False
  else :
   return True

def formatDevice(device) :
  # Now scrub the disk.
  device = device.lstrip("/dev/")
  smartbox.system.run("dd if=/dev/zero of=/dev/%s count=1 bs=512" % device)

def parseURL(urlString) :
  # Add support for ssh urls.
  tmpurl = urlparse.urlparse(urlString.replace("ssh","http"), "file")
  url = []
  for item in tmpurl :
    url.append(item)
  if "ssh://" in urlString : url[0] = "ssh"
  return url
