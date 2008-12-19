#!/usr/bin/ruby 
#
# list_systems.rb - example of using rubygem-cobbler to list system.
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
  ['--details',  '-d', GetoptLong::NO_ARGUMENT ],
  ['--help',     '-h', GetoptLong::NO_ARGUMENT ]
)

hostname = nil
details  = false

def usage
  puts "Usage: #{$0} [--hostname hostname] [--details]\n"
  exit
end

opts.each do |opt, arg|
  case opt
  when '--hostname' then hostname = arg
  when '--details'  then details  = true
  when '--help'     then usage
  end
end

Base.hostname = hostname if hostname
  
puts "Results:"
System.find do |system| 
  puts "\"#{system.name}\" is based on \"#{system.profile}\"."
  
  if details
    puts "\tOwner: #{system.owners}"
    system.interfaces.each_pair { |id,nic| puts "\tNIC[#{id}]: #{nic.mac_address}"} 
  end  
end

