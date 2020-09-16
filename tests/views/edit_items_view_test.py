import pytest
from django.urls import reverse

# Tests the correct views are displayed when editing items

def test_edit_aifile(login_web):
    client, response = login_web( reverse('aifile_edit', args=['default.ks']) )

    assert response.status_code == 200
    assert 'aifile_edit.tmpl' in (t.name for t in response.templates)
    assert b'Editing: default.ks' in response.content


def test_edit_snippet(login_web):
    client, response = login_web( reverse('snippet_edit', args=['cobbler_register']) )

    assert response.status_code == 200
    assert 'snippet_edit.tmpl' in (t.name for t in response.templates)
    assert b'Snippet: cobbler_register' in response.content


def test_generic_edit(login_web):
    client, response = login_web( reverse('setting_edit', args=['http_port']) )

    assert response.status_code == 200
    assert 'generic_edit.tmpl' in (t.name for t in response.templates)
    assert b'Editing a Setting: http_port' in response.content
