#!/usr/bin/ruby -w 
#
# create_system.rb - example of using rubygem-cobbler to create a system.
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
 
base = File.expand_path(File.join(File.dirname(__FILE__), ".."))
$LOAD_PATH << File.join(base, "lib")
$LOAD_PATH << File.join(base, "examples")

require 'getoptlong'

require 'cobbler'

include Cobbler

opts = GetoptLong.new(
  ['--hostname', '-s', GetoptLong::REQUIRED_ARGUMENT ],
  ['--name',     '-n', GetoptLong::REQUIRED_ARGUMENT ],
  ['--profile',  '-f', GetoptLong::REQUIRED_ARGUMENT ],
  ['--username', '-u', GetoptLong::REQUIRED_ARGUMENT ],
  ['--password', '-p', GetoptLong::REQUIRED_ARGUMENT ],
  ['--help',     '-h', GetoptLong::NO_ARGUMENT]
)

name = profile = hostname = username = password = nil

def usage
  puts "Usage: #{$0} --name system-name --profile profile-name [--hostname hostname] [--username username] [--password password]\n"
  exit
end
  
opts.each do |opt, arg|
  case opt
  when '--hostname' then hostname = arg
  when '--name'     then name     = arg
  when '--profile'  then profile  = arg
  when '--username' then username = arg
  when '--password' then password = arg
  when '--help'     then usage
  end
end

if name && profile 
  
  System.hostname = hostname if hostname
  System.username = username if username
  System.password = password if password
  
  system = System.new('name' => name,'profile' => profile)
  
  system.interfaces=[NetworkInterface.new({'mac_address' => '00:11:22:33:44:55:66:77'})]

  puts "Saving a new system with name #{system.name} based on the profile #{system.profile}."

  begin
    system.save
    puts "Successfully saved the new system."
  rescue Exception => error
    puts "Unable to create system: #{error.message}"
  end
else
  usage
end