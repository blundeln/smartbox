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
# manipulators (manipulators.py)
# ------------------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import re

from django import forms, newforms
from django.core import validators

import smartbox.settings
import smartbox.core
import smartbox.samba
import smartbox.network
import smartbox.remotebackup
import smartbox.system
import smartbox.ssh

from nbdebug import *

PASSWORD_LENGTH = 15
USER_LENGTH = 25
SHARE_PERMISSION_DELIMETER = "---"

RE_USERNAME = r"""^[a-zA-Z][\w.]+$"""
RE_SHARENAME = r"""^[a-zA-Z][\w ]+$"""
RE_WORKGROUP = r"""^[a-zA-Z][\w.-]+$"""
RE_KEY = r"""^[a-zA-Z0-9]+$"""

#
# Validators
#

def validateRE(field_data, all_data, regex, message) :
  if not re.match(regex, field_data) :
    raise validators.ValidationError(message)

def isValidUsername(field_data, all_data): validateRE(field_data, all_data, RE_USERNAME, "This field cannot have spaces or non-standard characters.")
def isValidShareName(field_data, all_data): validateRE(field_data, all_data, RE_SHARENAME, "This field cannot have non-standard characters.")
def isValidWorkgroup(field_data, all_data): validateRE(field_data, all_data, RE_WORKGROUP, "This field cannot have spaces or non-standard characters.")
def isValidEncryptionKey(field_data, all_data): validateRE(field_data, all_data, RE_KEY, "The encryption key can have only letters and numbers, with no spaces.")

def getSharePermission(username, shareName) :
  return "%s%s%s" % (username, SHARE_PERMISSION_DELIMETER, shareName)

def parseSharePermission(sharePermission) :
  return sharePermission.split(SHARE_PERMISSION_DELIMETER)


class PermissionsManipulator(forms.Manipulator) :
  
  def __init__(self, users, shares) :
    debugOutput("Creating")
    self.users, self.shares = users, shares
    
    self.fields = []
    for user in users :
      for share in shares :
        self.fields.append(forms.CheckboxField(field_name=getSharePermission(user, share)))

  def flatten_data(self) :
    data = {}
    for user in self.users :
      for share in self.shares :
        data[getSharePermission(user, share)] = smartbox.samba.getSharePermission(user, share)
    return data

  def save(self, new_data) :
    debugOutput("Saving %s" % new_data)

    for user in self.users :
      for share in self.shares :
        sharePermission = getSharePermission(user, share)
        smartbox.samba.setSharePermission(user, share, sharePermission in new_data and new_data[sharePermission] or False)


class ShareManipulator(forms.Manipulator) :
  def __init__(self, share=None, create=False) :
    debugOutput("Creating with share %s" % share)

    self.share, self.create = share, create
    
    self.fields = [
      forms.TextField(field_name="description", maxlength=100, is_required=True),
      forms.CheckboxField(field_name="publicAccess"),
    ]

    if self.create :
      self.fields[0:0] = [forms.TextField(field_name="shareName", length=25, maxlength=25, is_required=True, validator_list=[isValidShareName])]
    else :
      self.fields[0:0] = [forms.HiddenField(field_name="shareName", is_required=True)]

  def flatten_data(self) :
    if not self.share :
      return {}

    if "guest ok" in self.share and self.share["guest ok"].lower() == "yes" :
      publicAccess = True
    else :
      publicAccess = False

    comment = "comment" in self.share and self.share["comment"] or "No description"

    return {
      "shareName":self.share["name"],
      "description":comment,
      "publicAccess":publicAccess,
    }

  def save(self, new_data) :
    debugOutput("Saving %s" % new_data)
    
    shareName = new_data["shareName"]
    description = new_data["description"]
    publicAccess = new_data["publicAccess"]

    if self.create and shareName not in smartbox.samba.getShares() :
      smartbox.samba.addShare(shareName, description=description, public = publicAccess)
    else :
      if shareName in smartbox.samba.getShares() :
        smartbox.samba.setShareDetails(shareName, description=description, public = publicAccess)


