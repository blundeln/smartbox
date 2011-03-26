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
# seleniumtest (seleniumtest.py)
# ------------------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import unittest, time, re, os
import random
import smartbox.ssh
from selenium import selenium
import sys
import smartbox.sbpexpect
from nbdebug import *

HOST_STRING = sys.argv[1]
HOST = HOST_STRING.split(":")[0]
ADMIN_NAME = "Administrator"
ADMIN_PASS = "smartbox"
SERVER_ROOT_PASS = "smartbox"
TIMEOUT = "600000"
EXPECT_TIMEOUT = 30 * 10
REBOOT_WAIT_TIME = 50

MAX_GEN_FILE_SIZE = 10000
NO_TEST_FILES = 100

TEST_ENCRYPTION = True
#TEST_ENCRYPTION = False
BACKUP_FOLDERS = ["/users","/shares"]
#BACKUP_FOLDERS = None

sel = None

TEST_SSH_ACCOUNT = "/home/blundeln/work/smartbox/ssh-test-account.txt"  


class TestBase(unittest.TestCase):
  
  def setUp(self):
    global sel
    if not sel :
      self.refreshSelenium()
    goFast()

  def refreshSelenium(self) :
    global sel
    if sel :
      sel.stop()
      sel = None
    sel = selenium("localhost", 4444, "*firefox", getWebRoot())
    sel.start()


  def assertInBody(self, text) :
    self.assertTrue(text in sel.get_html_source())
  
  def assertNotInBody(self, text) :
    self.assertTrue(text not in sel.get_html_source())
  
  def assertInText(self, text) :
    self.assertTrue(text in sel.get_body_text())
  
  def assertNotInText(self, text) :
    self.assertTrue(text not in sel.get_body_text())

  def tearDown(self) :
    pause(3)



class InitialTests(TestBase) :

  def testFrontPage(self) :
    openPage("/")
    self.assertInBody("Users")
    self.assertInBody("File shares")


class UserTests(TestBase) :

  def testAddUsers(self) :
    self.addUserAndCheck(username="fred", name="Fred Bloggs", password="fred")
    self.addUserAndCheck(username="mary.jane",name="Mary Jane", password="mary")
    self.addUserAndCheck(username="jamie", name="Jamie Hillman", password="jamie")
    
  def addUserAndCheck(self, username, name, password) :  
    addUser(username=username, name=name, password=password)
    self.assertInBody(username)
    self.assertInBody(name)

    # Test that the logon batch file was created and has correct drive mappings.
    output = readSambaFile(username, password, HOST, "netlogon", "%s.bat" % username)
    self.assertTrue(r"""net use * "\\%s\backups""" % (HOST) in output)
    
    # Test the user can rw their own share.
    self.assertTrue(testShareAccess(username, password, HOST, username, mode="rw"))
    self.assertFalse(testShareAccess(username, password, HOST, "backups", mode="rw"))

  def testHomePermissions(self):
    self.assertTrue(testShareAccess("jamie", "jamie", HOST, "jamie", mode="rw"))
    self.assertFalse(testShareAccess("jamie", "jamie", HOST, "fred", mode="w"))
    self.assertFalse(testShareAccess("jamie", "jamie", HOST, "fred", mode="r"))
   
  def testEditUser(self) :

    openPage("/")
    sel.click("link=(fred)")
    wait()
    sel.type("name","John Smith")
    sel.type("password1","new pass")
    sel.type("password2","new pass")
    sel.click("save")
    wait()
    openPage("/")
    self.assertInBody("John Smith")
    
    # Check password change has been effective.
    self.assertFalse(testShareAccess("fred", "fred", HOST, "fred", mode="rw"))
    self.assertTrue(testShareAccess("fred", "new pass", HOST, "fred", mode="rw"))

  
  def testBadUsers(self) :  
    
    addUser(username="Bad$us?ernam", name="Fred Bloggs", password="fred")
    self.assertInBody("This field cannot have spaces or non-standard characters")

    addUser(username="hellome", name="Fred Bloggs", password="fred", password2="donkey")
    self.assertInBody("This must match the field above")


