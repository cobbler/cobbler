#
# cobbler.rb - Cobbler module declaration.
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
 
require 'cobbler/base'
require 'cobbler/distro'
require 'cobbler/image'
require 'cobbler/network_interface'
require 'cobbler/profile'
require 'cobbler/system'
 
module Cobbler      
  config = (ENV['COBBLER_YML'] || File.expand_path("config/cobbler.yml"))
      
  yml = YAML::load(File.open(config)) if File.exist?(config)
      
  if yml
    Base.hostname = yml['hostname']
    Base.username = yml['username']
    Base.password = yml['password']
  end
    
end
