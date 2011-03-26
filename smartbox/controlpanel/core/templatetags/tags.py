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
# tags (tags.py)
# --------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id: tags.py 412 2006-11-24 20:58:26Z blundeln $
#

from django import template
register = template.Library()
import django
import smartbox
import smartbox.system
import smartbox.util
import smartbox.raid
import smartbox.remotebackup
import smartbox.monitor

from smartbox.controlpanel.core.manipulators import getSharePermission

from nbdebug import *

#@register.simple_tag
def startSkinBox(name) :
  html = ""
  for i in range(0,8) :
    html += "<div class='%s%s clear'>" % (name, i+1)
  return html
register.simple_tag(startSkinBox)

#@register.simple_tag
def stopSkinBox(name) :
  return "</div>"*8
register.simple_tag(stopSkinBox)


@register.simple_tag
def version() :
  return smartbox.VERSION

@register.inclusion_tag("fieldrow.html", takes_context=True)
def fieldrow(context, field, label, editable=True, fieldNote=None) :

  visible = type(field.formfield) not in [django.forms.HiddenField]
 
  return {
    "visible":visible,
    "form":context["form"],
    "field":field,
    "label":label,
    "fieldNote":fieldNote,
  }


@register.simple_tag
def permissionField(form, user, share) :
  debugOutput("form %s user %s share %s" % (form.fields, user, share))
  key = getSharePermission(user.username, share["name"]) 
  debugOutput("key = %s" % key)
  return str(form[key])

@register.simple_tag
def progressBar(percentage, text, width=100, height=10) :

  barWidth = width * percentage / float(100)
  barWidth = barWidth > width and width or barWidth

  return """
  <div class="progressbar" style="width:%spx" align="left">
  <div class="bar" style="width:%spx">
  <div class="" style="font-size:%spx">&nbsp;</div><div class="text" style="width:%spx;font-size:%spx;">%s</div></div></div>
  """ % (width, barWidth, height, width, height, text or "&nbsp;")

@register.inclusion_tag("status.html", takes_context=True)
def statusBlock(context) :
  
  # Get disk usage.
  diskUsage = smartbox.system.getDiskUsage()
  diskPercent = 100 * (diskUsage["used"] / float(diskUsage["capacity"]))
  diskText = "%s/%s" % (smartbox.util.humanSize(diskUsage["used"]), smartbox.util.humanSize(diskUsage["capacity"]))

  raidStatus = smartbox.raid.getStatus()
  remoteBackupStatus = smartbox.remotebackup.getStatus()
  if smartbox.remotebackup.LAST_BACKUP_TIME in remoteBackupStatus and remoteBackupStatus[smartbox.remotebackup.LAST_BACKUP_TIME] :
    lastBackedUpAt = "Last backup: " + remoteBackupStatus[smartbox.remotebackup.LAST_BACKUP_TIME].strftime("%c")
  else :
    lastBackedUpAt = None

  return {
    "diskPercent":diskPercent,
    "diskText":diskText,
    "raidStatus":raidStatus,
    "remoteBackupStatus":remoteBackupStatus,
    "lastBackedUpAt":lastBackedUpAt
  }

@register.inclusion_tag("menu.html", takes_context=True)
def menuBlock(context) :
  return {}

@register.inclusion_tag("warnings.html", takes_context=True)
def warnings(context) :
  messages = smartbox.monitor.getMessages()
  return {"statusMessages":messages}
