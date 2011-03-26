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
# views (views.py)
# ----------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext, Context
from django import forms

import smartbox.core
import smartbox.samba
import smartbox.system
import smartbox.remotebackup
import smartbox
import manipulators

from nbdebug import *


class ResponseException(Exception) :
  """Allows us to throw HttpResponses, which is very handy for nested function views."""
  def __init__(self, response) : self.response = response
  def __str__(self) : return "ResponseException %s" % self.response

def main(request) :
  
  shares = smartbox.samba.getShares()
  users = smartbox.core.getUsers()
  
  manipulator = manipulators.PermissionsManipulator(users, shares)
  
  shares = [shares[shareName] for shareName in shares]
  users = [users[username] for username in users]
  
  if request.POST :
    # Check for delete button.
    debugOutput(request.POST)
    new_data = request.POST.copy()
    errors = manipulator.get_validation_errors(new_data)
    if not errors :
      manipulator.do_html2python(new_data)
      manipulator.save(new_data)
      return HttpResponseRedirect("/")
  else :
    new_data = manipulator.flatten_data()
    errors = {}

  form = forms.FormWrapper(manipulator, new_data, errors)

  context = {
    "form":form,
    "users":users,
    "shares":shares,
  }
  return render_to_response("users.html", RequestContext(request, context))


def share(request, shareName=None) :
  
  debugOutput("shareName = %s" % shareName)
  
  shareName = shareName and shareName.rstrip("/") or shareName
  try : share = smartbox.samba.getShares()[shareName]
  except : share = None
  create = share == None
  
  # Add confirmation.
  try : confirmDelete = confirm(request, "delete", "Are you sure you wish to delete the file share <b>%s</b>? All data in the share will be lost." % shareName)
  except ResponseException, e: return e.response
  
  if confirmDelete : 
    debugOutput("Deleting share '%s'" % shareName)
    smartbox.samba.deleteShare(shareName)
    return HttpResponseRedirect("/")
  
  
  manipulator = manipulators.ShareManipulator(share=share, create=create)
  
  if request.POST :
    
    # Check for delete button.
    debugOutput(request.POST)

    new_data = request.POST.copy()
    errors = manipulator.get_validation_errors(new_data)
    if not errors :
      manipulator.do_html2python(new_data)
      manipulator.save(new_data)
      return HttpResponseRedirect("/")
  else :
    new_data = manipulator.flatten_data()
    errors = {}

  form = forms.FormWrapper(manipulator, new_data, errors)

  context = {
    "share":share,
    "form":form,
  }
  return render_to_response("share.html", RequestContext(request, context))


def confirm(request, variable, message, redirect=None) :
  
  confirmVariable = "%s-%s" % ("confirm", variable or "n")
  cancelVariable = "%s-%s" % ("cancel",variable or "n")
  
  if cancelVariable in request.POST : 
    debugOutput("Canceling request")
    raise ResponseException(HttpResponseRedirect(redirect or request.path))

  if confirmVariable in request.POST :
    return True
  
  if variable == None or variable and variable in request.POST :
    raise ResponseException(messageBox(request, message, [("Confirm",confirmVariable),("Cancel", cancelVariable)]))
  
  return False

