#
# base.rb
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

require 'xmlrpc/client'
require 'pp'
require 'yaml'

module Cobbler
  include XMLRPC

  # +Base+ represents a remote Cobbler server.
  #
  # Child classes can define fields that will be retrieved from Cobbler by
  # using the +cobbler_field+ method. For example:
  #
  #   class System < Base
  #       cobbler_lifecycle :find_all => 'get_systems'
  #       cobbler_field :name
  #       cobbler_collection :owners, :type => 'String', :packing => :hash
  #   end
  #
  # declares a class named System that contains two fields and a class-level
  # method.
  #
  # The first field, "name", is a simple property. It will be retrieved from
  # the value "name" in the remote definition for a system, identifyed by the
  # +:owner+ argument.
  #
  # The second field, "owners", is similarly retrieved from a property also
  # named "owners" in the remote definition. However, this property is a
  # collection: in this case, it is an array of definitions itself. The
  # +:type+ argument identifies what the +local+ class type is that will be
  # used to represent each element in the collection.
  #
  # A +cobbler_collection+ is packed in one of two ways: either as an array
  # of values or as a hash of keys and associated values. These are defined by
  # the +:packing+ argument with the values +Array+ and +Hash+, respectively.
  #
  # The +cobbler_lifecycle+ method allows for declaring different methods for
  # retrieving remote instances of the class. These methods are:
  #
  # +find_one+ - the remote method to find a single instance,
  # +find_all+ - the remote method to find all instances,
  # +remove+   - the remote method to remote an instance
  #
  class Base

    @@hostname   = nil
    @@connection = nil
    @@auth_token = nil

    attr_accessor :definitions

    def initialize(defs = nil)
      @definitions = defs ? defs : Hash.new
    end

    # Sets the connection. This method is only needed during unit testing.
    #
    def self.connection=(connection)
      @@connection = connection
    end

    # Returns or creates a new connection.
    #
    def self.connect(writable)
      @@connection || XMLRPC::Client.new2("http://#{@@hostname}/cobbler_api#{writable ? '_rw' : ''}")
    end

    # Establishes a connection with the Cobbler system.
    #
    def self.begin_transaction(writable = false)
      @@connection = connect(writable)
    end

    # Sets the username.
    #
    def self.username=(username)
      @@username = username
    end

    # Sets the password.
    #
    def self.password=(password)
      @@password = password
    end

    # Logs into the Cobbler server.
    #
    def self.login
      (@@auth_token || make_call('login', @@username, @@password))
    end

    # Makes a remote call.
    #
    def self.make_call(*args)
      raise Exception.new('No connection established.') unless @@connection

      @@connection.call(*args)
    end

    # Ends a transaction and disconnects.
    #
    def self.end_transaction
      @@connection = nil
      @@auth_token = nil
    end

    def self.hostname=(hostname)
      @@hostname = hostname
    end

    class << self
      # Creates a complete finder method
      #
      def cobbler_lifecycle(*args)
        methods = args.first
        methods.keys.each do |key|

          method = methods[key]

          case key
          when :find_all then
            module_eval <<-"end;"
              def self.find(&block)
                begin
                  begin_transaction
                  records = make_call('#{method}')
                ensure
                  end_transaction
                end

                result = Array.new

                if records
                  records.each { |record| result << create(record) }
                end

                result.each { |system| yield(system) } if block

                return result
              end
            end;

          when :find_one then
            module_eval <<-"end;"
              def self.find_one(name, flatten = false)
                begin
                  begin_transaction
                  record = make_call('#{method}',name,flatten)
                ensure
                  end_transaction
                end

                return create(record) unless record.keys.empty?

                return nil
              end
            end;

          when :remove then
            module_eval <<-"end;"
              def self.remove(name)
                begin
                  begin_transaction(true)
                  token = login
                  result = make_call('#{method}',name,token)
                ensure
                  end_transaction
                end

                result
              end
            end;

          end
        end
      end

      # Allows for dynamically declaring fields that will come from
      # Cobbler.
      #
      def cobbler_field(field,*args) # :nodoc:
        if args
          for arg in args
            for key in arg.keys
              case key
              when :findable then

                module_eval <<-"end;"
                  def self.find_by_#{field.to_s}(value,&block)
                    properties = make_call('#{arg[key]}',value)

                    return create(properties) if properties && !properties.empty?

                    return nil
                  end
                end;

              end
            end
          end
        end
        
        module_eval("def #{field}() @definitions['#{field.to_s}']; end")
        module_eval("def #{field}=(val) @definitions['#{field.to_s}'] = val; end")
      end

      # Allows a field to be defined as a collection of objects. The type for that
      # other class must be provided.
      #
      def cobbler_collection(field, *args) # :nodoc:
        classname = 'String'
        packing   = 'Array'

        # process collection definition
        args.each do |arg|
          classname = arg[:type]    if arg[:type]
          if arg[:packing]
            case arg[:packing]
            when :hash  then packing = 'Hash'
            when :array then packing = 'Array'
            end
          end
        end

        module_eval <<-"end;"
          def #{field.to_s}(&block)

            unless @#{field.to_s}
              @#{field.to_s} = #{packing}.new

              values = @definitions['#{field.to_s}']

              case "#{packing}"
                when "Array" then
                  values.each do |value|
                    @#{field.to_s} << #{classname}.new(value)
                  end

                when "Hash" then
                  values.keys.each do |key|
                    @#{field.to_s}[key] = #{classname}.new(values[key])
                  end
              end
            end

            @#{field.to_s}

          end

          def #{field.to_s}=(replacement)
            @#{field.to_s} = replacement
          end
        end;

      end
    end
  end
end
