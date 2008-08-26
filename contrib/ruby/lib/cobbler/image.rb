#
# image.rb 
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
  
  # +Image+ represents an image within Cobbler.
  #
  class Image < Base
    
    cobbler_lifecycle :find_all => 'get_images', 
      :find_one => 'get_image', 
      :remove => 'remove_image'
    
    cobbler_field :name
    cobbler_field :owners
    cobbler_field :depth
    cobbler_field :virt_file_size
    cobbler_field :virt_path
    cobbler_field :xml_file
    cobbler_field :virt_bridge
    cobbler_field :virt_ram
    cobbler_field :file
    cobbler_field :virt_cpus
    cobbler_field :parent

    def initialize(definitions)
      super(definitions)
    end
    
    private
    
    # Creates a new instance of +System+ from a result received from Cobbler.
    #
    def self.create(attrs)
      Image.new(attrs)
    end
  end
end