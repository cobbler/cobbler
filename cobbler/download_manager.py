"""
Cobbler DownloadManager
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2018, Jorgen Maas <jorgen.maas@gmail.com

import logging
from typing import TYPE_CHECKING, Any, Optional, Tuple, Union

import requests
import yaml

if TYPE_CHECKING:
    from requests import Response


class DownloadManager:
    """
    Class to provide an easy way to download files from the web inside Cobbler. Mainly present to provide support for
    system-wide proxies.
    """

    def __init__(self) -> None:
        """
        Constructor
        """
        self.logger = logging.getLogger()
        with open("/etc/cobbler/settings.yaml", encoding="UTF-8") as main_settingsfile:
            ydata = yaml.safe_load(main_settingsfile)
        # requests wants a dict like:  protocol: proxy_uri
        proxy_url_ext = ydata.get("proxy_url_ext", "")
        if proxy_url_ext:
            self.proxies = {
                "http": proxy_url_ext,
                "https": proxy_url_ext,
            }
        else:
            self.proxies = {}

    def urlread(
        self,
        url: str,
        proxies: Any = None,
        cert: Optional[Union[str, Tuple[str, str]]] = None,
    ) -> "Response":
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
            return requests.get(url, proxies=proxies, cert=cert, timeout=600)
        return requests.get(url, proxies=proxies, timeout=600)
