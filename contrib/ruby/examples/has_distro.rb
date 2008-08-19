#!/usr/bin/ruby
#
# has_distro.rb - example of using rubygem-cobbler to check if a distro exists.
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
  ['--hostname', '-s', GetoptLong::REQUIRED_ARGUMENT ],
  ['--name',     '-n', GetoptLong::REQUIRED_ARGUMENT ],
  ['--help',     '-h', GetoptLong::NO_ARGUMENT]
)

name = hostname = nil

def usage
  puts "Usage: #{$0} --name distro-name [--hostname hostname]"
  exit
end

opts.each do |opt, arg|
  case opt
  when '--hostname' then hostname = arg
  when '--name'     then name     = arg
  when '--help'     then usage
  end
end

if name
  Distro.hostname = hostname
  
  puts "Finding the distro named \"#{name}\""
    
  result = Distro.find_one(name)
  
  if result
    puts "#{result.name} exists, and is a breed of #{result.breed}."
  else
    puts "No such distro"
  end
else 
  usage
end