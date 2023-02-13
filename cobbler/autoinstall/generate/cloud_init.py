"""
TODO
"""

from cobbler.autoinstall.generate.base import AutoinstallBaseGenerator


class CloudInitGenerator(AutoinstallBaseGenerator):
    """
    TODO
    """

    def generate_autoinstall(self, obj, template: str, requested_file: str) -> str:
        if requested_file == "user-data":
            return ""
        if requested_file == "meta-data":
            return ""
        if requested_file == "vendor-data":
            return ""
        return ""

    def __generate_user_data(self) -> str:
        """
        TODO

        :return: TODO
        """
        pass
