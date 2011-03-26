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
# remotebackup (remotebackup.py)
# ------------------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import os, time, datetime

import smartbox.system
import smartbox.apt
import smartbox.settings
import smartbox.ssh
import smartbox.core

from nbdebug import *


CRON_FILE = "/etc/cron.d/smartbox-backup"
INFINITE_DAYS = 10000

SOURCE_FOLDERS = ["/home","/users","/shares","/root","/etc"]

PEER_HOST = "PEER_HOST"
PEER_USERNAME = "PEER_USERNAME"
PEER_PASSWORD = "PEER_PASSWORD"
PEER_ENCRYPTION_KEY = "PEER_ENCRYPTION_KEY"
PEER_NOTES = "PEER_NOTES"

BACKUP_GROUP = "remote-backup"
REMOTE_BACKUPS_FOLDER = ".smartbox-backups"


BACKUP_BYTES = "BACKUP_BYTES"
BACKED_UP_BYTES = "BACKED_UP_BYTES"
LAST_BACKUP_TIME = "LAST_BACKUP_TIME"
BACKUP_DURATION = "BACKUP_DURATION"
LAST_BACKUP_STATUS = "LAST_BACKUP_STATUS"
DAYS_SINCE_LAST_BACKUP = "DAYS_SINCE_LAST_BACKUP"

MAX_RSYNC_FILE = None # "400mb" # Currently require this for encrypted backup.

# Capabilities
CAP_SSH_PORT = "CAP_SSH_PORT"
CAP_BACKUP_FOLDER = "CAP_BACKUP_FOLDER"
CAP_RSYNC = "CAP_RSYNC"
CAP_RSYNC_SMARTBOX = "CAP_RSYNC_SMARTBOX"
CAP_FAKEROOT = "CAP_FAKEROOT"
CAP_OPENSSL = "CAP_OPENSSL"


def install() :
  """Installs the remote backup system"""

  # Make the remote backups folder and set it's permissions for the backup user group.
  if BACKUP_GROUP not in smartbox.system.getGroupMembership() :
    smartbox.system.addGroup(BACKUP_GROUP)
  smartbox.system.run("mkdir -p /%s" % REMOTE_BACKUPS_FOLDER)
  smartbox.system.run("chmod 770 /%s" % REMOTE_BACKUPS_FOLDER)
  smartbox.system.run("chgrp %s /%s" % (BACKUP_GROUP, REMOTE_BACKUPS_FOLDER))

  # Installed modified rsync - this allows efficient encrypted dest files.
  smartbox.system.run("wget http://www.nickblundell.org.uk/packages/rsync-smartbox")
  smartbox.system.run("mv rsync-smartbox /usr/bin")
  smartbox.system.run("chmod +x /usr/bin/rsync-smartbox")



def getStatus() :
  """Returns the status of remote backup."""

  # Check that remote backup has been configured.
  if not smartbox.settings.get(PEER_HOST, None) :
    return {}

  status = {}
  status[LAST_BACKUP_TIME] = smartbox.settings.get(LAST_BACKUP_TIME, None)
  status[BACKUP_BYTES] = smartbox.settings.get(BACKUP_BYTES,0)
  status[BACKED_UP_BYTES] = smartbox.settings.get(BACKED_UP_BYTES,0)
  status[LAST_BACKUP_STATUS] = smartbox.settings.get(LAST_BACKUP_STATUS,False)
  
  # Compute the number of days since the last successful backup.
  if status[LAST_BACKUP_TIME] :
    status[DAYS_SINCE_LAST_BACKUP] = (datetime.datetime.now() - status[LAST_BACKUP_TIME]).days
  else :
    status[DAYS_SINCE_LAST_BACKUP] = INFINITE_DAYS

  debugOutput(status)
  
  return status


def backup(folders=None, timeout=None) :
  if not folders : folders = SOURCE_FOLDERS
  """Initiates the remote backup of the speicifed folders."""
  if smartbox.settings.get(PEER_HOST, None) :
    backupEngine.backup(folders, timeout=timeout or smartbox.settings.get(BACKUP_DURATION, 10) * 60 * 60)


def restore(restoreDir, hostname, username, password=None, encryptionKey=None, path=None, folders=None) :
  debugOutput("restoreDir %s" % restoreDir)
  if not folders : folders = SOURCE_FOLDERS
  """Initiates the restoration of the specified remotely backed up folders."""
  backupEngine.restore(folders=folders, restoreDir=restoreDir, hostname=hostname, username=username, password=password, encryptionKey=encryptionKey, path=path)


