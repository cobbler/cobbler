#!/usr/bin/ruby -w 
#
# create_system.rb - example of using rubygem-cobbler to create a system.
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
 
base = File.expand_path(File.join(File.dirname(__FILE__), ".."))
$LOAD_PATH << File.join(base, "lib")
$LOAD_PATH << File.join(base, "examples")

require 'getoptlong'

require 'cobbler'

include Cobbler

opts = GetoptLong.new(
  ["--server",   "-s", GetoptLong::REQUIRED_ARGUMENT ],
  ["--name",     "-n", GetoptLong::REQUIRED_ARGUMENT ],
  ["--profile",  "-f", GetoptLong::REQUIRED_ARGUMENT ],
  ["--system",   "-y", GetoptLong::REQUIRED_ARGUMENT ],
  ["--username", "-u", GetoptLong::REQUIRED_ARGUMENT ],
  ["--password", "-p", GetoptLong::REQUIRED_ARGUMENT ],
  ["--help",     "-h", GetoptLong::NO_ARGUMENT]
)

hostname = name = profile = system = username = password = nil

opts.each do |opt, arg|
  case opt
  when '--server'   then hostname = arg
  when '--name'     then name     = arg
  when '--system'   then system   = arg
  when '--profile'  then profile  = arg
  when '--username' then username = arg
  when '--password' then password = arg
  when '--help'     then usage
  end
end

def usage
  puts "Usage: #{$0} [--server hostname] --name system-name --system system-name [--username username] [--password password]\n"
end
  
if name && profile 
  
  system = System.new('name' => name,'profile' => profile)
  
  system.interfaces=[ NetworkInterface.new('mac_address' => '00:11:22:33:44:55:66:77') ]

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