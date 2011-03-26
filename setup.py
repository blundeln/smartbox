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
# setup (setup.py)
# ----------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#
import ez_setup 
ez_setup.use_setuptools()
from setuptools import setup, find_packages

MAIN_PACKAGE = "smartbox"
exec("import %s" % MAIN_PACKAGE)
VERSION = eval("%s.VERSION" % MAIN_PACKAGE)

setup(
  name = MAIN_PACKAGE,
  version = VERSION,
  packages = find_packages(),
  scripts=["scripts/smartbox"],
  install_requires=["pythondialog","nbdebug"],
  dependency_links=["http://www.nickblundell.org.uk/packages/"],
  include_package_data=True,
  #data_files=[
  #  ('/etc/cron.d',['smartbox/resources/smartbox-cron']),
  #],
)
