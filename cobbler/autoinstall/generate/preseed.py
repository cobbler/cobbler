"""
This module is responsible to generate preseed files and metadata.

Documentation for AutoYAST can be found `in the wiki <https://wiki.debian.org/DebianInstaller/Preseed>`_ and
`in the guide <https://www.debian.org/releases/stable/amd64/apb.en.html>`_
"""

from cobbler.autoinstall.generate.base import AutoinstallBaseGenerator


class PreseedGenerator(AutoinstallBaseGenerator):
    """
    TODO
    """

    def generate_autoinstall(self, obj, template: str, requested_file: str) -> str:
        pass
