# distro.rb 
# 
# Copyright (C) 2008 Red Hat, Inc.
# Written by Darryl L. Pierce <dpierce@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.  A copy of the GNU General Public License is
# also available at http://www.gnu.org/copyleft/gpl.html.

module Cobbler
  # +NetworkInterface+ represents a single network interface card on a system.
  #
  class NetworkInterface < Base
    cobbler_field :dhcp_tag
    cobbler_field :mac_address
    cobbler_field :subnet
    cobbler_field :gateway
    cobbler_field :hostname
    cobbler_field :virt_bridge
    cobbler_field :ip_address
    
    def initialize(definitions)
      @definitions = definitions
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
      result["subnet-intf#{which}"]     = subnet      if subnet
      result["gateway-intf#{which}"]    = gateway     if gateway
      
      return result
    end
  end
end
