#
# image.rb
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

module Cobbler

  # +Image+ represents an image within Cobbler.
  #
  class Image < Base

    cobbler_lifecycle :find_all => 'get_images',
      :find_one => 'get_image',
      :remove => 'remove_image'

    ATTRIBUTES = [:name, :owners, :depth, :virt_file_size,
      :virt_path, :xml_file, :virt_bridge, :file, :parent]
    # These attributes seem to not exist yet. :virt_ram, :virt_cpus,

    ATTRIBUTES.each do |attr|
      puts "Creating field with #{attr}"
      cobbler_field attr
    end

    def initialize(definitions = nil)
      super(definitions)
    end

    # Saves this instance.
    #
    def save
      Base.begin_transaction(true)

      token = Base.login

      raise Exception.new('Update failed prior to saving') unless Base.make_call('update')

      imgid = Base.make_call('new_image',token)

      ATTRIBUTES.each do |attr|
        Base.make_call('modify_image',imgid,attr.to_s, self.send(attr),token) if self.send(attr) !=  nil
      end

      Base.make_call('save_image',imgid,token)

      Base.end_transaction
    end

    private

    # Creates a new instance of +Image+ from a result received from Cobbler.
    #
    def self.create(attrs)
      Image.new(attrs)
    end
  end
end