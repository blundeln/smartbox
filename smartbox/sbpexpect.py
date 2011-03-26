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
# sbpexpect (sbpexpect.py)
# ------------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import sys, time
import smartbox
import system, interface
from nbdebug import *

TIMEOUT = 5


def install() :
  if isInstalled() :
    return
  debugOutput("Installing pexpect")
  system.downloadUncompressInstall("http://pexpect.sourceforge.net/pexpect-2.3.tar.gz","cd pexpect-2.3 && python setup.py install")


def isInstalled() :
  try :
    import pexpect
    return True
  except: 
    return False


def expect(command, qas, timeout=TIMEOUT, ignoreExitCode=False) :
  debugOutput("%s: %s" % (command, qas))
  try :
    import pexpect
  except :
    debugOutput("No pexpect!")
    return

  if smartbox.options.testRun :
    return

  debugOutput("spawn(%s)" % command)
  process = pexpect.spawn(command)
  if smartbox.options.verbose :
    process.logfile = sys.stdout
  
  for qa in qas :

    questions = type(qa[0]) == list and qa[0] or [qa[0]]
    answers = type(qa[1]) == list and qa[1] or [qa[1]]

    for i in range(0, len(questions)) :
      if questions[i] == None :
        questions[i] = pexpect.EOF

    debugOutput("qs %s anws %s" % (questions, answers))
    try :
      debugOutput("expect(%s)" % str(questions))
      index = process.expect(questions, timeout=timeout)
      debugOutput("before: %s; after %s" % (process.before, process.after))
    except:
      raise Exception("Pexpect failed to parse: %s" % str(process))
    if answers[index] :
      debugOutput("sendline(%s)" % answers[index])
      process.sendline(answers[index])
  
  #output = process.expect(pexpect.EOF, timeout=timeout)
  
  # Hmmm.  If we digested the lot, use 'before' to give us some output.
  output = process.read() or process.before
 
  # Check the exit code.
  if not ignoreExitCode :
    while process.isalive() :
      time.pause(0.1)

    # XXX: This doesn't work yet.  
    if process.exitstatus != 0 :
      raise Exception("Command failed with exit code %s: %s" % (process.exitstatus, command))

  return output


def runExpect(command, events=None, exitOnFail=True, timeout=TIMEOUT) :
  import pexpect

  debugOutput("runing command:%s , events %s" % (command, events))

  def doTimeout(args) :
    raise Exception("Command timed out: %s" % command)

  events[pexpect.TIMEOUT] = doTimeout

  output, errorCode = pexpect.run(command, events=events, timeout=timeout, withexitstatus=1)
  if exitOnFail and errorCode :
    raise Exception("Command failed with exit code %s: %s: output: %s" % (errorCode, command, output))
  return output, errorCode