class ShareTests(TestBase) :

  def testAddShares(self) :
    self.addShareAndCheck(shareName="My Share", description="My share for things")
    self.addShareAndCheck("Secret Share", "Some secrets")
    self.addShareAndCheck("Python stuff", "Things about python")
    self.addShareAndCheck("Public Share", "A share for the public")

  def testSetPublicShare(self) :
    debugOutput("Adding public share")
    shareName = "Public Share"
    addShare(shareName,"A public share", public=True)
    self.assertInText(shareName)
    # Test anonymous access to the share
    self.assertTrue(testShareAccess("guest", "", HOST, shareName, mode="rw"))
    
    # Now remove public access and test it worked
    openPage("/")
    sel.click("link=%s" % shareName)
    wait()
    self.assertTrue(sel.is_checked("publicAccess"))
    sel.uncheck("publicAccess")
    sel.click("save")
    wait()
    self.assertFalse(testShareAccess("guest", "", HOST, shareName, mode="rw"))
  
  def testEditShares(self) :
    openPage("/")
    shareName = "Secret Share"
    sel.click("link=%s" % shareName)
    wait()
    sel.type("description","A new description")
    sel.click("save")
    wait()
    openPage("/")
    shareName = "Secret Share"
    sel.click("link=%s" % shareName)
    wait()
    self.assertTrue(sel.get_value("description") == "A new description")

  
  def addShareAndCheck(self, shareName, description) :
    addShare(shareName, description)
    self.assertInText(shareName)
    # Test samba access of the share
    self.assertTrue(testShareAccess("Administrator", "smartbox", HOST, shareName, mode="rw"))


class SharePermissionsTests(TestBase) :

  def testBasicPermissions(self):
  
    # Mary can rw her own stuff but not other users'.
    self.assertTrue(testShareAccess("mary.jane", "mary", HOST, "mary.jane", mode="rw"))
    self.assertFalse(testShareAccess("mary.jane", "mary", HOST, "fred", mode="r"))
    self.assertFalse(testShareAccess("mary.jane", "mary", HOST, "fred", mode="w"))
  
  def testPermissionsInterface(self):
    
    openPage("/")
    sel.check("id_jamie---Python stuff")
    sel.click("save")
    wait()
    # Check the right box is now ticked.
    self.assertTrue(sel.is_checked("id_jamie---Python stuff"))

    # Check permissions via samba.
    self.assertTrue(testShareAccess("jamie", "jamie", HOST, "Python stuff", mode="rw"))
    self.assertFalse(testShareAccess("jamie", "jamie", HOST, "Secret Share", mode="r"))
    self.assertFalse(testShareAccess("jamie", "jamie", HOST, "Secret Share", mode="w"))
    self.assertTrue(testShareAccess("jamie", "jamie", HOST, "jamie", mode="rw"))

    # Now remove permissions.
    sel.uncheck("id_jamie---Python stuff")
    sel.click("save")
    wait()
    # Check the right box is now not ticked.
    self.assertFalse(sel.is_checked("id_jamie---Python stuff"))

    # Check permissions via samba.
    self.assertFalse(testShareAccess("jamie", "jamie", HOST, "Python stuff", mode="r"))
    self.assertFalse(testShareAccess("jamie", "jamie", HOST, "Python stuff", mode="rw"))
    
    # Now add permissions again.
    sel.check("id_jamie---Python stuff")
    sel.click("save")
    wait()
    
    self.assertTrue(testShareAccess("jamie", "jamie", HOST, "Python stuff", mode="rw"))


class DataLoadTests(TestBase) :

  def testGenerateData(self) :

    noFiles = 300
    MAX_FILE_SIZE = 1000
    random.seed("a seed")

    # Generate some files
    prefix = "/tmp/sbtestdata"
    self.testDataFolder = generateData(prefix, noFiles, MAX_FILE_SIZE)

    # Put some files in a user folder.
    output = runSambaCommand("fred", "new pass", HOST, "fred", "lcd %s; recurse; prompt; mput %s" % (os.path.dirname(prefix), os.path.basename(prefix)))
    self.assertTrue("NT_STATUS" not in output)

    # For each share
    output = runSambaCommand("jamie", "jamie", HOST, "Python stuff", "lcd %s; recurse; prompt; mput %s" % (os.path.dirname(prefix), os.path.basename(prefix)))
    self.assertTrue("NT_STATUS" not in output)


  def testCleanUp(self) :
    os.system("rm -fr /tmp/sbtestdata")


