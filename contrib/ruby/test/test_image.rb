# test_image.rb - Tests the Image class.
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
