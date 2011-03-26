#
# Copyright (C) 2008 Nick Blundell.
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
# make-iso (make-iso.py)
# ----------------------
#
# Description:
#  Modifies the ubuntu ISO
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import os, sys
from nbdebug import *

UBUNTU_ISO = sys.argv[1]
SOURCE_PATH = os.path.dirname(__file__)

def runCommand(command) :
  debugOutput(command)
  os.system(command)

def unpackISO(isoFile) :
  runCommand("rm -fr /tmp/sb-ubuntu")
  runCommand("mkdir -p /tmp/sb-ubuntu")
  runCommand("mount -o loop %s /tmp/sb-ubuntu" % isoFile)
  runCommand("cp -rT /tmp/sb-ubuntu /tmp/new-sb-ubuntu")
  runCommand("umount /tmp/sb-ubuntu")
  return "/tmp/new-sb-ubuntu"

def modifyPreseed(preseedFile) :
  preseed = open(preseedFile).read()
  if "Smartbox" not in preseed :
    preseed += "\n\n" + open(os.path.join(SOURCE_PATH, "preseed"),"r").read()
    ps = open(preseedFile,"w")
    ps.write(preseed)

def modifyIsolinux(configFile) :
  debugOutput(configFile)
  config = open(configFile,"r").read()
  config = config.replace("Install Ubuntu Server", "Install SmartBOX")
  conf = open(configFile, "w")
  conf.write(config)

def rebuildISO(sourcePath) :

  newISO = os.path.join("/tmp",os.path.basename(UBUNTU_ISO).replace("ubuntu","smartbox"))
  debugOutput(newISO)

  command = """
  mkisofs -r -V "SmartBOX Ubuntu Install CD" -cache-inodes -J -l -b isolinux/isolinux.bin -c isolinux/boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table -o %s %s
  """ % (newISO, sourcePath)

  runCommand(command)

  # Generate md5sum.
  runCommand("md5sum %s > %s" % (newISO, newISO+".md5"))

if __name__ == "__main__" :

  cdFolder = unpackISO(UBUNTU_ISO)

  runCommand("cp %s %s" % (os.path.join(SOURCE_PATH, "splash.pcx"), os.path.join(cdFolder, "isolinux")))
  runCommand("cp %s %s" % (os.path.join(SOURCE_PATH, "splash.rle"), os.path.join(cdFolder, "isolinux")))
  runCommand("cp %s %s" % (os.path.join(SOURCE_PATH, "install.sh"), os.path.join(cdFolder, "preseed")))

  modifyPreseed(os.path.join(cdFolder, "preseed", "ubuntu-server.seed"))
  modifyIsolinux(os.path.join(cdFolder, "isolinux", "isolinux.cfg"))

  rebuildISO(cdFolder)