def user(request, username=None, backupPeer=False) :

  debugOutput("username = %s" % username)

  username = username and username.rstrip("/") or username
  try : user = smartbox.system.getUserDetails()[username]
  except : user = None

  # Add confirmation.
  try : confirmDelete = confirm(request, "delete", "Are you sure you wish to delete the user account for <b>%s</b>? All associated data with that user will be lost." % username)
  except ResponseException, e: return e.response

  if backupPeer :
    manipulator = manipulators.UserManipulator(user=user, create = user == None, groups=[smartbox.remotebackup.BACKUP_GROUP], systemOnly=True)
  else :
    manipulator = manipulators.UserManipulator(user=user, create = user == None)
  
  if request.POST :
    
    if confirmDelete : 
      debugOutput("Deleting user '%s'" % username)
      if backupPeer :
        smartbox.remotebackup.deletePeerAccount(username)
        return HttpResponseRedirect("/settings")
      else :
        smartbox.core.deleteUser(username)
        return HttpResponseRedirect("/")

    new_data = request.POST.copy()
    errors = manipulator.get_validation_errors(new_data)
    if not errors :
      manipulator.do_html2python(new_data)
      manipulator.save(new_data)
      if backupPeer :
        return HttpResponseRedirect("/settings")
      else :
        return HttpResponseRedirect("/")
  else :
    new_data = manipulator.flatten_data()
    errors = {}

  form = forms.FormWrapper(manipulator, new_data, errors)
  
  context = {"sbuser":user, "form":form}
  
  return render_to_response("user.html", RequestContext(request, context))


def settings(request) :
  
  try : confirmRestore = confirm(request, "restoreBackupData", "Are you sure you wish to restore all data from the backup peer: current data will be overwritten; and depending on network speed and the amount of data, this may take a few hours to a few days.")
  except ResponseException, e: return e.response
  
  try : confirmDeleteBackupData = confirm(request, "clearBackupData", "Are you sure you wish to delete all current backup data on the backup peer: a lengthy full synchronisation will then follow on the next backup.")
  except ResponseException, e: return e.response
  
  # Process buttons.
  if confirmRestore :
    #smartbox.remotebackup.restore()
    smartbox.system.run("smartbox restore &")
    # TODO: A bit of ajax here could be used to determine progress of restoration - or at least when restore is complete.
    return HttpResponseRedirect(request.path)

  if confirmDeleteBackupData :
    smartbox.remotebackup.clearBackupData()
    return HttpResponseRedirect(request.path)
 

  if "resetStatusMessages" in request.POST :
    smartbox.monitor.reset()

  manipulator = manipulators.SettingsManipulator()
  
  if request.POST :
    
    # Check for delete button.
    debugOutput(request.POST)

    new_data = request.POST.copy()
    errors = manipulator.get_validation_errors(new_data)
    if not errors :
      manipulator.do_html2python(new_data)
      manipulator.save(new_data)
      return HttpResponseRedirect("/settings")
  else :
    new_data = manipulator.flatten_data()
    errors = {}

  form = forms.FormWrapper(manipulator, new_data, errors)
  
  context = {
    "form":form,
    "peerAccounts":smartbox.remotebackup.getPeerAccounts().items(),
    "smartboxPort":smartbox.core.SMARTBOX_SSH_PORT,
  }
  
  return render_to_response("settings.html", RequestContext(request, context))


def runCommand(request, command) :
  debugOutput(command)
  
  command = command.lower()

  debugOutput("request.POST: %s" % request.POST)

  try : confirmCommand = confirm(request, None,"Are you sure you wish to <b>%s</b> the server?" % command, redirect="/")
  except ResponseException, e: return e.response
  
  #if "Cancel" in request.POST : 
  #  debugOutput("Canceling request")
  #  return HttpResponseRedirect("/")
    
  #if "Confirm" not in request.POST :
  #  return messageBox(request, "Are you sure you wish to <b>%s</b> the server?" % command, ["Confirm","Cancel"])

  if confirmCommand :
    if command == "reboot" :
      smartbox.system.reboot()
      return messageBox(request, "Smartbox is rebooting - reload the main smartbox page in a moment", [])
    elif command == "shutdown" :
      smartbox.system.shutdown()
      return messageBox(request, "Smartbox is shutting down", [])
  else :
    return HttpResponseRedirect("/")
  

def messageBox(request, message, options) :
  next = "next" in request.POST and request.POST["next"] or "next" in request.GET and request.GET["next"] or None
  return render_to_response("message.html", RequestContext(request, {"message":message, "options":options, "next":next}))