class UserManipulator(forms.Manipulator) : 
  def __init__(self, user=None, create=False, groups=None, systemOnly=False) :
    debugOutput("Creating")

    self.user = user
    self.create = create
    self.groups = groups
    self.systemOnly = systemOnly

    self.fields = [
      forms.TextField(field_name="name", maxlength=100, is_required=True),
      forms.PasswordField(field_name="password1", length=PASSWORD_LENGTH, maxlength=PASSWORD_LENGTH, is_required=self.create),
      forms.PasswordField(field_name="password2", length=PASSWORD_LENGTH, maxlength=PASSWORD_LENGTH, is_required=self.create, validator_list=[validators.AlwaysMatchesOtherField("password1",error_message="This must match the field above.")]),
    ]

    if self.create :
      self.fields[0:0] = [forms.TextField(field_name="username", length=USER_LENGTH, maxlength=USER_LENGTH, is_required=True, validator_list=[isValidUsername])]
    else :
      self.fields[0:0] = [forms.HiddenField(field_name="username", is_required=True)]


  def flatten_data(self) :
    if not self.user :
      return {}

    return {
      "name":self.user.name,
      "username":self.user.username,
    }


  def save(self, new_data) :
    debugOutput("Saving %s" % new_data)

    if self.create and new_data["username"] not in smartbox.system.getUserDetails() :
      smartbox.core.addUser(new_data["username"], new_data["password1"], new_data["name"], systemOnly=self.systemOnly)
      if self.groups :
        for group in self.groups :
          smartbox.system.addUserToGroup(new_data["username"], group)
    else :
      # Check the user exists.
      debugOutput(new_data)
      if "username" not in new_data : return
      username = new_data["username"]
      if username not in smartbox.system.getUserDetails() : return

      smartbox.core.setUserDetails(username, name=new_data["name"], password = "password1" in new_data and new_data["password1"] or None)


#class SettingsForm(newforms.Form) :

