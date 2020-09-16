import pytest
from django.urls import reverse

# Test action requests in view. These test the website operation 
# and do not test that the requested background action succeeded

def test_check_action(login_web):
    client, response = login_web( reverse('check') )

    assert response.status_code == 200
    assert 'check.tmpl' in (t.name for t in response.templates)

@pytest.mark.parametrize("action", [
    'reposync', 'buildiso', 'hardlink', 'sync'
])
def test_posted_action(login_web, action):
    client, response = login_web( reverse('index') )
    response = client.post( reverse(action) )

    assert response.status_code == 302
    assert response['location'] == '/cobbler_web/task_created'
