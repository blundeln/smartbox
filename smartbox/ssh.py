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
# ssh (ssh.py)
# ------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import os
import sbpexpect
from nbdebug import *
import smartbox.system

TIMEOUT = 60
SSHD_CONFIG = "/etc/ssh/sshd_config"

def addSSHPeer(username, password, host) :
  debugOutput("Adding ssh peer for %s to %s" % (username, host))

  # XXX: Does not always pick up root username. sshKeyFile = os.path.expanduser("~/.ssh/id_rsa.pub")
  sshKeyFile = os.path.expanduser("/root/.ssh/id_rsa.pub")
  if not os.path.exists(sshKeyFile) :
    debugOutput("Generating key file")
    expects = [  
      [".*Enter file in which to save the key.*:", "\n"],
      ["Enter passphrase.*:", "\n"],
      ["Enter same passphrase again.*:", "\n"],
      [".*", None],
    ]
    try :
      sbpexpect.expect("ssh-keygen -t rsa", expects, timeout=TIMEOUT)
    except Exception, e:
      raise Exception("Unable to generate ssh key in %s: %s" % (sshKeyFile, e))
  
  if not os.path.exists(sshKeyFile) :
    raise Exception("SSH key was not generated.")

  # If we don't have a security relation, add one
  if not testSSHFolderAccess(username, host) :
   
    debugOutput("No ssh peering, so trying to create one")

    # Copy the key
    expects = [  
      [["(?i)password","(?i)you sure you want to continue connecting"], ["%s" % password, "yes"]],
      [[None,"(?i)password"], [None, "%s" % password]],
    ]
    # if question  is sure, then yes, if question is password, answer is password
    try :
      sbpexpect.expect("ssh-copy-id -i %s %s@%s" % (sshKeyFile, username, host), qas=expects, timeout=TIMEOUT)
    except :
      raise Exception("Unable to create ssh peering with %s: check that the username, password and hostname are correct and that firewall or port forwarding settings are appropriately set on the destination." % host)

  # If we still don't have an ssh peering, raise an exception.
  if not testSSHFolderAccess(username, host) :
    raise Exception("Unable to create ssh peering with %s: check that the username, password and hostname are correct and that firewall or port forwarding settings are appropriately set on the destination." % host)

  debugOutput("ssh peering has been made successfully")


def testSSHFolderAccess(username, host, port=None, file="/tmp", password=None, timeout=TIMEOUT) :
  debugOutput("Tesing ssh access to %s@%s/%s" % (username, host, file))

  TEST_STRING = "access-test-file"
  testFile = os.path.join(file, "sshaccesstest")

  command = """echo %s > %s && cat %s ; rm %s """ % (TEST_STRING, testFile, testFile, testFile)

  try :
    output, errorCode = runSSHCommand(username, host, command, port=port, password = password, timeout=timeout)
  except Exception, e:
    raise Exception("Peering test failed with %s@%s: %s" % (username, host, e))
  
  if TEST_STRING in output :
    return True

  return False

def runSSHCommand(username, host, command, port=None, password=None, timeout=TIMEOUT) :
  sshCommand = """ssh %s@%s %s "%s" """ % (username, host, port and "-p %s" % port or "", command)
  debugOutput("running ssh command: %s" % sshCommand)
  if password :
    return sbpexpect.runExpect(sshCommand, events={"assword": "%s\n" % password,"yes/no":"yes\n"}, timeout=timeout)
  else :
    return sbpexpect.expect(sshCommand, [[".*", None]], timeout=timeout)


def addSSHPort(port) :
  debugOutput("Adding port %s" % port)
  sshdConfig = smartbox.system.readFromFile(SSHD_CONFIG)
  newPortString = "Port %s" % port
  if newPortString not in sshdConfig :
    sshdConfig = sshdConfig.replace("Port 22", "Port 22\n%s" % newPortString)
    sshdConfig = sshdConfig.replace("ListenAddress 1.0.0.0", "ListenAddress 0.0.0.0")
    smartbox.system.writeToConfigFile(SSHD_CONFIG, sshdConfig)
    debugOutput("Added port to sshd_config")
    restart()


def restart() :
  smartbox.system.run("/etc/init.d/ssh restart")


if __name__ == "__main__" :

  debugOutput("Testing")
  #output = runSSHCommand("root","smartbox","ls -alh", password="smartbox")
  #debugOutput(output)
