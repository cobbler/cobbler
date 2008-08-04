# base.rb
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
  #   class Farkle < Base
  #       cobbler_field :name, findable => 'get_farkle'
  #       cobbler_field :owner
  #   end
  #   
  # declares a class named Farkle that contains two fields. The first, "name",
  # will be one that is searchable on Cobbler; i.e., a method named "find_by_name"
  # will be generated and will use the "get_farkle" remote method to retrieve
  # that instance from Cobbler. 
  # 
  # The second field, "owner", will simply be a field named Farkle.owner that 
  # returns a character string.
  #
  # +Base+ provides some common functionality for all child classes:
  #
  #  
  class Base
    
    @@hostname   = nil    
    @@connection = nil
    
    @defintions = nil
    
    def initialize(definitions)
      @definitions = definitions
    end
    
    # Sets the connection. This method is only needed during unit testing.
    #
    def self.connection=(mock)
      @@connection = mock
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
      make_call('login', @@username, @@password)
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
    end
    
    def definition(key)
      @definitions ? @definitions[key] : nil
    end
    
    def store_definition(key,value)
      @definitions[key] = value
    end
    
    def definitions
      @definitions
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
        
        defined = false
        
        if args
          for arg in args
            for key in arg.keys
              case key 
              when :findable then      
              
                module_eval <<-"end;"
                  def self.find_by_#{field.to_s}(name,&block)
                    properties = make_call('#{arg[key]}',name)

                    return create(properties) if properties && !properties.empty?

                    return nil
                  end
                end;
                
              end              
            end
          end
        end        

        module_eval <<-"end;"
            def #{field.to_s}(&block)
              return definition('#{field.to_s}')
            end

            def #{field.to_s}=(value)
              store_definition('#{field.to_s}',value)
            end
        end;
      end
      
      # Allows a field to be defined as a collection of objects. The type for that
      # other class must be provided.
      #
      def cobbler_collection(field, *args) # :nodoc:
        classname = args[0][:type]
        
        module_eval <<-"end;"
          def #{field.to_s}(&block)
            unless @#{field.to_s}
              @#{field.to_s} = Array.new

              definition('#{field.to_s}').values.each do |value|
                @#{field.to_s} << #{classname}.new(value)
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
