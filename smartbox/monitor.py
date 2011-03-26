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
# monitor (monitor.py)
# --------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import raid, system
import smartbox
import smartbox.remotebackup
import smartbox.settings
import smartbox.samba
import datetime
from nbdebug import *

class StatusMessage :
  def __init__(self, message, type, timestamp) :
    self.message, self.type, self.timestamp = message, type, timestamp

class MonitorHook(object):                                                                                                     
  def process_request(self, request):
    # Trigger monitor function on every interface request - to keep interface up-to-date
    monitor()
    #return request


ERRORS = "ERRORS"
WARNINGS = "WARNINGS"
LAST_ALARM_TIME = "LAST_ALARM_TIME"
ALARM_INTERVAL = 2 * 60 * 60

def reset() :
  smartbox.settings.set(WARNINGS, [])
  smartbox.settings.set(ERRORS, [])

def addMessage(message, type) :
  warnings = smartbox.settings.get(type, [])
  statusMessage = StatusMessage(message, type, datetime.datetime.now())
  # Update timestamp if warning message is already there.
  added = False
  for warning in warnings :
    if warning.message == statusMessage.message :
      warning.timestamp = statusMessage.timestamp
      added = True
      break

  if not added :
    warnings.append(statusMessage)

  # Save the messages
  smartbox.settings.set(type, warnings)

def removeMessage(match) :
  messages = smartbox.settings.get(WARNINGS, [])
  for message in messages[:] :
    debugOutput("msg: %s" % message.message)
    if message.message.split(":")[1].strip().startswith(match) :
      debugOutput("removeing: %s" % message.message)
      messages.remove(message)
  
  smartbox.settings.set(WARNINGS, messages)

  

def addError(message) :
  addMessage("ERROR: "+message, ERRORS)
  debugOutput(message)

def addWarning(message) :
  addMessage("WARNING: "+message, WARNINGS)
  debugOutput(message)

def getMessages() :
  messages = {}
  messages[ERRORS] = smartbox.settings.get(ERRORS, [])
  messages[WARNINGS] = smartbox.settings.get(WARNINGS, [])
  return messages

def monitor() :
  
  # Check raid
  raidStatus = raid.getStatus()
  if raidStatus :
    if raidStatus.status not in [raid.STATUS_OKAY, raid.STATUS_SYNCING] :
      addWarning("A disk has failed and must be replaced immediately to maintain your internal backup system.")
    else :
      removeMessage("A disk has failed")

  # Check remote backup
  remoteBackupStatus = smartbox.remotebackup.getStatus()
  if remoteBackupStatus :
    daysSinceBackup = remoteBackupStatus[smartbox.remotebackup.DAYS_SINCE_LAST_BACKUP]
    removeMessage("Remote backup")
    if daysSinceBackup > 1 :
      # Replace this message if necessary.
      addWarning("Remote backup has not been run successfully for %s days." % (daysSinceBackup))
    # XXX: Below flags an error during backup
    #elif not remoteBackupStatus[smartbox.remotebackup.LAST_BACKUP_STATUS] :
    #  addWarning("Remote backup did not complete successfully the last time it ran.")
    else :
      pass

  # Check samba netbios has not stopped.
  smartbox.samba.checkNmbd()

  # Sound the alarm if necessary.
  messages = getMessages()
  if messages[WARNINGS] or messages[ERRORS] :
    alarm()
  
  
def alarm() :
  lastAlarmTime = smartbox.settings.get(LAST_ALARM_TIME, None)
  debugOutput("lastAlarmTime: %s" % lastAlarmTime)
  now = datetime.datetime.now()
  if lastAlarmTime :
    ellapsedTime = (now - lastAlarmTime).seconds
  else :
    ellapsedTime = ALARM_INTERVAL + 1
 
  debugOutput("ellapsedTime: %s limit: %s now: %s" % (ellapsedTime, ALARM_INTERVAL, now))

  if ellapsedTime > ALARM_INTERVAL :
    smartbox.system.beep(smartbox.system.BEEP_WARNING)
    smartbox.settings.set(LAST_ALARM_TIME, datetime.datetime.now())