class HistoricalBackupTests(TestBase) :
  
  def testRsnapshot(self) :
    
    # Delete any rsnapshots
    runSmartboxCommand("rm -fr /.rsnapshot/*")
    # Check none there
    self.assertFalse("hourly" in runSmartboxCommand("ls -alh /.rsnapshot")[0])
    # Invoke rsnapshot
    for days in range(0,2) :
      for hours in range(0,6) :
        runSmartboxCommand("rsnapshot hourly")
      runSmartboxCommand("rsnapshot daily")
    
    snapshotList, errorCode = runSmartboxCommand("ls -alh /.rsnapshot")
    # Check they are all there
    for i in range(0,2) :
      self.assertTrue(("daily.%s" % i) in snapshotList)
    for i in range(0,5) :
      self.assertTrue(("hourly.%s" % i) in snapshotList)
    

  def testRsnapshotAccess(self) :

    # User can read but not write to backup of their home share.
    self.assertTrue(testShareAccess("jamie", "jamie", HOST, "backups", mode="r", path="hourly.3/backups/users/jamie"))
    self.assertFalse(testShareAccess("jamie", "jamie", HOST, "backups", mode="rw", path="hourly.4/backups/users/jamie"))
    
    # User can read backup of their permitted shares.
    self.assertTrue(testShareAccess("jamie", "jamie", HOST, "backups", mode="r", path="daily.1/backups/shares/Python stuff"))
    
    # User cannot read backup of other user's home share or non permitted share.
    self.assertFalse(testShareAccess("fred", "new pass", HOST, "backups", mode="r", path="hourly.3/backups/users/jamie"))
    self.assertFalse(testShareAccess("fred", "new pass", HOST, "backups", mode="r", path="daily.1/backups/shares/Python stuff"))


class BackupTests(TestBase) :

  def testCreateBackupAccount(self) :

    openPage("/settings")
    sel.click("link=[Add new peer account]")
    wait()
    sel.type("username","backup1")
    sel.type("name","A backup account")
    sel.type("password1","smartbox")
    sel.type("password2","smartbox")
    sel.click("save")
    wait()

  def testAddRemoteSmartboxPeer(self) :
    self.setRemotePeer(hostname="localhost", username="backup1", password="smartbox", key=TEST_ENCRYPTION and "encryptme123" or None)
    self.assertNotInText("Please correct the following error")
  
  
  def testPartialBackup(self) :
    
    self.runBackup(folders=BACKUP_FOLDERS, timeout=2, clearBackups=True)
    openPage("/")
    self.assertInBody("full backup may take several days")
    
 
  

  def testFullBackup(self) :
    
    # Invoke a long backup on the server.
    self.runBackup(folders=BACKUP_FOLDERS)
    
    # Test that the interface reflects the full backup status.
    openPage("/")
    self.assertInBody("Your smartbox is fully synchronised with the remote smartbox")

  def testRemoteSSHPeerBackup(self) :
    hostname, username, password = getTestSSHAccount()
    self.setRemotePeer(hostname=hostname, username=username, password=password)
    self.assertNotInText("Please correct the following error")
    
    # Invoke a long backup on the server.
    self.runBackup(folders=["/users","/shares"])
    
    # Test that the interface reflects the full backup status.
    openPage("/")
    self.assertInBody("Your smartbox is fully synchronised with the remote smartbox")
 
  def runBackup(self, folders=None, timeout=None, clearBackups=False) :

    if clearBackups :
      # Remove any traces of previous backups.
      runSmartboxCommand("rm -rf /.smartbox-backups/*")

    # Invoke a long backup on the server.
    command = "smartbox backup"
    if timeout :
      command += " %s" % timeout
    if folders :
      command += " --folders='%s'" % ",".join(folders)
    runSmartboxCommand(command, timeout=None)
    pause(2)


  def setRemotePeer(self, hostname, username, password, key=None) :
    openPage("/settings")
    sel.type("peerHost", hostname)
    sel.type("peerUsername", username)
    sel.type("peerPassword", password)
    if key :
      sel.type("peerEncryptionKey",key)
    else :
      sel.type("peerEncryptionKey","")
    sel.type("peerNotes","A nice backup server")
    sel.type("backupTime","12:12")
    sel.select("backupDuration","8 hours")
    sel.submit("settings-form")
    wait()

  def xxxtestBrokenBackup(self) :

    # Change the backup user account.
    openPage("/backup-peer/backup1")
    sel.type("username","backup1")
    sel.type("name","A backup account")
    sel.type("password1","changedpass")
    sel.type("password2","changedpass")
    sel.click("save")
    wait()
   
    # Invoke a long backup on the server.
    try :
      runSmartboxCommand("smartbox backup")
    except :
      pass
    
    pause(2)
    openPage("/")
    self.assertInBody("The last backup failed")
    self.assertInBody("WARNING: Remote backup did not complete successfully the last time it ran")
    
    # Put the config back.
    # Change back the backup account password.
    openPage("/backup-peer/backup1")
    sel.type("username","backup1")
    sel.type("name","A backup account")
    sel.type("password1","backup")
    sel.type("password2","backup")
    sel.click("save")
    wait()

    # Invoke a long backup on the server.
    runSmartboxCommand("smartbox backup")
    runSmartboxCommand("smartbox monitor")
    pause(2)
    openPage("/")
    self.assertNotInBody("The last backup failed")
    self.assertNotInBody("WARNING: Remote backup did not complete successfully the last time it ran")
    self.assertInBody("Your smartbox is fully synchronised with the remote smartbox")
 
  
