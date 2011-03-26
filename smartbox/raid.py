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
# raid (raid.py)
# --------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import re
import time
from nbdebug import *
import smartbox
import smartbox.system

STATUS_SYNCING = "STATUS_SYNCING"
STATUS_OKAY = "STATUS_OKAY"
STATUS_DRIVE1_DOWN = "STATUS_DRIVE1_DOWN"
STATUS_DRIVE2_DOWN = "STATUS_DRIVE2_DOWN"
STATUS_UNKOWN = "STATUS_UNKOWN"

MDSTAT = "/proc/mdstat"
GRUB_MAP = "/boot/grub/device.map"

RE_RAID_STATUS = r"^(?P<raidDevice>md\d+)\s*:\s*active raid1 (?P<partitions>[^\n]+)\n\s+\d+ blocks (?P<status>[^\n]+)"
RE_DISK_ARRAY_ITEM = r"(?P<device>[a-zA-Z]+)(?P<partition>\d+)\[\d+\](?P<state>\(.*?\))?"
RE_GRUB_DEVICE_MAP = r"^\((?P<grubDev>.+)\)\s+(?P<sysDev>.+)$"

GRUB_TEMPLATE = """device (GRUB_DEVICE) SYS_DEVICE
root (GRUB_DEVICE,0)
setup (GRUB_DEVICE)
quit
"""

SLEEP_TIME = 5

class RAIDStatus :

  def __init__(self, mdstat) :
    self._parseStatus(mdstat)

  def getSurvivingDevice(self) :
    debugOutput("raidDevices %s deviceCount %s" % (self.raidDevices, self.deviceCount))
    for device in self.deviceCount :
      if self.deviceCount[device] == len(self.raidDevices) :
        return device

  def _parseStatus(self, mdstat) :

    debugOutput("mdstat: %s" % mdstat)

    self.devices = []
    self.failedDevices = []
    self.raidDevices = {}
    self.recoveryProgress = None
    self.status = None
    self.deviceCount = {}

    for match in re.finditer(RE_RAID_STATUS, mdstat, re.MULTILINE | re.DOTALL) :
      
      raidDevice = match.groupdict()["raidDevice"]
      status = match.groupdict()["status"]
      
      # Log the raid device.
      if raidDevice not in self.raidDevices :
        self.raidDevices[raidDevice] = None
    
      # Parse devices used by this raid device.
      for diskMatch in re.finditer(RE_DISK_ARRAY_ITEM, match.groupdict()["partitions"]) :
    
        debugOutput("diskMatch: %s" % diskMatch.groupdict())

        device = diskMatch.groupdict()["device"]
        partition = diskMatch.groupdict()["partition"]
        state = diskMatch.groupdict()["state"]
        debugOutput("device, partition, state: %s %s %s" % (device, partition, state))

        # Count the number of devices.
        if device not in self.deviceCount :
          self.deviceCount[device] = 1
        else :
          self.deviceCount[device] += 1
          

        # Log any devices we see.
        if device not in self.devices :
          self.devices.append(device)

        # Log the partition used by this raid device.
        self.raidDevices[raidDevice] = partition

        # Assume additional drive state is sign of a fault.
        if state and device not in self.failedDevices :
          self.failedDevices.append(device)
   
      # Check counts
      for device in self.deviceCount :
        if self.deviceCount[device] < len(self.raidDevices) and device not in self.failedDevices :
          self.failedDevices.append(device)
      
      # Try to parse RAID recovery progress.
      recoveryMatch = re.search(r"recovery\s*=\s*(?P<recoveryPercentage>.+?)%", mdstat)
      if recoveryMatch :
        self.recoveryProgress = float(recoveryMatch.groupdict()["recoveryPercentage"])

    debugOutput("raidDevices %s" % self.raidDevices)
    
    # Now set the status flag.
    if self.recoveryProgress != None :
      self.status = STATUS_SYNCING
    elif "[_U]" in mdstat :
      self.status = STATUS_DRIVE1_DOWN
    elif "[U_]" in mdstat :
      self.status = STATUS_DRIVE2_DOWN
    else :
      self.status = STATUS_OKAY


    debugOutput(self)


  def __str__(self) :
    return "status %s, devices %s, failedDevices %s, raidDevices %s, recoveryProgress %s." % (self.status, self.devices, self.failedDevices, self.raidDevices, self.recoveryProgress)
    


