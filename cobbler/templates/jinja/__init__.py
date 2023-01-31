"""
Template functionality that is tied to Jinja2.
"""

from cobbler.templates import BaseTemplateProvider

try:
    import jinja2

    JINJA2_AVAILABLE = True
except ModuleNotFoundError:
    jinja2 = None
    JINJA2_AVAILABLE = False


class JinjaTemplateProvider(BaseTemplateProvider):
    """
    Provides support for the Jinja2 template language to Cobbler.

    See: https://jinja.palletsprojects.com/en/3.1.x/
    """

    template_language = "jinja"

    @property
    def template_type_available(self) -> bool:
        return JINJA2_AVAILABLE

    def render(self, raw_data: str, search_table: dict) -> str:
        try:
            if self.api.settings().jinja2_includedir:
                template = jinja2.Environment(
                    loader=jinja2.FileSystemLoader(
                        self.api.settings().jinja2_includedir
                    )
                ).from_string(raw_data)
            else:
                template = jinja2.Template(raw_data)
            data_out = template.render(search_table)
        except Exception as exc:
            self.logger.warning("errors were encountered rendering the template")
            self.logger.warning(str(exc))
            data_out = "# EXCEPTION OCCURRED DURING JINJA2 TEMPLATE PROCESSING\n"

        return data_out
