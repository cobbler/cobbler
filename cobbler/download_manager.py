"""
Cobbler DownloadManager
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2018, Jorgen Maas <jorgen.maas@gmail.com

import logging

import requests
import yaml


class DownloadManager:
    def __init__(self):
        """
        Constructor

        """
        self.logger = logging.getLogger()
        self.cert = ()
        with open("/etc/cobbler/settings.yaml") as main_settingsfile:
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
        return requests.get(url, proxies=proxies, cert=cert)

    def download_file(self, url, dst, proxies=None, cert=None):
        """
        Donwload a file from a URL and save it to any disc location.

        :param url: The URL the request.
        :param dst: The destination file path.
        :param proxies: Override the default Cobbler proxies.
        :param cert: Override the default Cobbler certs.
        """
        if proxies is None:
            proxies = self.proxies
        if cert is None:
            cert = self.cert
        response = requests.get(url, stream=True, proxies=proxies, cert=cert)
        with open(dst, "wb") as handle:
            for chunk in response.iter_content(chunk_size=512):
                # filter out keep-alive new chunks
                if chunk:
                    handle.write(chunk)
