#
#  distro.rb 
# 
# Copyright (C) 2008 Red Hat, Inc.
# Written by Darryl L. Pierce <dpierce@redhat.com>
#
# This file is part of rubygem-cobbler.
#
# rubygem-cobbleris free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published 
# by the Free Software Foundation, either version 2.1 of the License, or
# (at your option) any later version.
#
# rubygem-cobbler is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with rubygem-cobbler.  If not, see <http://www.gnu.org/licenses/>.
#
 
module Cobbler
  # +NetworkInterface+ represents a single network interface card on a system.
  #
  class NetworkInterface < Base
    cobbler_field :dhcp_tag
    cobbler_field :mac_address
    cobbler_field :netmask
    cobbler_field :gateway
    cobbler_field :hostname
    cobbler_field :virt_bridge
    cobbler_field :ip_address
    
    def initialize(args = nil)
      @definitions = args
    end
   
    # A hack for getting the NIC's details over the wire.
    #
    def bundle_for_saving(which)
      result = Hash.new
      
      result["macaddress-intf#{which}"] = mac_address if mac_address
      result["ipaddress-intf#{which}"]  = ip_address  if ip_address
      result["hostname-intf#{which}"]   = hostname    if hostname
      result["virtbridge-intf#{which}"] = virt_bridge if virt_bridge
      result["dhcptag-intf#{which}"]    = dhcp_tag    if dhcp_tag
      result["netmask-intf#{which}"]    = netmask     if netmask
      result["gateway-intf#{which}"]    = gateway     if gateway
      
      return result
    end
  end
end
