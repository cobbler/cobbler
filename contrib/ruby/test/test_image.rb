#
#  test_image.rb - Tests the Image class.
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
 
$:.unshift File.join(File.dirname(__FILE__),'..','lib')

require 'test/unit'
require 'flexmock/test_unit'
require 'cobbler'

module Cobbler
  class TestImage < Test::Unit::TestCase
    def setup
      @connection = flexmock('connection')
      Image.connection = @connection
      Image.hostname   = "localhost"
      
      @username        = 'dpierce'
      @password        = 'farkle'
      Image.username = @username
      Image.password = @password

      @images = Array.new
      @images << {
        'name'            => 'Fedora-9-LiveCD-KDE',
        'owners'          => 'admin',
        'depth'           => '2',
        'virt_file_size'  => '<<inherit>>',
        'virt_path'       => '<<inherit>>',
        'virt_bridge'     => '<<inherit>>',
        'virt_ram'        => '<<inherit>>',
        'virt_auto_boot'  => '<<inherit>>',
        'virt_cpus'       => '<<inherit>>',
        'file'            => '/var/ftp/pub/Fedora-9-i686-Live-KDE.iso',
        'parent'          => nil,
      }

      @images << {
        'name'            => 'Fedora-9-LiveCD-GNOME',
        'owners'          => 'admin',
        'depth'           => '2',
        'virt_file_size'  => '<<inherit>>',
        'virt_path'       => '<<inherit>>',
        'virt_bridge'     => '<<inherit>>',
        'virt_ram'        => '<<inherit>>',
        'virt_auto_boot'  => '<<inherit>>',
        'virt_cpus'       => '<<inherit>>',
        'file'            => '/var/ftp/pub/Fedora-9-i686-Live.iso',
        'parent'          => nil,
      }

    end

    # Ensures that an attempt to find all profiles works as expected.
    #
    def test_find
      @connection.should_receive(:call).with('get_images').once.returns(@images)

      result = Image.find

      assert result, 'Expected a result set.'
      assert_equal 2, result.size, 'Did not receive the right number of results'
    end
  end
end
