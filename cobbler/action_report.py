"""
Report from a cobbler master.

Copyright 2007-2008, Red Hat, Inc
Anderson Silva <ansilva@redhat.com>


This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import os
import os.path
import xmlrpclib
import api as cobbler_api
from cexceptions import *
from utils import _


class Report:

    def __init__(self, config):
        """
        Constructor
        """
        self.config = config
        self.settings = config.settings()
        self.api = config.api
        self.report_type = None
        self.report_what = None
        self.report_name = None
        self.report_fields = None
        self.report_noheaders = None

    def reporting_csv(self, info, order, noheaders):
        """
        Formats data on 'info' for csv output
        """
        outputheaders = ''
        outputbody = ''
        sep = ','

        info_count = 0
        for item in info:

            item_count = 0
            for key in order:

                if info_count == 0:
                    outputheaders += str(key) + sep

                outputbody += str(item[key]) + sep

                item_count = item_count + 1

            info_count = info_count + 1
            outputbody += '\n'

        outputheaders += '\n'

        if noheaders:
            outputheaders = '';

        return outputheaders + outputbody
 
    def reporting_trac(self, info, order, noheaders):
        """
        Formats data on 'info' for trac wiki table output
        """        
        outputheaders = ''
        outputbody = ''
        sep = '||'

        info_count = 0
        for item in info:
            
            item_count = 0
            for key in order:


                if info_count == 0:
                    outputheaders += sep + str(key)

                outputbody += sep + str(item[key])

                item_count = item_count + 1

            info_count = info_count + 1
            outputbody += '||\n'

        outputheaders += '||\n'
        
        if noheaders:
            outputheaders = '';
        
        return outputheaders + outputbody

    def reporting_doku(self, info, order, noheaders):
        """
        Formats data on 'info' for doku wiki table output
        """      
        outputheaders = ''
        outputbody = ''
        sep1 = '^'
        sep2 = '|'


        info_count = 0
        for item in info:
            
            item_count = 0
            for key in order:

                if info_count == 0:
                    outputheaders += sep1 + key

                outputbody += sep2 + item[key]

                item_count = item_count + 1

            info_count = info_count + 1
            outputbody += sep2 + '\n'

        outputheaders += sep1 + '\n'
        
        if noheaders:
            outputheaders = '';
        
        return outputheaders + outputbody

    def reporting_mediawiki(self, info, order, noheaders):
        """
        Formats data on 'info' for mediawiki table output
        """
        outputheaders = ''
        outputbody = ''
        opentable = '{| border="1"\n'
        closetable = '|}\n'
        sep1 = '||'
        sep2 = '|'
        sep3 = '|-'


        info_count = 0
        for item in info:
            
            item_count = 0
            for key in order:

                if info_count == 0 and item_count == 0:
                    outputheaders += sep2 + key
                elif info_count == 0:
                    outputheaders += sep1 + key

                if item_count == 0:
                    outputbody += sep2 + str(item[key])
                else:
                    outputbody += sep1 + str(item[key])

                item_count = item_count + 1

            info_count = info_count + 1
            outputbody += '\n' + sep3 + '\n'

        outputheaders += '\n' + sep3 + '\n'

        if noheaders:
            outputheaders = '';

        return opentable + outputheaders + outputbody + closetable
    
    def print_formatted_data(self, data, order, report_type, noheaders):
        """
        Used for picking the correct format to output data as
        """
        if report_type == "csv":
            print self.reporting_csv(data, order, noheaders)
        if report_type == "mediawiki":
            print self.reporting_mediawiki(data, order, noheaders)
        if report_type == "trac":
            print self.reporting_trac(data, order, noheaders)
        if report_type == "doku":
            print self.reporting_doku(data, order, noheaders)

        return True

    def reporting_sorter(self, a, b):
        """
        Used for sorting cobbler objects for report commands
        """
        return cmp(a.name, b.name)

    def reporting_print_sorted(self, collection):
        """
        Prints all objects in a collection sorted by name
        """
        collection = [x for x in collection]
        collection.sort(self.reporting_sorter)
        for x in collection:
            print x.printable()
        return True

    def reporting_list_names2(self, collection, name):
        """
        Prints a specific object in a collection.
        """
        obj = collection.find(name=name)
        if obj is not None:
            print obj.printable()
        return True
    
    def reporting_print_all_fields(self, collection, report_type, report_noheaders):
        """
        Prints all fields in a collection as a table given the report type
        """
        collection = [x for x in collection]
        collection.sort(self.reporting_sorter)
        data = []
        out_order = []
        count = 0
        for x in collection:
            item = {}
            structure = x.to_datastruct()
           
            for (key, value) in structure.iteritems():

                # exception for systems which could have > 1 interface
                if key == "interfaces":
                    for (device, info) in value.iteritems():
                        for (info_header, info_value) in info.iteritems():
                            item[info_header] = str(device) + ': ' + str(info_value)
                            # needs to create order list for print_formatted_fields
                            if count == 0:
                                out_order.append(info_header)
                else: 
                    item[key] = value
                    # needs to create order list for print_formatted_fields
                    if count == 0:
                        out_order.append(key)                  

            count = count + 1
  
            data.append(item) 

        self.print_formatted_data(data = data, order = out_order, report_type = report_type, noheaders = report_noheaders)
        
        return True
    
    def reporting_print_x_fields(self, collection, report_type, report_fields, report_noheaders):
        """
        Prints specific fields in a collection as a table given the report type
        """
        collection = [x for x in collection]
        collection.sort(self.reporting_sorter)
        data = []
        fields_list = report_fields.replace(' ', '').split(',')
        
        for x in collection:
            structure = x.to_datastruct()
            item = {}
            for field in fields_list:

                if field in structure.keys():
                    item[field] = structure[field]
 
                # exception for systems which could have > 1 interface
                elif "interfaces" in structure.keys():
                    for device in structure['interfaces'].keys():
                        if field in structure['interfaces'][device]:
                            item[field] = device + ': ' + structure['interfaces'][device][field]                    
                else: 
                    raise CX(_("The field %s does not exist, see cobbler dumpvars for available fields.") % field)

            data.append(item)
         
        self.print_formatted_data(data = data, order = fields_list, report_type = report_type, noheaders = report_noheaders)
                        
        return True
        
    # -------------------------------------------------------

    def run(self, report_what = None, report_name = None, report_type = None, report_fields = None, report_noheaders = None):
        """
        Get remote profiles and distros and sync them locally
        """
               
        """
        1. Handles original report output
        2. Handles all fields of report outputs as table given a format
        3. Handles specific fields of report outputs as table given a format
        """        
        

        if report_type == 'text' and report_fields == 'all':

            if report_what in [ "all", "distros", "distro" ]:
                if report_name:
                    self.reporting_list_names2(self.api.distros(), report_name)
                else:
                    self.reporting_print_sorted(self.api.distros())

            if report_what in [ "all", "profiles", "profile" ]:
                if report_name:
                    self.reporting_list_names2(self.api.profiles(), report_name)
                else:
                    self.reporting_print_sorted(self.api.profiles())

            if report_what in [ "all", "systems", "system" ]:
                if report_name:
                    self.reporting_list_names2(self.api.systems(), report_name)
                else:
                    self.reporting_print_sorted(self.api.systems())

            if report_what in [ "all", "repos", "repo" ]:
                if report_name is not None:
                    self.reporting_list_names2(self.api.repos(), report_name)
                else:
                    self.reporting_print_sorted(self.api.repos())
                   
        elif report_type == 'text' and report_fields != 'all':
            raise CX(_("The 'text' type can only be used with field set to 'all'"))
 
        elif report_type != 'text' and report_fields == 'all':
            
            if report_what in [ "all", "distros", "distro" ]:
                self.reporting_print_all_fields(self.api.distros(), report_type, report_noheaders)

            if report_what in [ "all", "profiles", "profile" ]:
                self.reporting_print_all_fields(self.api.profiles(), report_type, report_noheaders)

            if report_what in [ "all", "systems", "system" ]:
                self.reporting_print_all_fields(self.api.systems(), report_type, report_noheaders)

            if report_what in [ "all", "repos", "repo" ]:
                self.reporting_print_all_fields(self.api.repos(), report_type, report_noheaders) 
        
        else:
            
            if report_what in [ "all", "distros", "distro" ]:
                self.reporting_print_x_fields(self.api.distros(), report_type, report_fields, report_noheaders)

            if report_what in [ "all", "profiles", "profile" ]:
                self.reporting_print_x_fields(self.api.profiles(), report_type, report_fields, report_noheaders)

            if report_what in [ "all", "systems", "system" ]:
                self.reporting_print_x_fields(self.api.systems(), report_type, report_fields, report_noheaders)

            if report_what in [ "all", "repos", "repo" ]:
                self.reporting_print_x_fields(self.api.repos(), report_type, report_fields, report_noheaders)
