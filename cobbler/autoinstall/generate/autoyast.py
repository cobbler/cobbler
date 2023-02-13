"""
This module is responsible to generate AutoYAST files and metadata.

Documentation for AutoYAST can be found `here <https://doc.opensuse.org/projects/autoyast/>`_
"""

import xml.dom.minidom
from cobbler import utils
from cobbler.autoinstall.generate.base import AutoinstallBaseGenerator


class AutoYastGenerator(AutoinstallBaseGenerator):
    """
    Implementation of the abstract :class:`~cobbler.autoinstall.generate.AutoinstallBaseGenerator` for AutoYAST.
    """

    def generate_autoinstall(self, obj, template: str, requested_file: str) -> str:
        what = obj.ITEM_TYPE
        blended = utils.blender(self.api, False, obj)
        srv = blended["http_server"]

        document = xml.dom.minidom.parseString(template)

        # Do we already have the #raw comment in the XML? (add_comment = 0 means, don't add #raw comment)
        add_comment = 1
        for node in document.childNodes[1].childNodes:
            if node.nodeType == node.ELEMENT_NODE and node.tagName == "cobbler":
                add_comment = 0
                break

        # Add some cobbler information to the XML file, maybe that should be configurable.
        if add_comment == 1:
            cobbler_element = document.createElement("cobbler")
            cobbler_element_system = xml.dom.minidom.Element("system_name")
            cobbler_element_profile = xml.dom.minidom.Element("profile_name")
            cobbler_text_profile = document.createTextNode(obj.name)
            cobbler_element_profile.appendChild(cobbler_text_profile)

            cobbler_element_server = document.createElement("server")
            cobbler_text_server = document.createTextNode(blended["http_server"])
            cobbler_element_server.appendChild(cobbler_text_server)

            cobbler_element.appendChild(cobbler_element_server)
            cobbler_element.appendChild(cobbler_element_system)
            cobbler_element.appendChild(cobbler_element_profile)

        if self.api.settings().run_install_triggers:
            # notify cobblerd when we start/finished the installation
            protocol = self.api.settings().autoinstall_scheme
            AutoYastGenerator.__add_auto_yast_script(
                document,
                "pre-scripts",
                f'\ncurl "{protocol}://{srv}/cblr/svc/op/trig/mode/pre/{what}/{obj.name}" > /dev/null',
            )
            AutoYastGenerator.__add_auto_yast_script(
                document,
                "init-scripts",
                f'\ncurl "{protocol}://{srv}/cblr/svc/op/trig/mode/post/{what}/{obj.name}" > /dev/null',
            )

        return document.toxml()

    @staticmethod
    def __create_autoyast_script(document, script, name):
        """
        This method attaches a script with a given name to an existing AutoYaST XML file.

        :param document: The existing AutoYaST XML file.
        :param script: The script to attach.
        :param name: The name of the script.
        :return: The AutoYaST file with the attached script.
        """
        new_script = document.createElement("script")
        new_script_source = document.createElement("source")
        new_script_source_text = document.createCDATASection(script)
        new_script.appendChild(new_script_source)

        new_script_file = document.createElement("filename")
        new_script_file_text = document.createTextNode(name)
        new_script.appendChild(new_script_file)

        new_script_source.appendChild(new_script_source_text)
        new_script_file.appendChild(new_script_file_text)
        return new_script

    @staticmethod
    def __add_auto_yast_script(document, script_type, source):
        """
        Add scripts to an existing AutoYaST XML.

        :param document: The existing AutoYaST XML object.
        :param script_type: The type of the script which should be added.
        :param source: The source of the script. This should be ideally a string.
        """
        scripts = document.getElementsByTagName("scripts")
        if scripts.length == 0:
            new_scripts = document.createElement("scripts")
            document.documentElement.appendChild(new_scripts)
            scripts = document.getElementsByTagName("scripts")
        added = 0
        for stype in scripts[0].childNodes:
            if stype.nodeType == stype.ELEMENT_NODE and stype.tagName == script_type:
                stype.appendChild(
                    AutoYastGenerator.__create_autoyast_script(
                        document, source, script_type + "_cobbler"
                    )
                )
                added = 1
        if added == 0:
            new_chroot_scripts = document.createElement(script_type)
            new_chroot_scripts.setAttribute("config:type", "list")
            new_chroot_scripts.appendChild(
                AutoYastGenerator.__create_autoyast_script(
                    document, source, script_type + "_cobbler"
                )
            )
            scripts[0].appendChild(new_chroot_scripts)