class RestoreTests(TestBase) :
  
  def testRestore(self) :
    # Invoke the restore
    runSmartboxCommand("rm -fr /restore-test")
    #restoreCommand = "smartbox restore ssh://backup1@localhost//.smartbox-backups/backup1/rsync /restore-test --password smartbox %s %s" % (TEST_ENCRYPTION and "--key encryptme123" or "", BACKUP_FOLDERS and "--folders=%s" % ",".join(BACKUP_FOLDERS) or "")
    restoreCommand = "smartbox restore backup1@localhost /restore-test --password=smartbox %s %s" % (TEST_ENCRYPTION and "--key encryptme123" or "", BACKUP_FOLDERS and "--folders=%s" % ",".join(BACKUP_FOLDERS) or "")
    output = runSmartboxCommand(restoreCommand, timeout=None)
    debugOutput("OUTPUT: %s" % str(output))

    # TODO: Get listings of /etc without modified times.

    # Check folders are identical.
    folders = BACKUP_FOLDERS or ["home","users","shares","root"]
    #lsCommand = "ls -RAlh . --ignore='blundeln' --ignore='netlogon' --ignore='back1' --ignore='.ssh' --ignore='.subversion' --ignore='.smartbox-backups' --ignore='fakeroot.state'"
    lsCommand = "ls -R . --ignore='blundeln' --ignore='netlogon' --ignore='back1' --ignore='.ssh' --ignore='.subversion' --ignore='.smartbox-backups' --ignore='fakeroot.state'"
    sourceListing = ""
    restoredListing = ""
    for folder in folders :
      sourceListing += runSmartboxCommand("cd /%s; %s" % (folder, lsCommand))[0]
      restoredListing += runSmartboxCommand("cd /restore-test/%s; %s" % (folder, lsCommand))[0]
    
    open("/tmp/d1","w").write(sourceListing)
    open("/tmp/d2","w").write(restoredListing)
    self.assertTrue(sourceListing == restoredListing)

 



class ControlTests(TestBase) :
  
  def xtestReboot(self) :
    openPage("/command/reboot")
    sel.click("//*[@value='Confirm']")
    wait()
    self.assertInText("The system is going down")
    # TODO: Poll the smartbox until we see it again.
    pause(REBOOT_WAIT_TIME)
    openPage("/")
    self.assertInBody("Users")
    



