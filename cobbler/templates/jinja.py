"""
Template functionality that is tied to Jinja2.
"""

# pyright: strict, reportPossiblyUnboundVariable=false

from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Tuple

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
        TODO
        """

        def __init__(self, cobbler_api: "CobblerAPI") -> None:
            """
            Constructor

            :param cobbler_api: TODO
            """
            self.cobbler_api = cobbler_api

        def get_source(
            self, environment: "jinja2.Environment", template: str
        ) -> Tuple[str, Optional[str], Optional[Callable[[], bool]]]:
            """
            TODO
            """
            search_result = self.cobbler_api.find_template(False, False, name=template)
            if search_result is None or isinstance(search_result, list):
                raise jinja2.TemplateNotFound(template)
            return search_result.content, search_result.name, None


class JinjaTemplateProvider(BaseTemplateProvider):
    """
    Provides support for the Jinja2 template language to Cobbler.

    See: https://jinja.palletsprojects.com/en/3.1.x/
    """

    template_language = "jinja"

    def __init__(self, api: "CobblerAPI"):
        super().__init__(api)
        if JINJA2_AVAILABLE:
            self.jinja2_env = jinja2.Environment(loader=CobblerJinjaLoader(self.api))

    @property
    def template_type_available(self) -> bool:
        return JINJA2_AVAILABLE

    @property
    def template_file_extension(self) -> str:
        return "jinja"

    def render(self, raw_data: str, search_table: Dict[str, Any]) -> str:
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
