"""
Cobbler DownloadManager
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2018, Jorgen Maas <jorgen.maas@gmail.com

import logging

import requests
import yaml


class DownloadManager:
    """
    TODO
    """

    def __init__(self):
        """
        Constructor

        """
        self.logger = logging.getLogger()
        self.cert = ()
        with open("/etc/cobbler/settings.yaml", encoding="UTF-8") as main_settingsfile:
            ydata = yaml.safe_load(main_settingsfile)
        # requests wants a dict like:  protocol: proxy_uri
        self.proxies = ydata.get("proxy_url_ext", {})

    def urlread(self, url, proxies=None, cert=None):
        """
        Read the content of a given URL and pass the requests. Response object to the caller.

        :param url: The URL the request.
        :param proxies: Override the default Cobbler proxies.
        :param cert: Override the default Cobbler certs.
        :returns: The Python ``requests.Response`` object.
        """
        if proxies is None:
            proxies = self.proxies
        if cert is None:
            cert = self.cert
        return requests.get(url, proxies=proxies, cert=cert, timeout=600)
