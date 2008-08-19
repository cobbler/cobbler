# profile.rb 
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

# +Profile+ represents a single profile.
#
module Cobbler
  
  # +Profile+ represents a single profile within Cobbler.
  #
  class Profile < Base
    cobbler_lifecycle :find_all => 'get_profiles',
      :find_one => 'get_profile',
      :remove => 'remove_profile'
    
    cobbler_field :name, :findable => 'get_profile'
    cobbler_field :parent
    cobbler_collection :owners, :packing => :array
    cobbler_field :dhcp_tag
    cobbler_field :depth
    cobbler_field :virt_file_size
    cobbler_field :virt_path
    cobbler_field :virt_type
    cobbler_field :repos
    cobbler_field :distro
    cobbler_field :server
    cobbler_field :virt_bridge
    cobbler_field :virt_ram
    cobbler_field :kernel_options
    cobbler_field :virt_cpus
    cobbler_field :ks_meta
    cobbler_field :kickstart
    
    def initialize(definitions)
      super(definitions)
    end
    
    private
    
    # Creates a new instance of +Profile+ from a result received from Cobbler.
    #
    def self.create(attrs)
      Profile.new(attrs)
    end
  end
end
