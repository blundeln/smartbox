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
# settings (settings.py)
# ----------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import os, pickle

SETTINGS_FILE = "/etc/smartbox.conf"

def load() :
  if not os.path.exists(SETTINGS_FILE) :
    return {}
  return pickle.load(open(SETTINGS_FILE,"r"))

def save(data) :
  return pickle.dump(data, open(SETTINGS_FILE,"wb"))

def get(settingNames, defaultValues) :
  
  wasList = type(settingNames) == list
  if not wasList :
    settingNames = [settingNames]
    defaultValues = [defaultValues]

  values = {}
  data = load()
  for settingName in settingNames :
    values[settingName] = settingName in data and data[settingName] or defaultValues[settingNames.index(settingName)]

  if wasList :
    return values
  else :
    return values.items()[0][1]


def set(settingNames, values) :
  
  wasList = type(settingNames) == list
  if not wasList :
    settingNames = [settingNames]
    values = [values]

  data = load()
  for settingName in settingNames :
    data[settingName] = values[settingNames.index(settingName)]
  
  save(data)