class SettingsTests(TestBase) :

  def xxxtestAdminPasswordChange(self) :
    
    global ADMIN_PASS
    openPage("/settings")
    newPassword = "newpass"
    sel.type("password1", newPassword)
    sel.type("password2", newPassword)
    sel.submit("settings-form")
    oldPass = ADMIN_PASS
    ADMIN_PASS = newPassword
    
    # Check we can see the page using new password
    openPage("/")
    self.assertInBody("File shares")

    self.assertTrue(testShareAccess("Administrator", newPassword, HOST, "Files", mode="rw"))
    
    # Now change it back
    openPage("/settings")
    sel.type("password1", oldPass)
    sel.type("password2", oldPass)
    sel.submit("settings-form")
    ADMIN_PASS = oldPass

    # And again test the password allows us to the front page.
    openPage("/")
    self.assertInBody("File shares")
  
    self.assertFalse(testShareAccess("Administrator", newPassword, HOST, "Files", mode="rw"))
    self.assertTrue(testShareAccess("Administrator", oldPass, HOST, "Files", mode="rw"))
 
  def testSettingsDomain(self) :
    
    openPage("/settings")
    oldDomain = sel.get_value("domain")
    sel.type("domain","CHIPS")
    sel.submit("settings-form")
    wait()
    pause(10)
    self.assertTrue(sel.get_value("domain") == "CHIPS")
    self.assertTrue("Domain=[CHIPS]" in getShareListing(HOST))
    
    sel.type("domain", oldDomain)
    sel.submit("settings-form")
    wait()
    pause(10)
    self.assertTrue(sel.get_value("domain") == oldDomain)
    self.assertTrue("Domain=[%s]" % oldDomain in getShareListing(HOST))


  def testSettingsHostname(self) :
    global HOST
    
    # Change hostname
    openPage("/settings")

    # Change the hostname
    newHostname = "frank"
    sel.type("hostname","frank")
    sel.submit("settings-form")
    oldHostname = HOST
    HOST = newHostname

    # Check we can access the interface using the new hostname.
    pause(20)
    self.refreshSelenium()
    openPage("/")
    self.assertInBody("File shares")

    # Now change the hostname back.
    openPage("/settings")

    # Change the hostname
    sel.type("hostname", oldHostname)
    sel.submit("settings-form")
    HOST = oldHostname
    pause(20)
    self.refreshSelenium()
  

  def testIPAddress(self) :
    global HOST
    
    openPage("/settings")
  
    self.assertTrue(sel.get_selected_value("networkconfig") == "DHCP")
    dhcpAddress = sel.get_value("address")

    # Change to static address
    sel.select("networkconfig","STATIC")
    staticAddress = dhcpAddress.split(".")
    staticAddress[3] = str(int(staticAddress[3])+1)
    staticAddress = ".".join(staticAddress)
    sel.type("address",staticAddress)
    sel.submit("settings-form")
    
    # Re-launch browser using new host address.
    oldHostname = HOST
    HOST = staticAddress
    pause(15)
    self.refreshSelenium()

    # Now change back to dhcp
    openPage("/settings")
    sel.select("networkconfig","DHCP")
    sel.submit("settings-form")
  
    # Now re-launch browser
    HOST = oldHostname
    pause(20)
    self.refreshSelenium()
    openPage("/")
    self.assertInBody("File shares")




class ClosureTests(TestBase) :
  
  def testDeleteShares(self) :
    for shareName in ["My Share","Secret Share", "Python stuff", "Public Share"] :
      deleteShare(shareName)
      openPage("/")
      self.assertNotInText(shareName)
  
  def testDeleteUsers(self) :

    for username in ["fred","mary.jane","jamie"] :
      deleteUser(username)
      openPage("/")
      self.assertNotInBody("(%s)" % username)
 
  def testDeleteBackupAccount(self) :
    openPage("/backup-peer/backup1")
    wait()
    sel.click("delete")
    wait()
    sel.click("//*[@value='Confirm']")
    wait()
    self.assertNotInText("backup1")

  def testClearRemotePeer(self) :
    openPage("/settings")
    sel.type("peerHost","")
    sel.type("peerUsername","")
    sel.type("peerPassword","")
    sel.type("peerEncryptionKey","")
    sel.type("peerNotes","")
    sel.submit("settings-form")
    wait()
    self.assertNotInText("Please correct the following error")


  def testClearRestoreFiles(self) :
    runCommand("rm -rf /tmp/d1")
    runCommand("rm -rf /tmp/d2")



#
# Helper classes and methods.
#


def wait() : sel.wait_for_page_to_load(TIMEOUT)
def goSlow(speed=2000) : sel.set_speed(speed)
def goFast() : sel.set_speed(0)
def pause(secs=10) : time.sleep(secs)

def getWebRoot() :
  try :
     port = ":%s" % HOST_STRING.split(":")[1]
  except :
    port = ""
  webroot = "http://%s:%s@%s%s" % (ADMIN_NAME, ADMIN_PASS, HOST, port)
  debugOutput("webroot = %s" % webroot)
  return webroot

def openPage(page) :
  sel.open("%s%s" % (getWebRoot(), page))
  wait()

def addUser(username, name, password, password2=None) :
  if not password2 : password2 = password

  openPage("/")
  sel.click("link=[Add user]")
  wait()
  sel.type("username",username)
  sel.type("name",name)
  sel.type("password1",password)
  sel.type("password2",password2)
  sel.click("save")
  wait()

def deleteUser(username) :
  openPage("/")
  sel.click("link=(%s)" % username)
  wait()
  sel.click("delete")
  wait()
  sel.click("//*[@value='Confirm']")
  wait()

