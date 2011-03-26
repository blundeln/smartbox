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
# dialog (dialog.py)
# ------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import smartbox, interface, system, apt
from nbdebug import *

dialogInstance = None

def install() :
  debugOutput("Installing dialog.")
  apt.install("dialog")

def getDialog() :
  global dialogInstance
  if not dialogInstance :
    import dialog
    dialogInstance = dialog.Dialog(dialog="dialog")
    dialogInstance.add_persistent_args(["--backtitle", smartbox.COPYRIGHT])
  
  return dialogInstance

def handleCode(code) :
  if code in (dialogInstance.DIALOG_CANCEL, dialogInstance.DIALOG_ESC): interface.abort("")
