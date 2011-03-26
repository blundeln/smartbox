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
# interface (interface.py)
# ------------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import sys
import smartbox
from nbdebug import *

progressDialog = None
currentStep = noProgressSteps = 0

def abort(message) :
  
  if smartbox.options.verbose :
    print("Aborting: %s" % message)
  else :
    showMessage(message)

  #TODO: in some cases it will be best to throw an exception here.
  sys.exit(1)

def showMessage(message, height=10, width=30) :
  import smartbox
  if smartbox.options.usedialog :
    import smartbox.nickdialog
    d = smartbox.nickdialog.getDialog()
    d.msgbox(message, height=height, width=width)
  else :
    print("%s" % message)
  

def prompt(message, default=None, password=False) :

  # XXX: Not sure why python wants this here - I'll have to investigate.
  import smartbox
  if smartbox.options.usedialog :
    import smartbox.nickdialog
    d = smartbox.nickdialog.getDialog()
    (code, input) = password and d.passwordbox(message) or d.inputbox(message, init=default or "")
    smartbox.nickdialog.handleCode(code)
  else :
    input = raw_input("%s%s: " % (message, default and " (%s)" % default or ""))
    if not input :
      input = default

    if not input :
      sys.exit(1)

  return input

  

def displayHeader(headerString) :
  if smartbox.options.usedialog :
    pass
  else :
    border = "="*len(headerString)
    print("%s\n%s\n%s" % (border, headerString, border))

def startProgress(title, noSteps=None) : 
  
  global progressDialog, noProgressSteps, currentStep
  debugOutput("title = '%s'" % title)
  noProgressSteps = noSteps
  currentStep = 0

  if not smartbox.options.usedialog : return

  import nickdialog
  assert(not progressDialog)
  progressDialog = nickdialog.getDialog()
  progressDialog.gauge_start("", title=title)

def stopProgress() :
  global progressDialog, noProgressSteps, currentStep
  debugOutput("Stopping: currentStep = '%s'." % currentStep)
  if not smartbox.options.usedialog : return
  global progressDialog
  if progressDialog :
    progressDialog.gauge_stop()
    progressDialog = None

def updateProgress(message=None, percent=None) :
  
  global progressDialog, noProgressSteps, currentStep
 
  if not percent :
    if noProgressSteps :
      currentStep += 1
      percent = 100 * (currentStep / float(noProgressSteps))
    else :
      percent = 0

  debugOutput("message = '%s', percent = '%s'" % (message, percent))
  if not smartbox.options.usedialog : return
  if not progressDialog :
    return
   
  percent = percent > 100 and 100 or percent
 
  if message :
    progressDialog.gauge_update(percent, message, update_text=1)
  else :
    progressDialog.gauge_update(percent)
    

def cleanup() :
  stopProgress()