def addShare(shareName, description, public=False) :
  openPage("/")
  sel.click("link=[Add share]")
  wait()
  sel.type("shareName",shareName)
  sel.type("description",description)
  if public :
    sel.check("publicAccess")
  sel.click("save")
  wait()

def deleteShare(shareName) :
  openPage("/")
  sel.click("link=%s" % shareName)
  wait()
  sel.click("delete")
  wait()
  sel.click("//*[@value='Confirm']")
  wait()

def testShareAccess(username, password, server, shareName, mode="r", path=None) :

  debugOutput("Testing %s access (%s) to share %s" % (username, mode, shareName))
  
  # XXX: Sometimes a share is hidden but you have access, so I'll drop this test for now.
  # Can we see the share?
  #output = runCommand("""smbclient -L %s -U "%s"%%"%s" """ % (server, username, password))
  #if shareName not in output :
  #  return False

  # Can we view the share
  if "r" in mode :
    output = runSambaCommand(username, password, server, shareName, "%sls" % (path and "cd \"%s\"; " % path or ""))
    if "NT_STATUS" in output :
      return False
  
  if "w" in mode :
    output = runSambaCommand(username, password, server, shareName, "%smkdir test1; rmdir test1" % (path and "cd \"%s\"; " % path or ""))
    if "NT_STATUS" in output :
      return False

  return True
  

def getShareListing(server, username="", password="") :
  return runCommand("""smbclient -L %s -U "%s"%%"%s" """ % (server, username, password))

def readSambaFile(username, password, server, shareName, filename) :

  tempFile = "/tmp/samba-read"
  runCommand("rm -fr %s" % tempFile)
  output = runSambaCommand(username, password, server, shareName, "get %s %s" % (filename, tempFile))
  if "NT_STATUS" in output :
    return ""
  f = open(tempFile,"r")
  data = f.read()
  f.close()

  os.remove(tempFile)
  return data

def runSambaCommand(username, password, server, shareName, command) :
  output = runCommand("""smbclient //"%s"/"%s" -U "%s"%%"%s" -c '%s' """ % (server, shareName, username, password, command))
  return output

def runCommand(command, input=None) :
  debugOutput(command)
  
  # Retry if connection failes - remember: we are constantly restarting samba server.
  while True :
    output = os.popen4(command)[1].read()
    if "Connection to smartbox failed" in output :
      debugOutput("Connection failed so retrying!")
    else :
      break
    time.sleep(1)
  
  debugOutput("OUTPUT: %s" % output)
  return output

def runSmartboxCommand(command, timeout=EXPECT_TIMEOUT) :
  return runSSHCommand("root",HOST, command, password=SERVER_ROOT_PASS, timeout=timeout)

def runSSHCommand(username, host, command, password=None, timeout=30) :
  sshCommand = """ssh %s@%s "%s" """ % (username, host, command)
  debugOutput("running ssh command: %s" % sshCommand)
  if password :
    return smartbox.sbpexpect.runExpect(sshCommand, events={"root@%s's password" % HOST: "%s\n" % password,"yes/no":"yes\n"}, timeout=timeout)
  else :
    return smartbox.sbpexpect.expect(sshCommand, [[".*", None]], timeout=timeout)

def generateData(prefix="/tmp", noFiles=NO_TEST_FILES, maxSize=MAX_GEN_FILE_SIZE) :
  EXTENSIONS = ["mov", "doc","txt","jpg"]
  MAX_DEPTH = 4

  testString = "A"*100

  debugOutput("generating test data")
  for i in range(0, noFiles) :
    path = os.path.join(prefix,*["folder-%s-%s" % (j, random.randint(0,2)) for j in range(0, random.randint(0,MAX_DEPTH))])
    filename = os.path.join(path, "file-%s.%s" % (random.randint(0,1000), random.choice(EXTENSIONS)))
    size = random.randint(len(testString), maxSize)
    debugOutput("filename: %s %s" % (filename, size))

    if not os.path.exists(filename) :
      
      # Make the folder
      os.system("mkdir -p %s" % os.path.dirname(filename))

      # Write the file.
      testFile = open(filename,"w")
      for i in range(0, size/len(testString)) :
        testFile.write(testString)
      testFile.close()

  return prefix


def getTestSSHAccount() :
  return open(TEST_SSH_ACCOUNT,"r").read().replace("\n","").split(",") 

if __name__ == "__main__" :
  debugOutput("Testing")
  debugOutput(getTestSSHAccount())
