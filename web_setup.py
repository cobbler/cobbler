#!/usr/bin/env python
from distutils.core import setup

#Django Configuration
dj_config       = "/etc/httpd/conf.d/"
#dj_templates    = "/usr/share/cobbler/web/cobbler_web/templates"
#dj_webui        = "/usr/share/cobbler/web/cobbler_web"
#dj_webui2       = "/usr/share/cobbler/web/cobbler_web/templatetags"
#dj_webui_proj   = "/usr/share/cobbler/web"
dj_sessions     = "/var/lib/cobbler/webui_sessions"
dj_js           = "/var/www/cobbler_webui_content/"

#Web Content
wwwcon      = "/var/www/cobbler_webui_content"

setup(
    name = "cobbler-web",
    version = "2.0.4",
    description = "Web interface for Cobbler",
    long_description = "Web interface for Cobbler that allows visiting http://server/cobbler_web to configure the install server.",
    author = "Michael DeHaan",
    author_email = "mdehaan@redhat.com",
    url = "http://fedorahosted.org/cobbler/",
    license = "GPLv2+",
    requires = ["mod_python",
                "cobbler",
    ],
    packages = ["web", "web.cobbler_web", "web.cobbler_web.templatetags"],
    package_dir = {"cobbler_web": "web/cobbler_web"},
    package_data = {"web.cobbler_web": ["templates/*.tmpl"]},
    data_files = [
        (dj_config,     ['config/cobbler_web.conf']),
        (dj_sessions,   []),
        (wwwcon,        ['web/content/style.css']),
        (wwwcon,        ['web/content/logo-cobbler.png']),
        (dj_js,         ['web/content/cobbler.js']),
        # FIXME: someday Fedora/EPEL will package these and then we should not embed them then.
        (dj_js,         ['web/content/jquery-1.3.2.js']),
        (dj_js,         ['web/content/jquery-1.3.2.min.js']),
        (dj_js,         ['web/content/jsGrowl_jquery.js']),
        (dj_js,         ['web/content/jsGrowl.js']),
        (dj_js,         ['web/content/jsgrowl_close.png']),
        (dj_js,         ['web/content/jsgrowl_corners.png']),
        (dj_js,         ['web/content/jsgrowl_middle_hover.png']),
        (dj_js,         ['web/content/jsgrowl_corners_hover.png']),
        (dj_js,         ['web/content/jsgrowl_side_hover.png']),
        (dj_js,         ['web/content/jsGrowl.css']),
#
#        # django webui content
        (dj_config,     ['config/cobbler_web.conf']),
#        (dj_templates,  ['web/cobbler_web/templates/blank.tmpl']),
#        (dj_templates,  ['web/cobbler_web/templates/empty.tmpl']),
#        (dj_templates,  ['web/cobbler_web/templates/enoaccess.tmpl']),
#        (dj_templates,  ['web/cobbler_web/templates/header.tmpl']),
#        (dj_templates,  ['web/cobbler_web/templates/index.tmpl']),
#        (dj_templates,  ['web/cobbler_web/templates/item.tmpl']),
#        (dj_templates,  ['web/cobbler_web/templates/ksfile_edit.tmpl']),
#        (dj_templates,  ['web/cobbler_web/templates/ksfile_list.tmpl']),
#        (dj_templates,  ['web/cobbler_web/templates/snippet_edit.tmpl']),
#        (dj_templates,  ['web/cobbler_web/templates/snippet_list.tmpl']),
#        (dj_templates,  ['web/cobbler_web/templates/master.tmpl']),
#        (dj_templates,  ['web/cobbler_web/templates/message.tmpl']),
#        (dj_templates,  ['web/cobbler_web/templates/paginate.tmpl']),
#        (dj_templates,  ['web/cobbler_web/templates/settings.tmpl']),
#        (dj_templates,  ['web/cobbler_web/templates/generic_edit.tmpl']),
#        (dj_templates,  ['web/cobbler_web/templates/generic_list.tmpl']),
#        (dj_templates,  ['web/cobbler_web/templates/generic_delete.tmpl']),
#        (dj_templates,  ['web/cobbler_web/templates/generic_rename.tmpl']),
#        (dj_templates,  ['web/cobbler_web/templates/events.tmpl']),
#        (dj_templates,  ['web/cobbler_web/templates/eventlog.tmpl']),
#        (dj_templates,  ['web/cobbler_web/templates/import.tmpl']),
#        (dj_templates,  ['web/cobbler_web/templates/task_created.tmpl']),
#        (dj_templates,  ['web/cobbler_web/templates/check.tmpl']),
        
#        # django code, private to cobbler-web application
#        (dj_webui,      ['web/cobbler_web/__init__.py']),
#        (dj_webui_proj, ['web/__init__.py']),
#        (dj_webui_proj, ['web/urls.py']),
#        (dj_webui_proj, ['web/manage.py']),
#        (dj_webui_proj, ['web/settings.py']),
#        (dj_webui,      ['web/cobbler_web/urls.py']),
#        (dj_webui,      ['web/cobbler_web/views.py']),
#        (dj_webui2,     ['web/cobbler_web/templatetags/site.py']),
#        (dj_webui2,     ['web/cobbler_web/templatetags/__init__.py']),
        (dj_sessions,   []),
    ],

)
