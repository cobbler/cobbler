#!/usr/bin/ruby
#
# remove_system.rb - example of using rubygem-cobbler to remove a system.
# 
# Copyright (C) 2008 Red Hat, Inc.
# Written by Darryl L. Pierce <dpierceredhat.com>
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
  ["--hostname",   "-s", GetoptLong::REQUIRED_ARGUMENT ],
  ["--name",   "-d", GetoptLong::REQUIRED_ARGUMENT ],
  ["--username", "-u", GetoptLong::REQUIRED_ARGUMENT ],
  ["--password", "-p", GetoptLong::REQUIRED_ARGUMENT ],
  ["--help",    "-h", GetoptLong::NO_ARGUMENT]
)

hostname = name = username = password = nil

def usage
  puts "Usage: #{$0} --name distro-name [--hostname hostname] [--username username] [--password password]\n"
  exit
end

opts.each do |opt, arg|
  case opt
  when '--hostname' then hostname = arg
  when '--name'     then name   = arg
  when '--username' then username = arg
  when '--password' then password = arg
  when '--help'     then usage
  end
end

if name
  Base.hostname = hostname if hostname
  Base.username = username if username
  Base.password = password if password
  
  puts "Removing the distro named \"#{name}\"..."
    
  begin
    puts "Deleted." if Distro.remove(name)
  rescue Exception => e
    puts "Error: #{e.message}"
  end
else
  usage
end