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
# network (network.py)
# --------------------
#
# Description:
#
#
# Author       : Nick Blundell
# Organisation : www.nickblundell.org.uk
# Version Info : $Id$
#

import os
import re

import socket
import smartbox.core
import smartbox.system

from nbdebug import *

INTERFACES_FILE = "/etc/network/interfaces"
HOSTNAME_FILE = "/etc/hostname"

USELESS_INTERFACES = ["lo"]
DHCP = "DHCP"
STATIC = "STATIC"
configurations = [DHCP, STATIC]

RE_IFCONFIG = r"""^(?P<interface>\S*)\s+Link encap.*?inet addr:(?P<address>\S+).*?Mask:(?P<netmask>\S+)"""
RE_NETSTAT_NR = r"""^0\.0\.0\.0\s+(?P<gateway>\S+)"""

def getNetworkDetails() :
  debugOutput("Getting network details")

  liveInterfaces = _getLiveInterfaces()
  mainInterface = _getMainInterface(liveInterfaces)
  mode = "iface %s inet dhcp" % mainInterface in _getInterfaceConfig(mainInterface) and DHCP or STATIC
  gateway = _getGateway()

  return {"configuration":mode, "address":liveInterfaces[mainInterface][0], "netmask":liveInterfaces[mainInterface][1], "gateway":gateway}

def setNetworkDetails(configuration, address=None, netmask=None, gateway=None) :
  debugOutput("Setting network details (%s, %s, %s)" % (configuration, address, netmask))
  mainInterface = _getMainInterface(_getLiveInterfaces())
  interfaceConfig = _getInterfaceConfig(mainInterface)
  if configuration == STATIC and address and netmask :
    newConfig = """iface %s inet static\n\taddress %s\n\tgateway %s\n\tnetmask %s""" % (mainInterface, address, gateway, netmask)
  else : 
    newConfig = "iface %s inet dhcp" % mainInterface

  if interfaceConfig != newConfig :
    interfacesConfig = smartbox.system.readFromFile(INTERFACES_FILE)
    interfacesConfig = interfacesConfig.replace(interfaceConfig, newConfig)
    smartbox.system.writeToFile(INTERFACES_FILE, interfacesConfig)
    # TODO: Sort out DNS, etc for static mode
    smartbox.core.restart()
  
def restart() :
  smartbox.system.run("/etc/init.d/networking restart")

def getHostname() :
  return socket.gethostname()

def setHostname(newHostname) :
  oldHostname = getHostname()
  if newHostname != oldHostname :
    smartbox.system.run("hostname '%s'" % newHostname)
    smartbox.system.writeToFile(HOSTNAME_FILE, newHostname)
    smartbox.core.restart()


def _getMainInterface(interfaces) :
  for interface in interfaces :
    if interface not in USELESS_INTERFACES :
      return interface

def _getInterfaceConfig(interface) :
  config = smartbox.system.readFromFile(INTERFACES_FILE)
  debugOutput(config)
  match = re.search("""(iface %s\s.*dhcp$)|(iface %s\s+.*?netmask \S+$)""" % (interface, interface), config, re.MULTILINE | re.DOTALL)
  if match :
    debugOutput(match.groups())
    for group in match.groups() :
      if group: return group
  return None
  

def _getLiveInterfaces() :

  ifconfig = os.popen4("ifconfig")[1].read()

  interfaces = {}
  for match in re.finditer(RE_IFCONFIG, ifconfig, re.MULTILINE | re.DOTALL) :
    debugOutput("match: %s" % match.groupdict())
    interface = match.groupdict()["interface"]
    interfaces[interface] = [match.groupdict()["address"], match.groupdict()["netmask"]]

  debugOutput(interfaces)
  return interfaces

def _getGateway() :

  gwConfig = os.popen4("netstat -nr")[1].read()
  match = re.search(RE_NETSTAT_NR, gwConfig, re.MULTILINE)
  if match :
    return match.groupdict()["gateway"]
  else :
    return None
