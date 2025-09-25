"""
Cobbler provides builtin methods for use in Cheetah templates. $SNIPPET is one
such function and is now used to implement Cobbler's SNIPPET:: syntax.

The CobblerCheetahTemplate class is defined using the Cheetah language. Using the 'compile' function we can compile the
source directly into a Python class. This class will allow us to define the cheetah builtins.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Written by Daniel Guernsey <danpg102@gmail.com>
# SPDX-FileCopyrightText: Contributions by Michael DeHaan <michael.dehaan AT gmail>
# SPDX-FileCopyrightText: US Government work; No explicit copyright attached to this file.

import logging
import os
import pprint
import re
from typing import TYPE_CHECKING, Any, Dict, Match, Optional, TextIO, Tuple, Union
from uuid import UUID

from cobbler import utils
from cobbler.cexceptions import CX
from cobbler.templates import BaseTemplateProvider

try:
    from Cheetah.Template import Template as CheetahTemplate  # type: ignore

    CHEETAH_AVAILABLE = True
except ModuleNotFoundError:
    CheetahTemplate = None  # pylint: disable=invalid-name
    CHEETAH_AVAILABLE = False  # type: ignore[reportConstantRedefinition]

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI

logger = logging.getLogger()


class CobblerCheetahTemplate(CheetahTemplate):  # type: ignore
    """
    This class will allow us to include any pure python builtin functions.
    It derives from the cheetah-compiled class above. This way, we can include both types (cheetah and pure python) of
    builtins in the same base template.

    This part (see 'Template' below for the other part) handles the actual inclusion of the file contents. We
    still need to make the snippet's namespace (searchList) available to the template calling SNIPPET (done in
    the other part).

    This function can be used in two ways:
    Cheetah syntax:
    - $SNIPPET('my_snippet')
    - SNIPPET syntax:
    - SNIPPET::my_snippet

    This follows all of the rules of snippets and advanced snippets. First it searches for a per-system snippet,
    then a per-profile snippet, then a general snippet. If none is found, a comment explaining the error is
    substituted.
    """

    # FIXME: Replace Snippet Mechanism with one that can load templates by name from the API, don't reuse the name since
    # the mechanism is completly different.

    def __init__(self, **kwargs: Any):
        """
        Constructor for this derived class. We include two additional default templates.

        :param kwargs: These arguments get passed to the super constructor of this class.
        """
        # pylint: disable-next=invalid-name
        self.BuiltinTemplate = CheetahTemplate.compile(  # type: ignore
            source="\n".join(
                [
                    "#def SNIPPET($file)",
                    "#set $snippet = $read_snippet($file)",
                    "#if $snippet",
                    "#include source=$snippet",
                    "#else",
                    "# Error: no snippet data for $file",
                    "#end if",
                    "#end def",
                ]
            )
            + "\n"
        )
        self.cobbler_api: "CobblerAPI" = kwargs.pop("cobbler_api")
        super().__init__(**kwargs)  # type: ignore

    @classmethod
    def compile(cls, *args: Any, **kwargs: Any) -> bytes:
        """
        Compile a cheetah template with Cobbler modifications. Modifications include ``SNIPPET::`` syntax replacement
        and inclusion of Cobbler builtin methods. Please be aware that you cannot use the ``baseclass`` attribute of
        Cheetah anymore due to the fact that we are using it in our implementation to enable the Cheetah Macros.

        This function gets called by Cheetah.Template.Template.__init__ to compile the template into a class. This
        is probably a kludge, but it add a baseclass argument to the standard compile (see Cheetah's compile docstring)
        and returns the resulting class. This argument, of course, points to this class. Now any methods entered here
        (or in the base class above) will be accessible to all cheetah templates compiled by Cobbler.

        :param args: These just get passed right to Cheetah.
        :param kwargs: We just execute our own preprocessors and remove them and let afterwards handle Cheetah the rest.
        :return: The compiled template.
        """

        def replacer(match: Match[str]) -> str:
            return f"$SNIPPET('{match.group(1)}')"

        def preprocess(
            source: Optional[str], file: Optional[Union[TextIO, str]]
        ) -> Tuple[str, Optional[Union[TextIO, str]]]:
            # Normally, the cheetah compiler worries about this, but we need to preprocess the actual source.
            if source is None:
                if isinstance(file, TextIO):
                    source = file.read()
                elif isinstance(file, str):
                    if os.path.exists(file):
                        with open(file, "r", encoding="UTF-8") as snippet_fd:
                            source = "#errorCatcher Echo\n" + snippet_fd.read()
                    else:
                        source = f"# Unable to read {file}\n"
                # Stop Cheetah from throwing a fit.
                file = None

            snippet_regex = re.compile(r"SNIPPET::([A-Za-z0-9_\-/.]+)")
            results = snippet_regex.sub(replacer, source or "")
            return results, file

        preprocessors = [preprocess]
        if "preprocessors" in kwargs:
            preprocessors.extend(kwargs["preprocessors"])
        kwargs["preprocessors"] = preprocessors

        # Now let Cheetah do the actual compilation - mypy can't introspect Cheetah
        return super().compile(*args, **kwargs)  # type: ignore

    def validate_uuid(self, possible_uuid: str) -> bool:
        """
        Copied from :meth:`~cobbler.validate.validate_uuid` to prevent issues with module availablity during
        template processing.

        :param possible_uuid: The str with the UUID.
        :return: True in case it is one, False otherwise.
        """
        try:
            uuid_obj = UUID(possible_uuid, version=4)
        except ValueError:
            return False
        return uuid_obj.hex == possible_uuid

    def read_snippet(self, template_identifier: str) -> Optional[str]:
        """
        Locate the appropriate snippet for the current system and profile and read its contents.

        This will first check for a per-system snippet, a per-profile snippet, a distro snippet, and a general snippet.

        :param template_identifier: The name or uid of the template.
        :return: None (if the snippet file was not found) or the string with the read snippet.
        """
        if self.validate_uuid(template_identifier):
            search_result = self.cobbler_api.find_template(
                False, False, uid=template_identifier
            )
        else:
            search_result = self.cobbler_api.find_template(
                False, False, name=template_identifier
            )

        if search_result is None or isinstance(search_result, list):
            logger.warning("Requested Cheetah Snippet not found!")
            return None

        for snippet_class in ("system", "profile", "distro"):
            if self.varExists(f"{snippet_class}_name"):  # type: ignore
                if self.validate_uuid(template_identifier):
                    override_search_result = self.cobbler_api.find_template(
                        False,
                        False,
                        uid=template_identifier,
                        tags=f"per_{snippet_class}",
                    )
                else:
                    override_search_result = self.cobbler_api.find_template(
                        False,
                        False,
                        name=template_identifier,
                        tags=f"per_{snippet_class}",
                    )
                if isinstance(override_search_result, list):
                    logger.warning(
                        "Override Template Search returned ambigous search result!"
                    )
                    return None
                if override_search_result is not None:
                    logger.info(
                        "Using override Template %s!", override_search_result.uid
                    )
                    return override_search_result.content

        return "#errorCatcher ListErrors\n" + search_result.content

    def SNIPPET(self, file: str) -> Any:
        """
        Include the contents of the named snippet here. This is equivalent to the #include directive in Cheetah, except
        that it searches for system and profile specific snippets, and it includes the snippet's namespace.

        This may be a little frobby, but it's really cool. This is a pure python portion of SNIPPET that appends the
        snippet's searchList to the caller's searchList. This makes any #defs within a given snippet available to the
        template that included the snippet.

        :param file: The snippet file to read and include in the template.
        :return: The updated template.
        """
        # First, do the actual inclusion. Cheetah (when processing #include) will track the inclusion in
        # self._CHEETAH__cheetahIncludes
        result = self.BuiltinTemplate.SNIPPET(self, file)  # type: ignore

        # Now do our dirty work: locate the new include, and append its searchList to ours. We have to compute the full
        # path again? Eww.

        # This weird method is getting even weirder, the cheetah includes keys are no longer filenames but actual
        # contents of snippets. Regardless this seems to work and hopefully it will be ok.

        snippet_contents = self.read_snippet(file)
        if snippet_contents:
            # Only include what we don't already have. Because Cheetah passes our searchList into included templates,
            # the snippet's searchList will include this templates searchList. We need to avoid duplicating entries.
            child_list = self._CHEETAH__cheetahIncludes[snippet_contents].searchList()  # type: ignore
            my_list = self.searchList()  # type: ignore
            for child_elem in child_list:  # type: ignore
                if child_elem not in my_list:
                    my_list.append(child_elem)  # type: ignore

        return result  # type: ignore

    # pylint: disable=R0201
    def sedesc(self, value: str) -> str:
        """
        Escape a string for use in sed.

        This function is used by several cheetah methods in cheetah_macros. It can be used by the end user as well.

        Example: Replace all instances of ``/etc/banner`` with a value stored in ``$new_banner``

        ..code::

           sed 's/$sedesc("/etc/banner")/$sedesc($new_banner)/'

        :param value: The phrase to escape.
        :return: The escaped phrase.
        """

        def escchar(character: str) -> str:
            if character in "/^.[]$()|*+?{}\\":
                return "\\" + character
            return character

        return "".join([escchar(c) for c in value])


class CheetahTemplateProvider(BaseTemplateProvider):
    """
    Provides support for the Cheetah template language to Cobbler.

    See: https://cheetahtemplate.org/
    """

    template_language = "cheetah"

    @property
    def template_type_available(self) -> bool:
        return CHEETAH_AVAILABLE

    @property
    def template_file_extension(self) -> str:
        return "template"

    def check_for_invalid_imports(self, data: str):
        """
        Ensure that Cheetah code is not importing Python modules that may allow for advanced privileges by ensuring we
        whitelist the imports that we allow.

        :param data: The Cheetah code to check.
        :raises CX: Raised in case there could be a pontentially insecure import in the template.
        """
        lines = data.split("\n")
        for line in lines:
            if "#import" in line or "#from" in line:
                rest = (
                    line.replace("#import", "")
                    .replace("#from", "")
                    .replace("import", ".")
                    .replace(" ", "")
                    .strip()
                )
                if rest not in self.api.settings().cheetah_import_whitelist:
                    raise CX(f"Potentially insecure import in template: {rest}")

    def render(self, raw_data: str, search_table: Dict[str, Any]) -> str:
        self.check_for_invalid_imports(raw_data)

        # Backward support for Cobbler's legacy (and slightly more readable) template syntax.
        raw_data = raw_data.replace("TEMPLATE::", "$")

        # HACK: the autoinstall_meta field may contain nfs://server:/mount in which case this is likely WRONG for
        # automated installation files, which needs the NFS directive instead. Do this to make the templates work.
        newdata = ""
        if "tree" in search_table and search_table["tree"].startswith("nfs://"):
            for line in raw_data.split("\n"):
                if line.find("--url") != -1 and line.find("url ") != -1:
                    rest = search_table["tree"][6:]  # strip off "nfs://" part
                    try:
                        (server, directory) = rest.split(":", 2)
                    except Exception as error:
                        raise SyntaxError(
                            f"Invalid syntax for NFS path given during import: {search_table['tree']}"
                        ) from error
                    line = f"nfs --server {server} --dir {directory}"
                    # But put the URL part back in so koan can still see what the original value was
                    line += "\n" + f"#url --url={search_table['tree']}"
                newdata += line + "\n"
            raw_data = newdata

        # Tell Cheetah not to blow up if it can't find a symbol for something.
        raw_data = "#errorCatcher ListErrors\n" + raw_data

        table_copy = search_table.copy()

        # For various reasons we may want to call a module inside a template and pass it all of the template variables.
        # The variable "template_universe" serves this purpose to make it easier to iterate through all of the variables
        # without using internal Cheetah variables

        search_table.update({"template_universe": table_copy})

        # Now do full templating scan, where we will also templatify the snippet insertions
        template = CobblerCheetahTemplate.compile(
            moduleName="cobbler.template_api",
            className="CobblerDynamicTemplate",
            source=raw_data,
            compilerSettings={"useStackFrame": False},
            baseclass=CobblerCheetahTemplate,
        )

        try:
            generated_template_class = template(searchList=[search_table], cobbler_api=self.api)  # type: ignore
            data_out = str(generated_template_class)  # type: ignore
            self.last_errors = generated_template_class.errorCatcher().listErrors()  # type: ignore
            if self.last_errors:  # type: ignore
                self.logger.warning("errors were encountered rendering the template")
                self.logger.warning("\n%s", pprint.pformat(self.last_errors))  # type: ignore
        except Exception as error:
            self.logger.error(utils.cheetah_exc(error))
            raise CX(
                "Error templating file, check cobbler.log for more details"
            ) from error

        return data_out