def getPeerAccounts() :
  """Returns details of local backup peer accounts (i.e. accounts on this smartbox for other smartboxes to use for backup)."""
  groups = smartbox.system.getGroupMembership()
  userDetails = smartbox.system.getUserDetails()

  users = {}

  if BACKUP_GROUP not in groups :
    return users

  for username in groups[BACKUP_GROUP] :
    users[username] = userDetails[username]

  return users
    

def deletePeerAccount(username) :
  """Deletes the specified backup peer acount and its data from this smartbox."""
  if username not in getPeerAccounts() :
    raise Exception("Username is not a backup peer account")

  # Remove any backup files.
  usersBackupFolder = os.path.join("/%s" % REMOTE_BACKUPS_FOLDER, username)
  smartbox.system.run("""rm -fr "%s" """ % usersBackupFolder)

  # Delete the user account.
  smartbox.core.deleteUser(username)


def clearBackupData() :
  """Clears any data that has previously been backed up to the remote destination."""

  # Load the peer settings
  settings = smartbox.settings.load()
  host = settings["PEER_HOST"]
  username = settings["PEER_USERNAME"]
  password = settings["PEER_PASSWORD"]
 
  if not host and not username :
    raise Exception("No backup peer account is configured." % (host))

  # Get backup capabilities of the host.
  hostCapabilities = getHostCapabilities(host, username, password)
  
  # Check for basic connectivity and access to the backup host.
  if not hostCapabilities :
    raise Exception("Unable to connect to host %s for backup: the username and password may be incorrect or no ssh connection can be made." % (host))
    
  # Build the destination path.
  destBackupFolder = os.path.join(hostCapabilities[CAP_BACKUP_FOLDER], username)

  # Delete it.
  debugOutput("Deleting backup folder %s@%s/%s" % (username, host, destBackupFolder))
  smartbox.ssh.runSSHCommand(username, host, "rm -fr %s" % destBackupFolder, password=password, port=hostCapabilities[CAP_SSH_PORT])
  
  # Reset backup status
  smartbox.settings.set(BACKED_UP_BYTES, 0)



#
# Cron methods.
#

def getBackupStartTime() :
  """Returns the start time for the next backup job, from the cron file.""" 
  
  # If the cron file has not been created, create it with the default time.
  if not os.path.exists(CRON_FILE) :
    setBackupStartTime(datetime.time(20,00))

  # Parse the cron time format.
  timeItems = smartbox.system.readFromFile(CRON_FILE).split("\n")[1].split()
  return datetime.time(int(timeItems[1]), int(timeItems[0]))


def setBackupStartTime(startTime) :
  """Sets the backup job start time for cron.""" 
  
  cronConfig = """PATH=:/bin:/usr/bin:/sbin:/usr/local/bin
%s %s * * * root /usr/bin/smartbox backup
""" % (startTime.minute, startTime.hour)
  smartbox.system.writeToFile(CRON_FILE, cronConfig)



#
# Alternate Backup Systems (currently just use rsync)
#

class BackupBackend :
  """Interface for backup systems"""
  def backup(self, folders, timeout=None) : raise Exception("Not implemented")
  def restore(self, folders) : raise Exception("Not implemented")
  def getBackedUpBytes(self) : raise Exception("Not implemented")


