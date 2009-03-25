#
#  test_system.rb - Tests the System class.
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
require 'flexmock/argument_matchers'
require 'cobbler'

module Cobbler
  class TestSystem < Test::Unit::TestCase
    def setup
      @connection = flexmock('connection')
      Profile.connection = @connection
      Profile.hostname   = "localhost"

      @username        = 'dpierce'
      @password        = 'farkle'
      Profile.username = @username
      Profile.password = @password

      @auth_token     = 'OICU812B4'
      @system_id      = 717
      @system_name    = 'system1'
      @profile_name   = 'profile1'
      @image_name     = 'image1'
      @nics           = Array.new
      @nic_details    = {'mac_address' => '00:11:22:33:44:55:66:77'}
      @nic            = NetworkInterface.new(@nic_details)
      @nics << @nic

      @systems = Array.new
      @systems << {
        'name'            => 'Web-Server',
        'owners'          => ['admin','dpierce','mpdehaan'],
        'profile'         => 'Fedora-9-i386',
        'depth'           => '2',
        'virt_file_size'  => '<<inherit>>',
        'virt_path'       => '<<inherit>>',
        'virt_type'       => '<<inherit>>',
        'server'          => '<<inherit>>',
        'interfaces'      => {
          'intf0' => {
            'mac_address' => '00:11:22:33:44:55'},
          'intf1' => {
            'mac_address' => '00:11:22:33:44:55'}
        },
        'virt_bridge'     => '<<inherit>>',
        'virt_ram'        => '<<inherit>>',
        'virt_auto_boot'  => '<<inherit>>',
        'ks_meta'         => nil,
        'netboot_enabled' => 'True',
        'kernel_options'  => nil,
        'virt_cpus'       => '<<inherit>>',
        'parent'          => nil,
        'kickstart'       => '<<inherit>>',
      }

      @systems << {
        'name'            => 'DNS-Server',
        'owners'          => 'admin',
        'profile'         => 'Fedora-9-x86_64',
        'depth'           => '2',
        'virt_file_size'  => '<<inherit>>',
        'virt_path'       => '<<inherit>>',
        'virt_type'       => '<<inherit>>',
        'server'          => '<<inherit>>',
        'interfaces'      => {
          'intf0' => {
            'mac_address' => 'AA:BB:CC:DD:EE:FF'}},
        'virt_bridge'     => '<<inherit>>',
        'virt_ram'        => '<<inherit>>',
        'virt_auto_boot'  => '<<inherit>>',
        'ks_meta'         => nil,
        'netboot_enabled' => 'True',
        'kernel_options'  => nil,
        'virt_cpus'       => '<<inherit>>',
        'parent'          => nil,
        'kickstart'       => '<<inherit>>',
      }

    end

    # Ensures that an attempt to find all profiles works as expected.
    #
    def test_find
      @connection.should_receive(:call).with('get_systems').once.returns(@systems)

      result = System.find

      assert result, 'Expected a result set.'
      assert_equal 2, result.size, 'Did not receive the right number of results.'
      assert_equal 2, result[0].interfaces.size, 'Did not parse the NICs correctly.'
      result[0].interfaces.keys.each { |intf| assert_equal "00:11:22:33:44:55", result[0].interfaces[intf].mac_address }
      assert_equal 3, result[0].owners.size, 'Did not parse the owners correctly.'
    end

    # Ensures that saving stops when an update fails.
    #
    def test_save_and_update_fails
      @connection.should_receive(:call).with('login',@username,@password).once.returns(@auth_token)
      @connection.should_receive(:call).with('version').once.returns("1.5")
      @connection.should_receive(:call).with('update').once.returns{ false }

      system = System.new('name' => @system_name, 'profile' => @profile_name)

      assert_raise(Exception) {system.save}
    end

    # Ensures that saving a system based on a profile works as expected.
    #
    def test_save_with_profile
      @connection.should_receive(:call).with('login',@username,@password).once.returns(@auth_token)
      @connection.should_receive(:call).with('version').once.returns("1.5")
      @connection.should_receive(:call).with('update').once.returns { true }
      @connection.should_receive(:call).with('new_system',@auth_token).once.returns(@system_id)
      @connection.should_receive(:call).with('modify_system',@system_id,'name',@system_name,@auth_token).once.returns(true)
      @connection.should_receive(:call).with('modify_system',@system_id,'profile',@profile_name,@auth_token).once.returns(true)
      @connection.should_receive(:call).with('save_system',@system_id,@auth_token).once.returns(true)

      system = System.new('name' => @system_name, 'profile' => @profile_name)

      system.save
    end

    # Ensures that saving a system based on an image works as expected.
    #
    def test_save_with_image
      @connection.should_receive(:call).with('login',@username,@password).once.returns(@auth_token)
      @connection.should_receive(:call).with('update').once.returns { true }
      @connection.should_receive(:call).with('new_system',@auth_token).once.returns(@system_id)
      @connection.should_receive(:call).with('modify_system',@system_id,'name',@system_name,@auth_token).once.returns(true)
      @connection.should_receive(:call).with('modify_system',@system_id,'image',@image_name,@auth_token).once.returns(true)
      @connection.should_receive(:call).with('save_system',@system_id,@auth_token).once.returns(true)

      system = System.new('name' => @system_name, 'image' => @image_name)

      system.save
    end

    # Ensures that saving a system works as expected even when network interfaces
    # are involved.
    #
    def test_save_with_new_nics
      @connection.should_receive(:call).with('login',@username,@password).once.returns(@auth_token)
      @connection.should_receive(:call).with('version').once.returns("1.5")
      @connection.should_receive(:call).with('update').once.returns { true }
      @connection.should_receive(:call).with('new_system',@auth_token).once.returns(@system_id)
      @connection.should_receive(:call).with('modify_system',@system_id,'name',@system_name,@auth_token).once.returns(true)
      @connection.should_receive(:call).with('modify_system',@system_id,'profile',@profile_name,@auth_token).once.returns(true)
      @connection.should_receive(:call).with("modify_system",@system_id,'modify-interface',
        @nic.bundle_for_saving(0),@auth_token).once.returns(true)
      @connection.should_receive(:call).with('save_system',@system_id,@auth_token).once.returns(true)

      system = System.new('name' => @system_name, 'profile' => @profile_name)
      system.interfaces = @nics

      system.save
    end

    # Ensures that removing a system works as expected.
    #
    def test_remove_system
      @connection.should_receive(:call).with('login',@username,@password).once.returns(@auth_token)
      @connection.should_receive(:call).with('version').once.returns("1.5")
      @connection.should_receive(:call).with('remove_system',@system_name,@auth_token).once.returns(true)

      system = System.new('name' => @system_name, 'profile' => @profile_name)

      system.remove
    end
  end
end
