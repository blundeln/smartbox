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
# rsnapshot (rsnapshot.py)
# ------------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import system, interface, apt
from nbdebug import *

def install(backupSources=None) :
  debugOutput("Installing rsnapshot")
  apt.install("rsnapshot")


  # TODO: Sort out config file handling.
  system.run("mkdir /.rsnapshot", exitOnFail=False)
  system.run("chmod +rx /.rsnapshot")

  rsnapshotConf = system.readFromFile("/etc/rsnapshot.conf")
  rsnapshotConf = rsnapshotConf.replace("snapshot_root\t/var/cache/rsnapshot/","snapshot_root\t/.rsnapshot/")
  #rsnapshotConf = rsnapshotConf.replace("#no_create_root\t1","no_create_root\t0")
  rsnapshotConf = rsnapshotConf.replace("#interval","interval")
  rsnapshotConf = rsnapshotConf.replace("\nbackup","\n#backup")

  rsnapshotConf += "\n\n"

  for backupSource in backupSources :
    rsnapshotConf += "backup\t%s/\tbackups/\n" % backupSource.rstrip("/")
  rsnapshotConf += "backup\t/home/\t.system/\n"
  rsnapshotConf += "backup\t/etc/\t.system/\n"

  debugOutput(rsnapshotConf)

  system.writeToConfigFile("/etc/rsnapshot.conf",rsnapshotConf)
  
  cronConf = system.readFromFile("/etc/cron.d/rsnapshot")
  cronConf = cronConf.replace("# 0","0")
  cronConf = cronConf.replace("# 30","30")
  cronConf = cronConf.replace("*/4","*")
  
  debugOutput(cronConf)
  
  system.writeToConfigFile("/etc/cron.d/rsnapshot", cronConf)
  
  interface.updateProgress()

  system.run("rsnapshot hourly")

  interface.updateProgress()