class Rsync(BackupBackend) :
  """Uses rsync to perform remote backup."""

  def backup(self, folders, restoreSource=None, timeout=None, restoreDir="/") :
    """Backs up the specified folders."""

    debugOutput("Starting backup of %s: timout %s" % (folders, timeout))

    # Assume the backup will fail unless it succeeeds and assume zero bytes are backed up on server.
    smartbox.settings.set(LAST_BACKUP_STATUS, False)
    smartbox.settings.set(BACKED_UP_BYTES, 0)
    
    # Load the backup peer settings
    settings = smartbox.settings.load()
    host = settings["PEER_HOST"]
    username = settings["PEER_USERNAME"]
    password = settings["PEER_PASSWORD"]
    encryptionKey = settings["PEER_ENCRYPTION_KEY"]
    
    # Get backup capabilities of the host.
    hostCapabilities = getHostCapabilities(host, username, password)
    
    # Check for basic connectivity and access to the backup host.
    if not hostCapabilities :
      raise Exception("Unable to connect to host %s for backup: the username and password may be incorrect or no ssh connection can be made." % (host))

    # Check rsync is available on the other end.
    if not hostCapabilities[CAP_RSYNC] :
      raise Exception("Cannot perform backup, since %s does not have rsync." % (host))

    # Build the destination path.
    userBackupFolder = os.path.join(hostCapabilities[CAP_BACKUP_FOLDER], username)
    destBackupFolder = os.path.join(userBackupFolder, "rsync")

    # Make and Set permissions on the backup folder
    smartbox.ssh.runSSHCommand(username, host, "mkdir -p '%s'" % userBackupFolder, port=hostCapabilities[CAP_SSH_PORT], password=password)
    smartbox.ssh.runSSHCommand(username, host, "chmod 700 '%s'" % userBackupFolder, port=hostCapabilities[CAP_SSH_PORT], password=password)

    # Compute the number of bytes to be backed up - for session style progress monitoring
    backupBytes = 0
    for folder in folders :
      backupBytes += smartbox.system.dirSize(folder, exclude=REMOTE_BACKUPS_FOLDER)

    # Store how many bytes we need to backup for a complete backup.
    smartbox.settings.set(BACKUP_BYTES, backupBytes)

    #
    # Backup each folder
    #
    for folder in folders :

      debugOutput("Processing folder %s" % folder)
      if timeout != None and timeout <= 0 :
        continue
      
      # Start timing.
      startTime = datetime.datetime.now()

      # Build the backup folder for this folder.
      backupFolder = destBackupFolder
      
      # Create the destination folder, if necessary.
      smartbox.ssh.runSSHCommand(username, host, "mkdir -p %s" % backupFolder, port=hostCapabilities[CAP_SSH_PORT], password=password)
      
    
      # Run rsync.
      self._runRsync(
        sourcePath=folder,
        destPath=backupFolder,
        destHost=host,
        rsyncTimeout=timeout,
        encryptionKey=hostCapabilities[CAP_OPENSSL] and hostCapabilities[CAP_RSYNC_SMARTBOX] and encryptionKey or None,
        port = hostCapabilities[CAP_SSH_PORT],
        username=username,
        password=password,
        useFakeroot=hostCapabilities[CAP_FAKEROOT],
      )

      if timeout != None and timeout > 0:
        # Decrement timeout based on how much time has so far been spent on backup.
        stopTime = datetime.datetime.now()
        ellapsedTime = stopTime - startTime
        timeout -= ellapsedTime.seconds
        if timeout < 0 :
          timeout = 0


    # Log the number of bytes currently backed up
    backedUpBytes = 0
    for folder in folders :
      
      backupFolder = os.path.join(destBackupFolder, folder.lstrip("/"))
      duCommand = """du -s '%s' -s --bytes""" % (backupFolder)
      try :
        output, errorCode = smartbox.ssh.runSSHCommand(username, host, duCommand, port=hostCapabilities[CAP_SSH_PORT], password=password) 
        debugOutput("du %s --> %s" % (duCommand, output))
        
        size = 0
        for part in output.split() :
          try :
            size = int(part)
            break
          except ValueError:
            pass
      except :
        size = 0
      
      debugOutput(size)
      backedUpBytes += size
    smartbox.settings.set(BACKED_UP_BYTES, backedUpBytes)

    # Store the time of this backup.
    smartbox.settings.set(LAST_BACKUP_TIME, datetime.datetime.now())
    
    debugOutput("<BACKUP COMPLETED>: Bytes: %s/%s" % (backedUpBytes, backupBytes))
    
    # Flag that the backup succeeded
    smartbox.settings.set(LAST_BACKUP_STATUS, True)
    

  
  def restore(self, folders, restoreDir, hostname=None, username=None, password=None, encryptionKey=None, path=None) :
    """Restore files from the backup location."""

   
    # Get backup capabilities of the host.
    hostCapabilities = getHostCapabilities(hostname, username, password)
    
    # Check for basic connectivity and access to the backup host.
    if not hostCapabilities :
      raise Exception("Unable to connect to host %s for backup: the username and password may be incorrect or no ssh connection can be made." % (host))

    # Check rsync is available on the other end.
    if not hostCapabilities[CAP_RSYNC] :
      raise Exception("Cannot perform backup, since %s does not have rsync." % (host))

    sourceDir = path or hostCapabilities[CAP_BACKUP_FOLDER]
    sourceDir = os.path.join(sourceDir, username, "rsync")

    debugOutput("Restoring folders %s from %s@%s %s to %s" % (str(folders), username, hostname, sourceDir, restoreDir))

    # Ensure the restore directory exists.
    smartbox.system.run("mkdir -p '%s'" % restoreDir)
    
    for folder in folders :
      
      debugOutput("Processing folder %s" % folder)
      sourcePath = os.path.join(sourceDir, folder.lstrip("/"))
      
      # Run rsync
      self._runRsync(
        sourcePath=sourcePath,
        destPath=restoreDir,
        sourceHost=hostname,
        encryptionKey=encryptionKey,
        username=username,
        password=password,
        useFakeroot=hostCapabilities[CAP_FAKEROOT],
      )
      
  
  def _runRsync(self, sourcePath, destPath, sourceHost=None, destHost=None, username=None, password=None, rsyncTimeout=None, useFakeroot=None, encryptionKey=None, options=None, port=None) :
    """A wrapper for the rsync command."""

    options = options or ""

    rsyncCommand = encryptionKey and "rsync-smartbox" or "rsync"

    # Build up the command
    command = ""

    if rsyncTimeout : command = "timeout %s " % rsyncTimeout + command
    command += rsyncCommand

    # Build up the options
    options += " -vaz --delete-after --numeric-ids --timeout=60 "
    options += " --exclude='%s' " % REMOTE_BACKUPS_FOLDER # Don't backup backups!
    options += port and (" -e 'ssh -p %s' " % port) or " -e ssh "

    # Add fakeroot arg
    if useFakeroot and (destHost or sourceHost):
      fakerootStateFile = os.path.join(destHost and destPath or sourcePath, "fakeroot.state")
      #XXX
      fakerootStateFile = "fakeroot.state"
      options += " --rsync-path='fakeroot -s %s -i %s -- %s' " % (fakerootStateFile, fakerootStateFile, rsyncCommand)
    else :
      # Make sure we use the same rsync on remote host: e.g. patched or non-patched.
      options += " --rsync-path='%s' " % (rsyncCommand)
    
    # Add encryption filter
    if encryptionKey :
      os.putenv("BACKUP_KEY",encryptionKey) 
      if destHost : 
        options += " --source-filter='openssl enc -e -bf -pass env:BACKUP_KEY' --times-only "
        if MAX_RSYNC_FILE :
          options += " --max-size=%s " % MAX_RSYNC_FILE
      else :
        options += " --dest-filter='openssl enc -d -bf -pass env:BACKUP_KEY' "
    else :
      options += " --partial --partial-dir=.rsync-partial "

    command += " %s " % options

    # Source
    command += " %s%s " % (sourceHost and "%s@%s:" % (username, sourceHost) or "", sourcePath)
    
    # Dest
    command += " %s%s " % (destHost and "%s@%s:" % (username, destHost) or "", destPath)

    debugOutput(command)

    output, errorCode = smartbox.system.runExpect(command, events={"assword": "%s\n" % password, "yes/no":"yes\n"}, exitOnFail=False, timeout=None)
    debugOutput("OUTPUT: %s, %s" % (output, errorCode))
    
    if errorCode :
      raise Exception("rsync failed with code %s: %s" % (errorCode, None))


