"""
Template functionality that is tied to Jinja2.

Provides :class:`JinjaTemplateProvider`, the Jinja2 implementation of
:class:`~cobbler.templates.BaseTemplateProvider`, a custom :class:`CobblerJinjaLoader` that resolves
``{% include %}``/``{% extends %}`` targets through the CobblerAPI template store, and the custom ``toyaml``
filter.
"""

# pyright: strict, reportPossiblyUnboundVariable=false

from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Tuple

import yaml

from cobbler.templates import BaseTemplateProvider

try:
    import jinja2

    JINJA2_AVAILABLE = True
except ModuleNotFoundError:
    JINJA2_AVAILABLE = False  # type: ignore[reportConstantRedefinition]


if TYPE_CHECKING:
    from cobbler.api import CobblerAPI

if JINJA2_AVAILABLE:

    class CobblerJinjaLoader(jinja2.BaseLoader):
        """
        Custom Jinja template loader that allows loading templates from the CobblerAPI.
        """

        def __init__(self, cobbler_api: "CobblerAPI") -> None:
            """
            Constructor

            :param cobbler_api: The CobblerAPI object to search for templates.
            """
            self.cobbler_api = cobbler_api

        def get_source(
            self, environment: "jinja2.Environment", template: str
        ) -> Tuple[str, Optional[str], Optional[Callable[[], bool]]]:
            """
            Look up a template by name through the CobblerAPI and return its source for Jinja2 to compile.

            This backs ``{% include %}``/``{% extends %}`` resolution for templates rendered through
            :class:`JinjaTemplateProvider`.

            :param environment: The Jinja2 environment requesting the template (unused, required by the
                ``jinja2.BaseLoader`` interface).
            :param template: The name of the template to look up via :meth:`~cobbler.api.CobblerAPI.find_template`.
            :return: A tuple of the template source, the template name (used as the cache key), and ``None`` since
                no up-to-date check is supported.
            :raises jinja2.TemplateNotFound: If no template with the given name exists, or if the name is
                ambiguous (resolves to more than one template).
            """
            search_result = self.cobbler_api.find_template(False, False, name=template)
            if search_result is None or isinstance(search_result, list):
                raise jinja2.TemplateNotFound(template)
            return search_result.content, search_result.name, None


def toyaml(data: Any) -> str:
    """
    Function which is registred as a custom Jinja filter and allows convering arbitrary data into YAML.
    """
    return yaml.dump(data).rstrip("\n")


class JinjaTemplateProvider(BaseTemplateProvider):
    """
    Provides support for the Jinja2 template language to Cobbler.

    See: https://jinja.palletsprojects.com/en/3.1.x/
    """

    template_language = "jinja"

    def __init__(self, api: "CobblerAPI"):
        """
        Constructor.

        In addition to the base initialization, if Jinja2 is installed, this sets up a :class:`jinja2.Environment`
        that loads templates via :class:`CobblerJinjaLoader` and registers the custom ``any``, ``all`` and
        ``toyaml`` filters. If Jinja2 is not installed, no environment is created and :meth:`render` will always
        return an empty string.

        :param api: The CobblerAPI instance to use for querying for information inside Cobbler.
        """
        super().__init__(api)
        if JINJA2_AVAILABLE:
            self.jinja2_env = jinja2.Environment(loader=CobblerJinjaLoader(self.api))
            self.jinja2_env.filters["any"] = any  # type: ignore
            self.jinja2_env.filters["all"] = all  # type: ignore
            self.jinja2_env.filters["toyaml"] = toyaml  # type: ignore

    @property
    def template_type_available(self) -> bool:
        """
        Returns whether the Jinja2 templating engine is available.

        :return: ``True`` if the ``jinja2`` package could be imported, ``False`` otherwise.
        """
        return JINJA2_AVAILABLE

    @property
    def template_file_extension(self) -> str:
        return "jinja"

    def render(self, raw_data: str, search_table: Dict[str, Any]) -> str:
        """
        Render a Jinja2 template into its final output.

        Unlike :meth:`~cobbler.templates.cheetah.CheetahTemplateProvider.render`, rendering errors are not raised
        to the caller: any exception encountered while parsing or rendering the template is logged and a
        placeholder comment is returned instead. If the ``jinja2`` package is not installed, an empty string is
        returned without attempting to render anything.

        :param raw_data: The Jinja2 template source to render.
        :param search_table: The dict of metadata keys and values available to the template.
        :return: The rendered template, a placeholder comment if rendering failed, or an empty string if Jinja2 is
            unavailable.
        """
        if not JINJA2_AVAILABLE:
            return ""
        try:
            template = self.jinja2_env.from_string(raw_data)
            data_out = template.render(search_table)
        except Exception as exc:
            self.logger.warning("errors were encountered rendering the template")
            self.logger.warning(str(exc))
            data_out = "# EXCEPTION OCCURRED DURING JINJA2 TEMPLATE PROCESSING\n"

        return data_out