class SettingsManipulator(forms.Manipulator) : 
  
  def __init__(self) :
    
    choices=[[hour, "%s hours" % hour] for hour in ["2", "4", "6", "8", "10"]]
    # TODO: Do this properly.
    choices.append(["500", "No limit"])
    
    self.fields = [
      # Admin password
      forms.PasswordField(field_name="password1", length=PASSWORD_LENGTH, maxlength=PASSWORD_LENGTH),
      forms.PasswordField(field_name="password2", length=PASSWORD_LENGTH, maxlength=PASSWORD_LENGTH, validator_list=[validators.AlwaysMatchesOtherField("password1",error_message="This must match the field above.")]),
      
      # Network
      forms.TextField(field_name="hostname", maxlength=40, validator_list=[]),
      forms.TextField(field_name="domain", maxlength=40, validator_list=[isValidWorkgroup]),
      forms.SelectField(field_name="networkconfig", choices=[(x,x) for x in smartbox.network.configurations]),
      forms.TextField(field_name="address", maxlength=40),
      forms.TextField(field_name="netmask", maxlength=40),
      forms.TextField(field_name="gateway", maxlength=40),

      # Remote backup
      forms.TextField(field_name="peerHost", maxlength=40, validator_list=[self.validateBackupPeer]),
      forms.TextField(field_name="peerUsername", maxlength=40),
      forms.PasswordField(field_name="peerPassword", maxlength=40),
      forms.PasswordField(field_name="peerEncryptionKey", maxlength=40, validator_list=[isValidEncryptionKey]),
      forms.LargeTextField(field_name="peerNotes", maxlength=40),
      forms.TimeField(field_name="backupTime"),
      forms.SelectField(field_name="backupDuration", choices=choices),
    ]


  def validateBackupPeer(self, field_data, all_data) :
    if all_data["peerHost"] :
      hostCapabilities = smartbox.remotebackup.getHostCapabilities(all_data["peerHost"], all_data["peerUsername"], all_data["peerPassword"])
      if not hostCapabilities : 
        raise validators.ValidationError("Unable to connect to this backup host: check username and password.")

      # Test if rsync is available.
      if not hostCapabilities[smartbox.remotebackup.CAP_RSYNC] : 
        raise validators.ValidationError("The specified backup host does not support rsync, which is essential for efficient backups.")
      
      # Test encryption caps
      if all_data["peerEncryptionKey"] :
        if not hostCapabilities[smartbox.remotebackup.CAP_RSYNC_SMARTBOX] or not hostCapabilities[smartbox.remotebackup.CAP_OPENSSL] :
          raise validators.ValidationError("Although data transfer will be encrypted, the specified backup host does not support encrypted storage of the data.  Please set the encryption key to empty for this host.")


  def flatten_data(self) :

    networkDetails = smartbox.network.getNetworkDetails()
    
    # Load some settings.
    settings = smartbox.settings.get([
      smartbox.remotebackup.PEER_HOST,
      smartbox.remotebackup.PEER_USERNAME,
      smartbox.remotebackup.PEER_PASSWORD,
      smartbox.remotebackup.PEER_NOTES,
      smartbox.remotebackup.BACKUP_DURATION,
      smartbox.remotebackup.PEER_ENCRYPTION_KEY,
    ], ["","","","","10",""])

    return {
      "hostname": smartbox.network.getHostname(),
      "domain" : smartbox.samba.getDomain(),
      "networkconfig": networkDetails["configuration"],
      "address": networkDetails["address"],
      "netmask": networkDetails["netmask"],
      "gateway": networkDetails["gateway"],

      "peerHost": settings[smartbox.remotebackup.PEER_HOST],
      "peerUsername": settings[smartbox.remotebackup.PEER_USERNAME],
      "peerPassword": settings[smartbox.remotebackup.PEER_PASSWORD],
      "peerEncryptionKey": settings[smartbox.remotebackup.PEER_ENCRYPTION_KEY],
      "peerNotes": settings[smartbox.remotebackup.PEER_NOTES],
      "backupTime": smartbox.remotebackup.getBackupStartTime(),
      "backupDuration": settings[smartbox.remotebackup.BACKUP_DURATION],
    }
  
  def save(self, new_data) :
    debugOutput("new_data %s" % new_data)
    if "password1" in new_data and new_data["password1"] :
      smartbox.core.setAdminPassword(new_data["password1"])
    
    if "hostname" in new_data and new_data["hostname"] :
      smartbox.network.setHostname(new_data["hostname"])
    
    if "domain" in new_data and new_data["domain"] :
      smartbox.samba.setDomain(new_data["domain"])

    # Set network details.
    smartbox.network.setNetworkDetails(new_data["networkconfig"], new_data["address"], new_data["netmask"], new_data["gateway"])

    oldKey = smartbox.settings.get(smartbox.remotebackup.PEER_ENCRYPTION_KEY,"")

    # Set backup details.
    smartbox.settings.set([
      smartbox.remotebackup.PEER_HOST,
      smartbox.remotebackup.PEER_USERNAME,
      smartbox.remotebackup.PEER_PASSWORD,
      smartbox.remotebackup.PEER_ENCRYPTION_KEY,
      smartbox.remotebackup.PEER_NOTES,
      smartbox.remotebackup.BACKUP_DURATION,
    ], [
      new_data["peerHost"],
      new_data["peerUsername"],
      new_data["peerPassword"],
      new_data["peerEncryptionKey"],
      new_data["peerNotes"],
      int(new_data["backupDuration"]),
    ])

    smartbox.remotebackup.setBackupStartTime(new_data["backupTime"])

    # If encryption key changes, we have to clear all backed up data, otherwise previous encrytions may linger.
    newKey = smartbox.settings.get(smartbox.remotebackup.PEER_ENCRYPTION_KEY, "")
    if newKey != oldKey:
      try :
        smartbox.remotebackup.clearBackupData()
      except Exception, e:
        debugOutput("Unable to clear backup data: %s " % e)
