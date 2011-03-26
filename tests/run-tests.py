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
# run-tests (run-tests.py)
# ------------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import os, unittest, time, sys, optparse
import nbutil.unittesttools
import seleniumtest
from nbdebug import *

argParser = optparse.OptionParser()
argParser.add_option("--list", action="store_true", help="", dest="listTests", default=False)

# Parse the command-line args.
(options, args) = argParser.parse_args()

SOURCE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__),".."))
#SELENIUM_PATH = "/home/blundeln/work/selenium/selenium-remote-control-0.9.2/selenium-server-0.9.2/selenium-server.jar"
SELENIUM_PATH = "/home/blundeln/work/selenium/selenium-remote-control-0.9.2-SNAPSHOT/selenium-server-0.9.2-SNAPSHOT/selenium-server.jar"
SELENIUM_SETUP_DELAY = 4

SUPERUSER_CODE = """
from django.contrib.auth.create_superuser import createsuperuser
createsuperuser('admin','admin@admin.com','admin')
exit
"""

def runCommand(command) :
  debugOutput(command)
  os.system(command)


def runSeleniumTests() :
  debugOutput("Running tests")
  
  # Launch selenium
  runCommand("""PATH=$PATH:/usr/lib/firefox java -jar %s -multiwindow > /dev/null 2>&1 &""" % SELENIUM_PATH)
  time.sleep(SELENIUM_SETUP_DELAY)

  try :
    testSequence = nbutil.unittesttools.parseTestSequence(sys.argv[2])
  except :
    testSequence = None


  testSuite = nbutil.unittesttools.loadFileOrderedTests(seleniumtest, testSequence=testSequence, listTests=options.listTests)
  debugOutput(testSuite)
  unittest.TextTestRunner(verbosity=3).run(testSuite)
 
  # Delay before kill
  time.sleep(5)

  # Kill selenium
  runCommand("""pkill -f "selenium-server.jar" """)
  

def runTests() :
  #from django.conf import settings
  #debugOutput("Running tests.")
  
  print "Running selenium tests"
  runSeleniumTests()

if __name__=="__main__" :
  runTests()