def getStatus() :

  if os.path.exists(MDSTAT) :
    mdstat = smartbox.system.readFromFile(MDSTAT)
  else :  
    return None

  return RAIDStatus(mdstat)


def isInstalled() :
  return getStatus()


def addNewDisk(newDevice) :
  
  debugOutput("Adding device '%s'." % newDevice)
 
  # Check the device exists.
  if not os.path.exists("/dev/%s" % newDevice) :
    smartbox.interface.abort("Device '%s' does not exist." % newDevice)

  # Check the disk has not already been partitioned.
  if smartbox.system.isPartitioned(newDevice) :
    smartbox.interface.abort("The device '%s' is already partitioned." % newDevice)

  raidStatus = getStatus()

  # Get the surviving raid device
  try :
    survivingDevice = raidStatus.getSurvivingDevice()
  except :
    smartbox.interface.abort("No surviving raid device can be found for partition cloning.")

  debugOutput("survivingDevice %s" % survivingDevice)

  # Clone the partitions from the surviving device to the new device.
  # TODO: Need to check out the consequences of doing --force here.
  force = True
  smartbox.system.run("sfdisk -d %s | sfdisk %s %s" % ("/dev/%s" % survivingDevice, force and "--force" or "", "/dev/%s" % newDevice))
  
  # Add the new disk partitions, mirroring the surviving device, to raid
  for raidDevice in raidStatus.raidDevices :
    smartbox.system.run("mdadm /dev/%s -a /dev/%s%s" % (raidDevice, newDevice, raidStatus.raidDevices[raidDevice]))

  
  # Poll RAID until the drives are synchronised.
  while True :
    time.sleep(SLEEP_TIME)
    if getStatus().status == STATUS_OKAY :
      break
  
  # Make sure grub is installed on the disk.
  updateGrub([newDevice])


def failRaidDevice(device) :
  """Force failure so we can test.""" 
  device = device.lstrip("/dev/")
  debugOutput("Failing RAID device %s" % device)

  raidStatus = getStatus()
  debugOutput("Raid devices: %s" % raidStatus.devices)
  
  # If the specified device is in the raid array.
  if device in raidStatus.devices :
    if raidStatus.status == STATUS_OKAY or device in raidStatus.failedDevices:
      debugOutput(raidStatus.raidDevices)
      # Fail the specified device.
      for raidDevice in raidStatus.raidDevices :
        debugOutput(raidDevice)
        smartbox.system.run("mdadm --manage --fail /dev/%s /dev/%s%s" % (raidDevice, device, raidStatus.raidDevices[raidDevice]), exitOnFail=False)
      

def removeRaidDevice(device) : 

  debugOutput("Removing device %s" % device)
  
  raidStatus = getStatus()
  if raidStatus.status in [STATUS_DRIVE1_DOWN, STATUS_DRIVE2_DOWN] and device in raidStatus.failedDevices :
    debugOutput("device %s has definitely failed" % device)
    for raidDevice in raidStatus.raidDevices :
      smartbox.system.run("mdadm /dev/%s -r /dev/%s%s" % (raidDevice, device, raidStatus.raidDevices[raidDevice]), exitOnFail=False)


def updateGrub(devices=None) :
  debugOutput("Installing grub")

  try :
    devices = devices or getStatus().devices
  except :
    devices = []
  
  # Configure grub for each device.
  for device in devices :
    debugOutput("Installing grub onto device %s" % device)
    grubConfig = GRUB_TEMPLATE.replace("SYS_DEVICE", "/dev/%s" % device).replace("GRUB_DEVICE", "hd0")
    debugOutput(grubConfig)
    
    if smartbox.options.testRun :
      continue
    
    grubin, grubout = os.popen4("grub --batch","w")
    grubin.write(grubConfig)
    grubin.close()
    debugOutput(grubout.read())
    grubout.close()


