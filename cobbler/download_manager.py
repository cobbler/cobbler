"""
Cobbler DownloadManager

Copyright 2018, Jorgen Maas <jorgen.maas@gmail.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA
"""
import logging

import requests


class DownloadManager:

    def __init__(self, api):
        """
        Constructor

        :param api: This is the current API instance which holds the settings.
        """
        self.settings = api.settings()
        self.logger = logging.getLogger()
        self.cert = ()
        if self.settings.proxy_url_ext:
            # requests wants a dict like:  protocol: proxy_uri
            self.proxies = self.settings.proxy_url_ext
        else:
            self.proxies = {}

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
