"""
Report from a Cobbler master.
FIXME: reinstante functionality for 2.0

Copyright 2007-2009, Red Hat, Inc and Others
Anderson Silva <ansilva@redhat.com>
Michael DeHaan <michael.dehaan AT gmail>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA.
"""
import re
from typing import Optional

from cobbler import utils


class Report:

    def __init__(self, api):
        """
        Constructor

        :param api: The API to hold all information in Cobbler available.
        """
        self.settings = api.settings()
        self.api = api
        self.report_type = None
        self.report_what = None
        self.report_name = None
        self.report_fields = None
        self.report_noheaders = None
        self.array_re = re.compile(r'([^[]+)\[([^]]+)\]')

    def fielder(self, structure: dict, fields_list: list):
        """
        Return data from a subset of fields of some item

        :param structure: The item structure to report.
        :param fields_list: The list of fields which should be returned.
        :return: The same item with only the given subset of information.
        """
        item = {}

        for field in fields_list:
            internal = self.array_re.search(field)
            # check if field is primary field
            if field in list(structure.keys()):
                item[field] = structure[field]
            # check if subfield in 'interfaces' field
            elif internal and internal.group(1) in list(structure.keys()):
                outer = internal.group(1)
                inner = internal.group(2)
                if isinstance(structure[outer], dict) and inner in structure[outer]:

                    item[field] = structure[outer][inner]
            elif "interfaces" in list(structure.keys()):
                for device in list(structure['interfaces'].keys()):
                    if field in structure['interfaces'][device]:
                        item[field] = device + ': ' + structure['interfaces'][device][field]
        return item

    def reporting_csv(self, info, order: list, noheaders: bool) -> str:
        """
        Formats data on 'info' for csv output

        :param info: The list of iteratable items for csv output.
        :param order: The list of fields which are available in the csv file.
        :param noheaders: Whether headers are printed to the output or not.
        :return: The string with the csv.
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

                if key in list(item.keys()):
                    outputbody += str(item[key]) + sep
                else:
                    outputbody += '-' + sep

                item_count += 1

            info_count += 1
            outputbody += '\n'

        outputheaders += '\n'

        if noheaders:
            outputheaders = ''

        return outputheaders + outputbody

    def reporting_trac(self, info, order: list, noheaders: bool) -> str:
        """
        Formats data on 'info' for trac wiki table output

        :param info: The list of iteratable items for table output.
        :param order: The list of fields which are available in the table file.
        :param noheaders: Whether headers are printed to the output or not.
        :return: The string with the generated table.
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

                if key in list(item.keys()):
                    outputbody += sep + str(item[key])
                else:
                    outputbody += sep + '-'

                item_count = item_count + 1

            info_count = info_count + 1
            outputbody += '||\n'

        outputheaders += '||\n'

        if noheaders:
            outputheaders = ''

        return outputheaders + outputbody

    def reporting_doku(self, info, order: list, noheaders: bool) -> str:
        """
        Formats data on 'info' for doku wiki table output

        :param info: The list of iteratable items for table output.
        :param order: The list of fields which are available in the table file.
        :param noheaders: Whether headers are printed to the output or not.
        :return: The string with the generated table.
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

                if key in list(item.keys()):
                    outputbody += sep2 + item[key]
                else:
                    outputbody += sep2 + '-'

                item_count = item_count + 1

            info_count = info_count + 1
            outputbody += sep2 + '\n'

        outputheaders += sep1 + '\n'

        if noheaders:
            outputheaders = ''

        return outputheaders + outputbody

    def reporting_mediawiki(self, info, order: list, noheaders: bool) -> str:
        """
        Formats data on 'info' for mediawiki table output

        :param info: The list of iteratable items for table output.
        :param order: The list of fields which are available in the table file.
        :param noheaders: Whether headers are printed to the output or not.
        :return: The string with the generated table.
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
                    if key in list(item.keys()):
                        outputbody += sep2 + str(item[key])
                    else:
                        outputbody += sep2 + '-'
                else:
                    if key in list(item.keys()):
                        outputbody += sep1 + str(item[key])
                    else:
                        outputbody += sep1 + '-'

                item_count = item_count + 1

            info_count = info_count + 1
            outputbody += '\n' + sep3 + '\n'

        outputheaders += '\n' + sep3 + '\n'

        if noheaders:
            outputheaders = ''

        return opentable + outputheaders + outputbody + closetable

    def print_formatted_data(self, data, order: list, report_type: str, noheaders: bool):
        """
        Used for picking the correct format to output data as

        :param data: The list of iteratable items for table output.
        :param order: The list of fields which are available in the table file.
        :param noheaders: Whether headers are printed to the output or not.
        :param report_type: The type of report which should be used.
        """
        if report_type == "csv":
            print(self.reporting_csv(data, order, noheaders))
        if report_type == "mediawiki":
            print(self.reporting_mediawiki(data, order, noheaders))
        if report_type == "trac":
            print(self.reporting_trac(data, order, noheaders))
        if report_type == "doku":
            print(self.reporting_doku(data, order, noheaders))

    def reporting_print_sorted(self, collection):
        """
        Prints all objects in a collection sorted by name

        :param collection: The collection to print.
        """
        collection = [x for x in collection]
        collection.sort(key=lambda x: x.name)
        for x in collection:
            print(x.to_string())

    def reporting_list_names2(self, collection, name: str):
        """
        Prints a specific object in a collection.

        :param collection: The collections object to print a collection from.
        :param name: The name of the collection to print.
        """
        obj = collection.get(name)
        if obj is not None:
            print(obj.to_string())

    def reporting_print_all_fields(self, collection, report_name: str, report_type: str, report_noheaders: bool) -> str:
        """
        Prints all fields in a collection as a table given the report type

        :param collection: The collection to report.
        :param report_name: The name of the report.
        :param report_type: The type of report to give.
        :param report_noheaders: Report without the headers. (May be useful for machine parsing)
        :return: A report with all fields included pretty printed or machine readable.
        """
        # per-item hack
        if report_name:
            collection = collection.find(name=report_name)
            if collection:
                collection = [collection]
            else:
                return ""

        collection = [x for x in collection]
        collection.sort(key=lambda x: x.name)
        data = []
        out_order = []
        count = 0
        for x in collection:
            item = {}
            if x.ITEM_TYPE == "settings":
                structure = x.to_dict()
            else:
                structure = x.to_list()

            for (key, value) in list(structure.items()):
                # exception for systems which could have > 1 interface
                if key == "interfaces":
                    for (device, info) in list(value.items()):
                        for (info_header, info_value) in list(info.items()):
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

        self.print_formatted_data(data=data, order=out_order, report_type=report_type, noheaders=report_noheaders)

    def reporting_print_x_fields(self, collection, report_name: str, report_type: str, report_fields: str,
                                 report_noheaders: bool):
        """
        Prints specific fields in a collection as a table given the report type

        :param collection: The collection to report.
        :param report_name: The name of the report.
        :param report_type: The type of report to give.
        :param report_fields: The fields which should be included in the report.
        :param report_noheaders: Report without the headers. (May be useful for machine parsing)
        """
        # per-item hack
        if report_name:
            collection = collection.find(name=report_name)
            if collection:
                collection = [collection]
            else:
                return

        collection = [x for x in collection]
        collection.sort(key=lambda x: x.name)
        data = []
        fields_list = report_fields.replace(' ', '').split(',')

        for x in collection:
            if x.ITEM_TYPE == "settings":
                structure = x.to_dict()
            else:
                structure = x.to_list()
            item = self.fielder(structure, fields_list)
            data.append(item)

        self.print_formatted_data(data=data, order=fields_list, report_type=report_type, noheaders=report_noheaders)

    # -------------------------------------------------------

    def run(self, report_what: Optional[str] = None, report_name: Optional[str] = None,
            report_type: Optional[str] = None, report_fields: Optional[str] = None,
            report_noheaders: Optional[bool] = None):
        """
        Get remote profiles and distros and sync them locally

        1. Handles original report output
        2. Handles all fields of report outputs as table given a format
        3. Handles specific fields of report outputs as table given a format

        :param report_what: What should be reported. May be "all".
        :param report_name: The name of the report.
        :param report_type: The type of report to give.
        :param report_fields: The fields which should be included in the report.
        :param report_noheaders: Report without the headers. (May be useful for machine parsing)
        """
        if report_type == 'text' and report_fields == 'all':
            for collection_name in ["distro", "profile", "system", "repo", "network", "image", "mgmtclass", "package",
                                    "file"]:
                if report_what == "all" or report_what == collection_name or report_what == "%ss" % collection_name \
                        or report_what == "%ses" % collection_name:
                    if report_name:
                        self.reporting_list_names2(self.api.get_items(collection_name), report_name)
                    else:
                        self.reporting_print_sorted(self.api.get_items(collection_name))

        elif report_type == 'text' and report_fields != 'all':
            utils.die("The 'text' type can only be used with field set to 'all'")

        elif report_type != 'text' and report_fields == 'all':
            for collection_name in ["distro", "profile", "system", "repo", "network", "image", "mgmtclass", "package",
                                    "file"]:
                if report_what == "all" or report_what == collection_name or report_what == "%ss" % collection_name \
                        or report_what == "%ses" % collection_name:
                    self.reporting_print_all_fields(self.api.get_items(collection_name), report_name, report_type,
                                                    report_noheaders)

        else:
            for collection_name in ["distro", "profile", "system", "repo", "network", "image", "mgmtclass", "package",
                                    "file"]:
                if report_what == "all" or report_what == collection_name or report_what == "%ss" % collection_name \
                        or report_what == "%ses" % collection_name:
                    self.reporting_print_x_fields(self.api.get_items(collection_name), report_name, report_type,
                                                  report_fields, report_noheaders)