def getHostCapabilities(hostname, username, password) :
  """Gets the backup capabilities of a host (e.g. supports encryption, fakeroot, etc.)."""
  debugOutput("Getting capabilities for %s %s" % (hostname, username))

  capabilities = {}

  #
  # Detect the ssh port
  #
  for port in [22, smartbox.core.SMARTBOX_SSH_PORT] :
    try :
      smartbox.ssh.testSSHFolderAccess(username=username, host=hostname, password=password, port=port)
      capabilities[CAP_SSH_PORT] = port
      break
    except :
      pass

  if not CAP_SSH_PORT in capabilities :
    return {}

  #
  # Find a read write folder
  #
  
  # Try user's home
  try :
    homeDir = "/home/%s" % username
    if smartbox.ssh.testSSHFolderAccess(username=username, host=hostname, password=password, file=homeDir, port=capabilities[CAP_SSH_PORT]) :
      capabilities[CAP_BACKUP_FOLDER] = os.path.join(homeDir,REMOTE_BACKUPS_FOLDER)
  except :
    pass

  # Try /.smartbox-backups
  try :
    if smartbox.ssh.testSSHFolderAccess(username=username, host=hostname, password=password, file="/"+REMOTE_BACKUPS_FOLDER, port=capabilities[CAP_SSH_PORT]) :
      capabilities[CAP_BACKUP_FOLDER] = "/%s" % REMOTE_BACKUPS_FOLDER
  except :
    pass
  
  # We at least need an rw folder.
  if not capabilities[CAP_BACKUP_FOLDER] :
    return {}

  for cap, command in [(CAP_RSYNC, "rsync --help"), (CAP_RSYNC_SMARTBOX, "rsync-smartbox --help"), (CAP_FAKEROOT, "fakeroot ls"), (CAP_OPENSSL, "openssl --help")] :
    try :
      smartbox.ssh.runSSHCommand(username, hostname, command, password=password, port=capabilities[CAP_SSH_PORT])
      capabilities[cap] = True
    except :
      capabilities[cap] = False

  # XXX: Fakeroot causing problems
  capabilities[CAP_FAKEROOT] = False

  return capabilities





# Select the backup engine
backupEngine = Rsync()

#
# Tests
#

__test__ = {"tests":"""
"""}

def _test():
  import doctest
  doctest.testmod()

if __name__ == "__main__":
  # Run doctests
  _test()

  debugOutput("Testing")

  caps = getHostCapabilities("localhost","test","test")
  debugOutput("capabilities: %s" % caps)


