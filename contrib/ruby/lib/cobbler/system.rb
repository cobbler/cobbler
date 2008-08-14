# system.rb 
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
  
  # +System+ represents a system within Cobbler.
  #
  class System < Base
    
    cobbler_lifecycle :find_all => 'get_systems', 
      :find_one => 'get_system', 
      :remove => 'remove_system'
    
    cobbler_field      :name
    cobbler_field      :parent
    cobbler_field      :profile
    cobbler_field      :depth
    cobbler_collection :kernel_options, :packing => :hash
    cobbler_field      :kickstart
    cobbler_collection :ks_meta, :packing => :hash
    cobbler_field      :netboot_enabled
    cobbler_collection :owners
    cobbler_field      :server
    cobbler_collection :interfaces, :type => 'NetworkInterface', :packing => :hash
    cobbler_field      :virt_cpus
    cobbler_field      :virt_file_size
    cobbler_field      :virt_path
    cobbler_field      :virt_ram
    cobbler_field      :virt_type
    cobbler_field      :virt_bridge     

    def initialize(definitions)
      super(definitions)
    end
    
    # Saves this instance.
    #
    def save
      Base.begin_transaction(true)
      
      token = Base.login      
      sysid = Base.make_call('new_system',token)
      
      Base.make_call('modify_system',sysid,'name',self.name,token)
      Base.make_call('modify_system',sysid,'profile',profile,token)
      
      if @interfaces
        count = 0
        @interfaces.each do |interface|
        
          values = interface.bundle_for_saving(count)     
          
          unless values.empty?            
            Base.make_call('modify_system',sysid,'modify-interface',values,token)        
            count = count + 1
          end
        
        end
      end
      
      Base.make_call('save_system',sysid,token)

      Base.end_transaction      
    end
    
    private
    
    # Creates a new instance of +System+ from a result received from Cobbler.
    #
    def self.create(attrs)
      System.new(attrs)
    end
  end
end