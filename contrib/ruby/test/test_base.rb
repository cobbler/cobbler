# test_system.rb - Unit tests.
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
  class TestBase < Test::Unit::TestCase
    def setup
      @connection     = flexmock('connection')
      Base.connection = @connection
      Base.hostname   = "localhost"      
      @username       = 'dpierce'
      @password       = 'farkle'
      Base.username   = @username
      Base.password   = @password
    end
    
    # Ensures that the default behavior for the base is to create a connection
    # if one wasn't set.
    #
    def test_connection_without_mock
      Base.connection = nil
      
      assert Base.connect(true), 'Should have created a new connection.'

      Base.connection = nil
      
      assert Base.connect(false), 'Should have created a new connection.'
    end

    # Ensures that setting a mock connection works (for unit tests).
    #
    def test_connect
      assert_same @connection, Base.connect(true),  'Got the wrong connection object.'
      assert_same @connection, Base.connect(false), 'Got the wrong connection object.'
    end
    
    # Ensures that beginning a transaction results in creating a connection.
    #
    def test_begin_transaction
      assert_same @connection, Base.begin_transaction, 'Did not create a connection.'
    end
    
    # Ensures that a login submits the username and password to the Cobbler server.
    #
    def test_login
      @connection.should_receive(:call).with('login',@username, @password).once.returns(true)
      
      Base.login
    end
    
    # Ensures that, if no connection exists, making a call throws an exception.
    #
    def test_make_call_without_connection
      Base.connection = nil
      
      assert_raises(Exception) {Base.make_call('test')}
    end
    
    # Ensures that making a call actually sends the data.
    #
    def test_make_call
      @connection.should_receive(:call).with('test').once.returns('farkle')
      
      result = Base.make_call('test')
      
      assert_equal result, 'farkle', 'Did not get the expected result.'
    end
    
    # Ensures that ending a transaction closes the connection.
    #
    def test_end_transaction
      Base.end_transaction
      
      # we can't just call Base.connect since that will create a new object,
      # so we'll try to send data and, if that raises an exception, we'll 
      # know indirectly that the connection object is gone.
      assert_raises(Exception) {Base.make_call}
    end
  end
end
