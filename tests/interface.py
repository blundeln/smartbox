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
# selenium (selenium.py)
# ----------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

from selenium import selenium
import unittest

class TestGoogle(unittest.TestCase):
  def setUp(self):
    self.selenium = selenium("localhost", 4444, "*firefox", "http://www.google.com/webhp")
    self.selenium.start()
    
  def test_google(self):
    sel = self.selenium
    sel.open("http://www.google.com/webhp")
    sel.type("q", "hello world")
    sel.click("btnG")
    sel.wait_for_page_to_load(5000)
    self.assertEqual("hello world - Google Search", sel.get_title())
  
  def tearDown(self):
    self.selenium.stop()

if __name__ == "__main__":
  unittest.main()
