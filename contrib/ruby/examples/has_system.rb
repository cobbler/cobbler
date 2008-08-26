#!/usr/bin/ruby
#
# has_system.rb - example of using rubygem-cobbler to check if a system exists.
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
  ['--hostname',  '-s', GetoptLong::REQUIRED_ARGUMENT ],
  ['--name',  '-t', GetoptLong::REQUIRED_ARGUMENT ],
  ['--help',    '-h', GetoptLong::NO_ARGUMENT]
)

hostname = name = nil

def usage
  puts "Usage: #{$0} --name system-name [--hostname hostname]\n"
  exit
end

opts.each do |opt, arg|
  case opt
  when '--hostname' then hostname = arg
  when '--name'     then name  = arg
  when '--help'     then usage
  end
end

if name

  Base.hostname = hostname if hostname
  
  puts "Finding the system named \"#{name}\""
    
  result = System.find_one(name)
  
  if result
    puts "#{result.name} exists, and is owned by #{result.owners}."
  else
    puts "No such system."
  end
else
  usage
end