def getRaidCandidateDevices() :

  candidates = []

  raidStatus = getStatus()
  if not raidStatus : 
    return candidates
 
  debugOutput(raidStatus.status)

  if raidStatus.status not in [STATUS_DRIVE1_DOWN, STATUS_DRIVE2_DOWN] :
    return candidates

  debugOutput("Attempting to repair the raid array.")
  
  # Get the surviving raid device.
  survivingDevice = raidStatus.getSurvivingDevice()
  if not survivingDevice :
    smartbox.interface.abort("No surviving raid device can be found for partition cloning.")

  diskDevices = smartbox.system.getDiskDevices()
  debugOutput("diskDevices %s" % diskDevices)
  debugOutput("survivingDevice %s" % survivingDevice)

  for device in diskDevices :
    
    if device in [survivingDevice, "md"] :
      continue
    
    capacity = diskDevices[device]

    # If the drive has capacity greater than the raid device...
    if capacity > diskDevices["md"] :
      debugOutput("Device %s is a suitable disk for raid recovery" % device)
      candidates.append(device)

  return candidates


def autoRepair() :
  
  raidCandidates = getRaidCandidateDevices()
  debugOutput("Raid candidates: %s" % raidCandidates)
  if raidCandidates :
    addNewDisk(raidCandidates[0])


def updateRAID() :

  debugOutput("Preparing RAID")
  updateGrub()


#
# /proc/mdstat samples.
#

TEST_STATUS_OKAY = """
Personalities : [raid1]
md1 : active raid1 sda5[0] sdb5[1]
      353280 blocks [2/2] [UU]

md0 : active raid1 sda1[0] sdb1[1]
      8032384 blocks [2/2] [UU]

unused devices: <none>
"""

TEST_STATUS_FAIL1 = """
Personalities : [raid1] 
md1 : active raid1 sda5[1]
      353280 blocks [2/1] [_U]
      
md0 : active raid1 sda1[1]
      8032384 blocks [2/1] [_U]
      
unused devices: <none>
"""

TEST_STATUS_FAIL2 = """
Personalities : [raid1] 
md1 : active raid1 sda5[1]
      353280 blocks [2/1] [U_]
      
md0 : active raid1 sda1[1]
      8032384 blocks [2/1] [U_]
      
unused devices: <none>
"""

TEST_STATUS_FAIL3 = """
Personalities : [raid1] 

md1 : active raid1 sda5[0] sdb5[1]
      353280 blocks [2/2] [UU]
      
md0 : active raid1 sda1[1]
      8032384 blocks [2/1] [U_]
      
unused devices: <none>
"""

TEST_STATUS_FAIL4 = """
Personalities : [raid1] 
md1 : active raid1 hda5[2](F) hdb5[1]
369344 blocks [2/1] [_U]

md0 : active raid1 hda1[2](F) hdb1[1]
8016320 blocks [2/1] [_U]

unused devices: <none>
"""

TEST_STATUS_FAIL_ONLY = """
Personalities : [raid1] 
md1 : active raid1 sda5[2](F) sdb5[1]
      377408 blocks [2/1] [_U]
      
md0 : active raid1 sda1[2](F) sdb1[1]
      8008256 blocks [2/1] [_U]

unused devices: <none>
"""
      
TEST_STATUS_RECOVERY = """
Personalities : [raid1] 
md1 : active raid1 sda5[0] sdb5[1]
      353280 blocks [2/1] [_U]
      	resync=DELAYED
      
md0 : active raid1 sda1[2] sdb1[1]
      8032384 blocks [2/1] [_U]
      [=>...................]  recovery = 65.3% (471552/8032384) finish=10.8min speed=11580K/sec
      
unused devices: <none>
"""

TEST_FAILED_THEN_REBOOTED = """
Personalities : [raid1] 
md1 : active raid1 sda5[0] sdb5[1]
      377408 blocks [2/2] [UU]
      
md0 : active raid1 sdb1[1]
      8008256 blocks [2/1] [_U]
      
unused devices: <none>
"""
