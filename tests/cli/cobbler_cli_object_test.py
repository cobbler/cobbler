import os
import re
import shlex
import unittest

from cobbler import utils

dummy_file_path = "/root/dummy"

"""
Order is currently important:
self._test_distro(False)
self._test_profile(False)
self._test_system()
run_cmd("cobbler profile remove --name=test-profile")
run_cmd("cobbler distro remove --name=test-distro")

self._test_image()
self._test_repo()
self._test_mgmtclass()
self._test_package()
"""

# TODO: Do not use other test functions. These dependencys must be erased!


def run_cmd(cmd):
    """
    Run a command

    @param cmd str command
    @return str output
    @raise Exception if return code is not 0
    """

    print("run cmd: %s" % cmd)
    args = shlex.split(cmd)
    (output, rc) = utils.subprocess_sp(None, args, shell=False)
    if rc != 0:
        raise Exception
    return output


def get_last_line(lines):
    i = len(lines) - 1
    while lines[i] == '' and i > 0:
        i -= 1

    return lines[i]


class CobblerCliTestObject(unittest.TestCase):
    """
    Test CLI commands on objects
    """

    def setUp(self):
        """
        Initializes testcase
        """

        # create files if necessary
        if not os.path.exists(dummy_file_path):
            open(dummy_file_path, 'w').close()

        # @TODO: delete objects which will be added if they exist
        #        currently, if tests fail, tester may have to delete objects
        #        manually before running tests again

    def tearDown(self):
        """
        Cleans up testcase
        """

        # remove files
        if os.path.exists(dummy_file_path):
            os.remove(dummy_file_path)

    def list_objects(self, object_type):
        """
        Get objects of a type

        @param object_type str object type
        @return list objects
        """

        objects = []
        output = run_cmd("cobbler %s list" % object_type)
        lines = output.split("\n")
        for line in lines:
            if line.strip() != "":
                objects.append(line.strip())
        return objects

    def test_generic_commands(self, object_type, name, attr, objects):
        """
        Test object type generic commands

        @param object_type str object type
        @param name str object name
        @param attr dict object attributes to be tested.
                    Valid keys: name, long_name, initial_value, value
        @param objects list list of objects returned in cobbler <type> list.
                    This is an input parameter for performance reasons. Objects
                    list is already generated before this call(), when object is
                    created, so there is no reason to regenerate it.
        """

        new_name = "test-%s2" % object_type

        # cobbler <type> report
        output = run_cmd("cobbler %s report" % object_type)
        lines = output.split("\n")
        found_objects = {}
        for cur_object in objects:
            found_objects[cur_object] = False
        for line in lines:
            match_obj = re.match(r"Name\s*:\s*(.*)", line)
            if match_obj:
                cur_object = match_obj.group(1)
                self.assertTrue(match_obj.group(1) in objects)
                found_objects[cur_object] = True
        self.assertTrue(False not in found_objects.values())

        # cobbler <type> report <name>
        output = run_cmd("cobbler %s report --name=%s" % (object_type, name))
        regex = r"%s\s+:\s+%s" % (attr["long_name"], attr["initial_value"])
        lines = output.split("\n")
        found = False
        for line in lines:
            if re.match(regex, line):
                found = True
        self.assertTrue(found)

        # cobbler <type> edit
        cmd = "cobbler %s edit --name=%s --%s='%s'" % (object_type, name, attr["name"], attr["value"])
        run_cmd(cmd)

        output = run_cmd("cobbler %s report --name=%s" % (object_type, name))
        regex = re.escape(attr["long_name"]) + r"\s+:\s+" + re.escape(attr["value"])
        lines = output.split("\n")
        found = False
        for line in lines:
            if re.match(regex, line):
                found = True
        self.assertTrue(found)

        # cobbler <type> find
        cmd = "cobbler %s find --%s='%s'" % (object_type, attr["name"], attr["value"])
        output = run_cmd(cmd)
        lines = output.split("\n")
        self.assertTrue(len(lines) >= 1)

        # cobbler <type> copy
        run_cmd("cobbler %s copy --name=%s --newname=%s" % (object_type, name, "%s-copy" % name))

        new_objects = self.list_objects(object_type)
        self.assertTrue(len(new_objects) == len(objects) + 1)

        # cobbler <type> rename
        cmd = "cobbler %s rename --name=%s --newname=%s" % (object_type, name, new_name)
        run_cmd(cmd)
        cmd = "cobbler %s rename --name=%s --newname=%s" % (object_type, new_name, name)
        run_cmd(cmd)

        # cobbler distro remove
        run_cmd("cobbler %s remove --name=%s-copy" % (object_type, name))

        new_objects = self.list_objects(object_type)
        self.assertTrue(len(new_objects) == len(objects))

    def test_distro(self, remove):

        item_type = "distro"
        distro_name = "test-%s" % item_type
        attr = {"name": "arch",
                "long_name": "Architecture",
                "value": "x86_64",
                "initial_value": "i386"}

        distros = self.list_objects(item_type)

        # cobbler <type> add
        cmd = "cobbler %s add --name=%s --kernel=%s --initrd=%s --%s=%s" \
              % (item_type, distro_name, dummy_file_path, dummy_file_path, attr["name"], attr["initial_value"])
        output = run_cmd(cmd)

        new_distros = self.list_objects(item_type)
        self.assertTrue(len(new_distros) == len(distros) + 1)

        self.test_generic_commands(item_type, distro_name, attr, new_distros)

        if remove:
            # cobbler <type> remove
            run_cmd("cobbler %s remove --name=%s" % (item_type, distro_name))

    def test_profile(self, remove):

        item_type = "profile"
        profile_name = "test-%s" % item_type
        attr = {"name": "distro",
                "long_name": "Distribution",
                "value": "test-distro",
                "initial_value": "test-distro"}

        profiles = self.list_objects(item_type)

        # cobbler <type> add
        cmd = "cobbler %s add --name=%s --%s=%s" % (item_type, profile_name, attr["name"], attr["initial_value"])
        run_cmd(cmd)

        new_profiles = self.list_objects(item_type)
        self.assertTrue(len(new_profiles) == len(profiles) + 1)

        self.test_generic_commands(item_type, profile_name, attr, new_profiles)

        if remove:
            # cobbler <type> remove
            run_cmd("cobbler %s remove --name=%s" % (item_type, profile_name))

    def test_system(self):

        item_type = "system"
        system_name = "test-%s" % item_type
        attr = {"name": "profile",
                "long_name": "Profile",
                "value": "test-profile",
                "initial_value": "test-profile"}

        systems = self.list_objects(item_type)

        # cobbler <type> add
        cmd = "cobbler %s add --name=%s --%s=%s" % (item_type, system_name, attr["name"], attr["initial_value"])
        run_cmd(cmd)

        new_systems = self.list_objects(item_type)
        self.assertTrue(len(new_systems) == len(systems) + 1)

        self.test_generic_commands(item_type, system_name, attr, new_systems)

        # cobbler <type> remove
        run_cmd("cobbler %s remove --name=%s" % (item_type, system_name))

    def test_image(self):

        item_type = "image"
        image_name = "test-%s" % item_type
        attr = {"name": "arch",
                "long_name": "Architecture",
                "value": "i386",
                "initial_value": "x86_64"}

        images = self.list_objects(item_type)

        # cobbler <type> add
        cmd = "cobbler %s add --name=%s --%s=%s" % (item_type, image_name, attr["name"], attr["initial_value"])
        output = run_cmd(cmd)

        new_images = self.list_objects(item_type)
        self.assertTrue(len(new_images) == len(images) + 1)

        self.test_generic_commands(item_type, image_name, attr, new_images)

        # cobbler <type> remove
        run_cmd("cobbler %s remove --name=%s" % (item_type, image_name))

    def test_repo(self):

        item_type = "repo"
        repo_name = "test-%s" % item_type
        attr = {"name": "mirror",
                "long_name": "Mirror",
                "value": "ftp://test2.ibm.com",
                "initial_value": "ftp://test.ibm.com/"}

        repos = self.list_objects(item_type)

        # cobbler <type> add
        cmd = "cobbler %s add --name=%s --%s=%s" % (item_type, repo_name, attr["name"], attr["initial_value"])
        output = run_cmd(cmd)

        new_repos = self.list_objects(item_type)
        self.assertTrue(len(new_repos) == len(repos) + 1)

        self.test_generic_commands(item_type, repo_name, attr, new_repos)

        # cobbler <type> remove
        run_cmd("cobbler %s remove --name=%s" % (item_type, repo_name))

    def test_mgmtclass(self):

        item_type = "mgmtclass"
        mgmtclass_name = "test-%s" % item_type
        attr = {"name": "class-name",
                "long_name": "Class Name",
                "value": "test2",
                "initial_value": "test"}

        mgmt_classes = self.list_objects(item_type)

        # cobbler <type> add
        cmd = "cobbler %s add --name=%s --%s=%s" % (item_type, mgmtclass_name, attr["name"], attr["initial_value"])
        output = run_cmd(cmd)

        new_mgmt_classes = self.list_objects(item_type)
        self.assertTrue(len(new_mgmt_classes) == len(mgmt_classes) + 1)

        self.test_generic_commands(item_type, mgmtclass_name, attr, new_mgmt_classes)

        # cobbler <type> remove
        run_cmd("cobbler %s remove --name=%s" % (item_type, mgmtclass_name))

    def test_package(self):

        item_type = "package"
        package_name = "test-%s" % item_type
        attr = {"name": "version",
                "long_name": "Version",
                "value": "2.0",
                "initial_value": "1.0"}

        packages = self.list_objects(item_type)

        # cobbler <type> add
        cmd = "cobbler %s add --name=%s --%s=%s" % (item_type, package_name, attr["name"], attr["initial_value"])
        output = run_cmd(cmd)

        new_packages = self.list_objects(item_type)
        self.assertTrue(len(new_packages) == len(packages) + 1)

        self.test_generic_commands(item_type, package_name, attr, new_packages)

        # cobbler <type> remove
        run_cmd("cobbler %s remove --name=%s" % (item_type, package_name))


if __name__ == '__main__':
    unittest.main()
