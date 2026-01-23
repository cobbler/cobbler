"""
Test module to verify the built-in snippets for Cloud-Init.
"""

# pylint: disable=too-many-lines

from typing import Any, Dict, List

import pytest
import yaml

from cobbler.api import CobblerAPI


@pytest.mark.parametrize(
    "input_meta,expected_result",
    [
        ({}, []),
        (
            {
                "cloud_init_ansible": {
                    "package_name": "ansible-core",
                    "install_method": "distro",
                    "pull": [
                        {
                            "url": "https://github.com/holmanb/vmboot.git",
                            "playbook_names": ["ubuntu.yml"],
                        }
                    ],
                }
            },
            [
                "ansible:",
                '  install_method: "distro"',
                '  package_name: "ansible-core"',
                "  pull:",
                "    -",
                '      url: "https://github.com/holmanb/vmboot.git"',
                '      playbook_names: [ "ubuntu.yml" ]',
            ],
        ),
        (
            {
                "cloud_init_ansible": {
                    "install_method": "pip",
                    "package_name": "ansible-core",
                    "pull": [
                        {
                            "url": "https://github.com/holmanb/vmboot.git",
                            "playbook_names": ["ubuntu.yml", "watermark.yml"],
                        }
                    ],
                }
            },
            [
                "ansible:",
                '  install_method: "pip"',
                '  package_name: "ansible-core"',
                "  pull:",
                "    -",
                '      url: "https://github.com/holmanb/vmboot.git"',
                '      playbook_names: [ "ubuntu.yml", "watermark.yml" ]',
            ],
        ),
        (
            {
                "cloud_init_ansible": {
                    "run_user": "ansible",
                    "ansible_config": "/etc/ansible/ansible.cfg",
                    "package_name": "ansible-core",
                    "setup_controller": {
                        "repositories": [
                            {
                                "path": "/opt/playbooks",
                                "source": "git@github.com:example/playbooks.git",
                            }
                        ]
                    },
                }
            },
            [
                "ansible:",
                '  run_user: "ansible"',
                '  ansible_config: "/etc/ansible/ansible.cfg"',
                "  setup_controller:",
                "    repositories:",
                '      - path: "/opt/playbooks"',
                '        source: "git@github.com:example/playbooks.git"',
                '  package_name: "ansible-core"',
            ],
        ),
        (
            {
                "cloud_init_ansible": {
                    "package_name": "ansible-core",
                    "setup_controller": {
                        "run_ansible": [
                            {
                                "playbook_name": "site.yml",
                                "list_hosts": True,
                                "syntax_check": False,
                            }
                        ]
                    },
                    "galaxy": {"actions": [["install", "role1"], ["remove", "role2"]]},
                }
            },
            [
                "ansible:",
                "  setup_controller:",
                "    run_ansible:",
                '      - playbook_name: "site.yml"',
                "        list_hosts: true",
                "        syntax_check: false",
                "  galaxy:",
                "    actions:",
                "      -",
                '        - "install"',
                '        - "role1"',
                "      -",
                '        - "remove"',
                '        - "role2"',
                '  package_name: "ansible-core"',
            ],
        ),
    ],
)
def test_built_in_cloud_init_module_ansible(
    cobbler_api: CobblerAPI, input_meta: Dict[str, Any], expected_result: List[str]
):
    """
    Parametrized tests for the built-in Cloud-Init ansible snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-ansible"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    # Act
    result = cobbler_api.templar.render(
        target_template.content, input_meta, None, template_type="jinja"
    )

    # Assert
    if result:
        assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


@pytest.mark.parametrize(
    "input_meta,expected_result",
    [
        ({}, []),
        (
            {"cloud_init_apk_configure": {"preserve_repositories": True}},
            ["apk_repos:", "  preserve_repositories: true"],
        ),
        (
            {
                "cloud_init_apk_configure": {
                    "alpine_repo": {
                        "base_url": "https://mirror.example/alpine",
                        "community_enabled": True,
                        "testing_enabled": False,
                        "version": "v3.12",
                    }
                }
            },
            [
                "apk_repos:",
                "  alpine_repo:",
                "    base_url: https://mirror.example/alpine",
                "    community_enabled: true",
                "    testing_enabled: false",
                "    version: v3.12",
            ],
        ),
        (
            {
                "cloud_init_apk_configure": {
                    "local_repo_base_url": "https://local.example/alpine"
                }
            },
            ["apk_repos:", "  local_repo_base_url: https://local.example/alpine"],
        ),
    ],
)
def test_built_in_cloud_init_module_apk_repos(
    cobbler_api: CobblerAPI, input_meta: Dict[str, Any], expected_result: List[str]
):
    """
    Parametrized tests for the built-in Cloud-Init apk_repos snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-apk-repos"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    # Act
    result = cobbler_api.templar.render(
        target_template.content, input_meta, None, template_type="jinja"
    )

    # Assert
    if result:
        assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


@pytest.mark.parametrize(
    "input_meta,expected_result",
    [
        ({}, []),
        (
            {"cloud_init_apt_configure": {"preserve_sources_list": True}},
            ["apt:", "  preserve_sources_list: true"],
        ),
        (
            {"cloud_init_apt_configure": {"disable_suites": ["updates"]}},
            ["apt:", "  disable_suites:", "    - updates"],
        ),
        (
            {
                "cloud_init_apt_configure": {
                    "add_apt_repo_match": "^[\\w-]+:\\w",
                }
            },
            ["apt:", "  add_apt_repo_match: ^[\\w-]+:\\w"],
        ),
        (
            {
                "cloud_init_apt_configure": {
                    "debconf_selections": {"myconf": "pkg question type answer"}
                }
            },
            [
                "apt:",
                "  debconf_selections:",
                "    myconf: |",
                "      pkg question type answer",
            ],
        ),
        (
            {
                "cloud_init_apt_configure": {
                    "sources_list": "deb http://archive.ubuntu.com/ubuntu focal main"
                }
            },
            [
                "apt:",
                "  sources_list: |",
                "    deb http://archive.ubuntu.com/ubuntu focal main",
            ],
        ),
        (
            {
                "cloud_init_apt_configure": {
                    "conf": 'Acquire::http::Proxy "http://proxy:8080/";'
                }
            },
            ["apt:", "  conf: |", '    Acquire::http::Proxy "http://proxy:8080/";'],
        ),
        (
            {
                "cloud_init_apt_configure": {
                    "primary": [
                        {
                            "arches": ["amd64"],
                            "uri": "http://archive.ubuntu.com/ubuntu",
                            "keyid": "ABC123",
                        }
                    ]
                }
            },
            [
                "apt:",
                "  primary:",
                "    - arches:",
                "        - amd64",
                "      uri: http://archive.ubuntu.com/ubuntu",
                "      keyid: ABC123",
            ],
        ),
        (
            {
                "cloud_init_apt_configure": {
                    "security": [
                        {
                            "arches": ["amd64", "i386"],
                            "search": ["http://localmirror1", "http://localmirror2"],
                            "key": "KEYDATA",
                        }
                    ]
                }
            },
            [
                "apt:",
                "  security:",
                "    - arches:",
                "        - amd64",
                "        - i386",
                "      search:",
                "        - http://localmirror1",
                "        - http://localmirror2",
                "      key: KEYDATA",
            ],
        ),
        (
            {
                "cloud_init_apt_configure": {
                    "sources": {
                        "myrepo": {
                            "source": "deb http://example focal main",
                            "keyid": "ID123",
                            "filename": "myrepo.list",
                            "append": False,
                        }
                    }
                }
            },
            [
                "apt:",
                "  sources:",
                "    myrepo:",
                "      source: deb http://example focal main",
                "      keyid: ID123",
                "      filename: myrepo.list",
                "      append: false",
            ],
        ),
        (
            {
                "cloud_init_apt_configure": {
                    "preserve_sources_list": False,
                    "disable_suites": [
                        "$RELEASE-updates",
                        "backports",
                        "$RELEASE",
                        "mysuite",
                    ],
                    "primary": [
                        {
                            "arches": ["amd64", "i386", "default"],
                            "uri": "http://us.archive.ubuntu.com/ubuntu",
                            "search": [
                                "http://cool.but-sometimes-unreachable.com/ubuntu",
                                "http://us.archive.ubuntu.com/ubuntu",
                            ],
                            "search_dns": False,
                        },
                        {
                            "arches": ["s390x", "arm64"],
                            "uri": "http://archive-to-use-for-arm64.example.com/ubuntu",
                        },
                    ],
                    "security": [{"arches": ["default"], "search_dns": True}],
                    "sources_list": (
                        "deb $MIRROR $RELEASE main restricted\n"
                        "deb-src $MIRROR $RELEASE main restricted\n"
                        "deb $PRIMARY $RELEASE universe restricted\n"
                        "deb $SECURITY $RELEASE-security multiverse"
                    ),
                    "debconf_selections": {
                        "set1": "the-package the-package/some-flag boolean true"
                    },
                    "conf": (
                        "APT {\n"
                        "    Get {\n"
                        "        Assume-Yes 'true';\n"
                        "        Fix-Broken 'true';\n"
                        "    }\n"
                        "}"
                    ),
                    "proxy": "http://[[user][:pass]@]host[:port]/",
                    "http_proxy": "http://[[user][:pass]@]host[:port]/",
                    "ftp_proxy": "ftp://[[user][:pass]@]host[:port]/",
                    "https_proxy": "https://[[user][:pass]@]host[:port]/",
                    "sources": {
                        "source1": {
                            "keyid": "keyid",
                            "keyserver": "keyserverurl",
                            "source": "deb [signed-by=$KEY_FILE] http://<url>/ bionic main",
                        },
                        "source2": {"source": "ppa:<ppa-name>"},
                        "source3": {
                            "source": "deb $MIRROR $RELEASE multiverse",
                            "key": "------BEGIN PGP PUBLIC KEY BLOCK-------\n<key data>\n------END PGP PUBLIC KEY BLOCK-------",
                        },
                        "source4": {
                            "source": "deb $MIRROR $RELEASE multiverse",
                            "append": False,
                            "key": "------BEGIN PGP PUBLIC KEY BLOCK-------\n<key data>\n------END PGP PUBLIC KEY BLOCK-------",
                        },
                    },
                }
            },
            [
                "apt:",
                "  preserve_sources_list: false",
                "  disable_suites:",
                "    - $RELEASE-updates",
                "    - backports",
                "    - $RELEASE",
                "    - mysuite",
                "  primary:",
                "    - arches:",
                "        - amd64",
                "        - i386",
                "        - default",
                "      uri: http://us.archive.ubuntu.com/ubuntu",
                "      search:",
                "        - http://cool.but-sometimes-unreachable.com/ubuntu",
                "        - http://us.archive.ubuntu.com/ubuntu",
                "      search_dns: false",
                "    - arches:",
                "        - s390x",
                "        - arm64",
                "      uri: http://archive-to-use-for-arm64.example.com/ubuntu",
                "  security:",
                "    - arches:",
                "        - default",
                "      search_dns: true",
                "  debconf_selections:",
                "    set1: |",
                "      the-package the-package/some-flag boolean true",
                "  sources_list: |",
                "    deb $MIRROR $RELEASE main restricted",
                "    deb-src $MIRROR $RELEASE main restricted",
                "    deb $PRIMARY $RELEASE universe restricted",
                "    deb $SECURITY $RELEASE-security multiverse",
                "  conf: |",
                "    APT {",
                "        Get {",
                "            Assume-Yes 'true';",
                "            Fix-Broken 'true';",
                "        }",
                "    }",
                "  https_proxy: https://[[user][:pass]@]host[:port]/",
                "  http_proxy: http://[[user][:pass]@]host[:port]/",
                "  proxy: http://[[user][:pass]@]host[:port]/",
                "  ftp_proxy: ftp://[[user][:pass]@]host[:port]/",
                "  sources:",
                "    source1:",
                "      source: deb [signed-by=$KEY_FILE] http://<url>/ bionic main",
                "      keyid: keyid",
                "      keyserver: keyserverurl",
                "    source2:",
                "      source: ppa:<ppa-name>",
                "    source3:",
                "      source: deb $MIRROR $RELEASE multiverse",
                "      key: |",
                "        ------BEGIN PGP PUBLIC KEY BLOCK-------",
                "        <key data>",
                "        ------END PGP PUBLIC KEY BLOCK-------",
                "    source4:",
                "      source: deb $MIRROR $RELEASE multiverse",
                "      key: |",
                "        ------BEGIN PGP PUBLIC KEY BLOCK-------",
                "        <key data>",
                "        ------END PGP PUBLIC KEY BLOCK-------",
                "      append: false",
            ],
        ),
        (
            {
                "cloud_init_apt_configure": {
                    "sources_list": "Types: deb\nURIs: http://archive.ubuntu.com/ubuntu/\nSuites: $RELEASE\nComponents: main"
                }
            },
            [
                "apt:",
                "  sources_list: |",
                "    Types: deb",
                "    URIs: http://archive.ubuntu.com/ubuntu/",
                "    Suites: $RELEASE",
                "    Components: main",
            ],
        ),
    ],
)
def test_built_in_cloud_init_module_apt(
    cobbler_api: CobblerAPI, input_meta: Dict[str, Any], expected_result: List[str]
):
    """
    Parametrized tests for the built-in Cloud-Init apt snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-apt"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    # Act
    result = cobbler_api.templar.render(
        target_template.content, input_meta, None, template_type="jinja"
    )

    # Assert
    if result:
        assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


def test_built_in_cloud_init_module_apt_pipelining(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init addons XML snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-apt-pipelining"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {"cloud_init_apt_pipelining": True}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == "apt_pipelining: True"


def test_built_in_cloud_init_module_bootcmd(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init addons XML snippet.
    """
    # Arrange
    expected_result = [
        "bootcmd:",
        '  - "test1"',
        '  - ["test2", "test3"]',
        '  - "test4"',
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-bootcmd"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {
        "cloud_init_bootcmd": ["test1", ["test2", "test3"], "test4"]
    }

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


@pytest.mark.parametrize(
    "input_meta,expected_result",
    [({}, []), ({"cloud_init_byobu": "test"}, ["byobu_by_default: test"])],
)
def test_built_in_cloud_init_module_byobu_by_default(
    cobbler_api: CobblerAPI, input_meta: Dict[str, Any], expected_result: List[str]
):
    """
    Test to verify the rendering of the built-in Cloud-Init addons XML snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-byobu"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    # Act
    result = cobbler_api.templar.render(
        target_template.content, input_meta, None, template_type="jinja"
    )

    # Assert
    if result:
        assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


@pytest.mark.parametrize(
    "input_meta,expected_result",
    [
        ({}, []),
        (
            {"cloud_init_ca_certs": {"remove_defaults": True}},
            ["ca_certs:", "  remove_defaults: true"],
        ),
        (
            {"cloud_init_ca_certs": {"trusted": ["cert1", "cert2"]}},
            ["ca_certs:", "  trusted:", "    - cert1", "    - cert2"],
        ),
        (
            {
                "cloud_init_ca_certs": {
                    "trusted": [
                        "cert1",
                        "-----BEGIN CERTIFICATE-----\nYOUR-ORGS-TRUSTED-CA-CERT-HERE\n-----END CERTIFICATE-----",
                    ]
                }
            },
            [
                "ca_certs:",
                "  trusted:",
                "    - cert1",
                "    - |",
                "      -----BEGIN CERTIFICATE-----",
                "      YOUR-ORGS-TRUSTED-CA-CERT-HERE",
                "      -----END CERTIFICATE-----",
            ],
        ),
    ],
)
def test_built_in_cloud_init_module_ca_certs(
    cobbler_api: CobblerAPI, input_meta: Dict[str, Any], expected_result: List[str]
):
    """
    Test to verify the rendering of the built-in Cloud-Init addons XML snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-ca-certs"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    # Act
    result = cobbler_api.templar.render(
        target_template.content, input_meta, None, template_type="jinja"
    )

    # Assert
    if result:
        assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


@pytest.mark.parametrize(
    "input_meta,expected_result",
    [
        ({}, []),
        (
            {"cloud_init_chef": {"server_url": "https://chef.example"}},
            ["chef:", "  server_url: https://chef.example"],
        ),
        (
            {"cloud_init_chef": {"directories": ["/etc/chef", "/var/log/chef"]}},
            ["chef:", "  directories:", "    - /etc/chef", "    - /var/log/chef"],
        ),
        (
            {"cloud_init_chef": {"initial_attributes": "apache:\n  keepalive: true"}},
            ["chef:", "  initial_attributes:", "    apache:", "      keepalive: true"],
        ),
        (
            {
                "cloud_init_chef": {
                    "directories": ["/etc/chef", "/var/log/chef"],
                    "encrypted_data_bag_secret": "/etc/chef/encrypted_data_bag_secret",
                    "environment": "_default",
                    "initial_attributes": "apache:\n  keepalive: false\n  prefork: {maxclients: 100}",
                    "install_type": "omnibus",
                    "log_level": ":auto",
                    "omnibus_url_retries": 2,
                    "run_list": ["'recipe[apache2]'", "'role[db]'"],
                    "server_url": "https://chef.yourorg.com:4000",
                    "ssl_verify_mode": ":verify_peer",
                    "validation_cert": "system",
                    "validation_name": "yourorg-validator",
                }
            },
            [
                "chef:",
                "  directories:",
                "    - /etc/chef",
                "    - /var/log/chef",
                "  validation_cert: system",
                "  encrypted_data_bag_secret: /etc/chef/encrypted_data_bag_secret",
                "  environment: _default",
                "  log_level: :auto",
                "  omnibus_url_retries: 2",
                "  server_url: https://chef.yourorg.com:4000",
                "  ssl_verify_mode: :verify_peer",
                "  validation_name: yourorg-validator",
                "  initial_attributes:",
                "    apache:",
                "      keepalive: false",
                "      prefork: {maxclients: 100}",
                "  install_type: omnibus",
                "  run_list:",
                "    - 'recipe[apache2]'",
                "    - 'role[db]'",
            ],
        ),
    ],
)
def test_built_in_cloud_init_module_chef(
    cobbler_api: CobblerAPI, input_meta: Dict[str, Any], expected_result: List[str]
):
    """
    Parametrized tests for the built-in Cloud-Init chef snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-chef"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    # Act
    result = cobbler_api.templar.render(
        target_template.content, input_meta, None, template_type="jinja"
    )

    # Assert
    if result:
        assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


def test_built_in_cloud_init_module_disable_ec2_metadata(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init addons XML snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-disable-ec2-metadata"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {"cloud_init_disable_ec2_metadata": False}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == "disable_ec2_metadata: False"


@pytest.mark.parametrize(
    "input_meta,expected_result",
    [
        ({}, []),
        (
            {"cloud_init_disk_setup": {"device_aliases": {"my_alias": "/dev/sdd"}}},
            ["device_aliases:", "  my_alias: /dev/sdd"],
        ),
        (
            {
                "cloud_init_disk_setup": {
                    "disk_setup": {
                        "/dev/sdd": {
                            "table_type": "mbr",
                            "overwrite": True,
                            "layout": True,
                        }
                    }
                }
            },
            [
                "disk_setup:",
                "  /dev/sdd:",
                "    table_type: mbr",
                "    overwrite: true",
                "    layout: true",
            ],
        ),
        (
            {
                "cloud_init_disk_setup": {
                    "disk_setup": {
                        "my_alias": {
                            "table_type": "gpt",
                            "overwrite": True,
                            "layout": [[100, 82]],
                        }
                    }
                }
            },
            [
                "disk_setup:",
                "  my_alias:",
                "    table_type: gpt",
                "    overwrite: true",
                "    layout:",
                "      - [100, 82]",
            ],
        ),
        (
            {
                "cloud_init_disk_setup": {
                    "fs_setup": [
                        {
                            "label": "fs1",
                            "filesystem": "ext4",
                            "device": "my_alias.1",
                            "partition": 1,
                            "overwrite": True,
                            "replace_fs": False,
                        }
                    ]
                }
            },
            [
                "fs_setup:",
                "  -",
                "    label: fs1",
                "    filesystem: ext4",
                "    device: my_alias.1",
                "    partition: 1",
                "    overwrite: true",
                "    replace_fs: false",
            ],
        ),
        (
            {
                "cloud_init_disk_setup": {
                    "device_aliases": {"my_alias": "/dev/sdb", "swap_disk": "/dev/sdc"},
                    "disk_setup": {
                        "/dev/sdd": {
                            "layout": True,
                            "overwrite": True,
                            "table_type": "mbr",
                        },
                        "my_alias": {
                            "layout": [50, 50],
                            "overwrite": True,
                            "table_type": "gpt",
                        },
                        "swap_disk": {
                            "layout": [[100, 82]],
                            "overwrite": True,
                            "table_type": "gpt",
                        },
                    },
                    "fs_setup": [
                        {
                            "cmd": "mkfs -t %(filesystem)s -L %(label)s %(device)s",
                            "device": "my_alias.1",
                            "filesystem": "ext4",
                            "label": "fs1",
                        },
                        {"device": "my_alias.2", "filesystem": "ext4", "label": "fs2"},
                        {
                            "device": "swap_disk.1",
                            "filesystem": "swap",
                            "label": "swap",
                        },
                        {"device": "/dev/sdd1", "filesystem": "ext4", "label": "fs3"},
                    ],
                }
            },
            [
                "device_aliases:",
                "  my_alias: /dev/sdb",
                "  swap_disk: /dev/sdc",
                "disk_setup:",
                "  /dev/sdd:",
                "    table_type: mbr",
                "    overwrite: true",
                "    layout: true",
                "  my_alias:",
                "    table_type: gpt",
                "    overwrite: true",
                "    layout:",
                "      - 50",
                "      - 50",
                "  swap_disk:",
                "    table_type: gpt",
                "    overwrite: true",
                "    layout:",
                "      - [100, 82]",
                "fs_setup:",
                "  -",
                "    label: fs1",
                "    filesystem: ext4",
                "    device: my_alias.1",
                "    cmd: mkfs -t %(filesystem)s -L %(label)s %(device)s",
                "  -",
                "    label: fs2",
                "    filesystem: ext4",
                "    device: my_alias.2",
                "  -",
                "    label: swap",
                "    filesystem: swap",
                "    device: swap_disk.1",
                "  -",
                "    label: fs3",
                "    filesystem: ext4",
                "    device: /dev/sdd1",
            ],
        ),
    ],
)
def test_built_in_cloud_init_module_disk_setup(
    cobbler_api: CobblerAPI, input_meta: Dict[str, Any], expected_result: List[str]
):
    """
    Test to verify the rendering of the built-in Cloud-Init disk_setup snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-disk-setup"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    # Act
    result = cobbler_api.templar.render(
        target_template.content, input_meta, None, template_type="jinja"
    )

    # Assert
    if result:
        assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


def test_built_in_cloud_init_module_fan(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init addons XML snippet.
    """
    # Arrange
    expected_result = [
        "fan:",
        "  config: |",
        "    testline",
        '  config_path: "/etc/network_fan"',
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-fan"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {
        "cloud_init_fan_config": "testline",
        "cloud_init_fan_config_path": "/etc/network_fan",
    }

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


def test_built_in_cloud_init_module_final_message(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init addons XML snippet.
    """
    # Arrange
    expected_result = [
        "final_message: |",
        "  Testmessage",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-final-message"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {"cloud_init_final_message": "Testmessage"}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


@pytest.mark.parametrize(
    "input_meta,expected_result",
    [
        ({}, []),
        (
            {
                "cloud_init_growpart_mode": "auto",
            },
            [
                "growpart:",
                '  mode: "auto"',
            ],
        ),
        (
            {
                "cloud_init_growpart_devices": ["testdevice"],
            },
            [
                "growpart:",
                "  devices:",
                '    - "testdevice"',
            ],
        ),
        (
            {
                "cloud_init_growpart_ignore_growroot_disabled": True,
            },
            [
                "growpart:",
                "  ignore_growroot_disabled: true",
            ],
        ),
        (
            {
                "cloud_init_growpart_mode": "auto",
                "cloud_init_growpart_devices": ["testdevice"],
                "cloud_init_growpart_ignore_growroot_disabled": True,
            },
            [
                "growpart:",
                '  mode: "auto"',
                "  devices:",
                '    - "testdevice"',
                "  ignore_growroot_disabled: true",
            ],
        ),
        (
            {
                "cloud_init_growpart_mode": "auto",
                "cloud_init_growpart_devices": ["testdevice1", "testdevice2"],
                "cloud_init_growpart_ignore_growroot_disabled": False,
            },
            [
                "growpart:",
                '  mode: "auto"',
                "  devices:",
                '    - "testdevice1"',
                '    - "testdevice2"',
                "  ignore_growroot_disabled: false",
            ],
        ),
    ],
)
def test_built_in_cloud_init_module_growpart(
    cobbler_api: CobblerAPI, input_meta: Dict[str, Any], expected_result: List[str]
):
    """
    Test to verify the rendering of the built-in Cloud-Init addons XML snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-growpart"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    # Act
    result = cobbler_api.templar.render(
        target_template.content, input_meta, None, template_type="jinja"
    )

    # Assert
    if result:
        assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


def test_built_in_cloud_init_module_grub_dpkg(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init addons XML snippet.
    """
    # Arrange
    expected_result = [
        "grub_dpkg:",
        "  enabled: True",
        '  grub-pc/install_devices: "/dev/sda"',
        "  grub-pc/install_devices_empty: False",
        '  grub-efi/install_devices: "/dev/sda"',
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-grub-dpkg"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {
        "cloud_init_grub_dpkg_enabled": True,
        "cloud_init_grub_dpkg_bios_device": "/dev/sda",
        "cloud_init_grub_dpkg_devices_bios_empty": False,
        "cloud_init_grub_dpkg_efi_device": "/dev/sda",
    }

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


def test_built_in_cloud_init_module_hotplug(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init addons XML snippet.
    """
    # Arrange
    expected_result = [
        "updates:",
        "  network:",
        "    when:",
        '      - "boot"',
        '      - "hotplug"',
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-hotplug"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {"cloud_init_hotplug_network_when": ["boot", "hotplug"]}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


def test_built_in_cloud_init_module_keyboard(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init addons XML snippet.
    """
    # Arrange
    expected_result = [
        "keyboard:",
        '  layout: "de"',
        '  model: "pc105"',
        '  variant: "nodeadkeys"',
        '  options: "compose:rwin"',
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-keyboard"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {
        "cloud_init_keyboard_layout": "de",
        "cloud_init_keyboard_model": "pc105",
        "cloud_init_keyboard_variant": "nodeadkeys",
        "cloud_init_keyboard_options": "compose:rwin",
    }

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


def test_built_in_cloud_init_module_keys_to_console(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init addons XML snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-keys-to-console"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_landscape(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init landscape snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-landscape"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_locale(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init locale snippet.
    """
    # Arrange
    expected_result = ['locale: "test1"', 'locale_configfile: "test2"']
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-locale"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {
        "cloud_init_locale_locale": "test1",
        "cloud_init_locale_configfile": "test2",
    }

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


def test_built_in_cloud_init_module_lxd(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init lxd snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-lxd"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_mcollective(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init mcollective snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-mcollective"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


@pytest.mark.parametrize(
    "input_meta,expected_result",
    [
        ({}, []),
        (
            {
                "cloud_init_mounts": {
                    "mounts": [
                        ["/dev/ephemeral0", "/mnt", "auto", "defaults,noexec"],
                        ["sdc", "/opt/data"],
                        [
                            "xvdh",
                            "/opt/data",
                            "auto",
                            "defaults,nofail",
                            "0",
                            "0",
                        ],
                    ],
                    "mount_default_fields": [
                        None,
                        None,
                        "auto",
                        "defaults,nofail",
                        "0",
                        "2",
                    ],
                    "swap": {
                        "filename": "/my/swapfile",
                        "size": "auto",
                        "maxsize": 10485760,
                    },
                }
            },
            [
                "mounts:",
                '  - [ "/dev/ephemeral0", "/mnt", "auto", "defaults,noexec" ]',
                '  - [ "sdc", "/opt/data" ]',
                '  - [ "xvdh", "/opt/data", "auto", "defaults,nofail", "0", "0" ]',
                'mount_default_fields: [ None, None, "auto", "defaults,nofail", "0", "2" ]',
                "swap:",
                "  filename: /my/swapfile",
                "  size: auto",
                "  maxsize: 10485760",
            ],
        ),
        (
            {
                "cloud_init_mounts": {
                    "mounts": [["onlyspec"], ["sdc", "/opt/data"]],
                    "mount_default_fields": [
                        None,
                        None,
                        "auto",
                        "defaults,nofail",
                        "0",
                        "2",
                    ],
                }
            },
            [
                "mounts:",
                '  - [ "sdc", "/opt/data" ]',
                'mount_default_fields: [ None, None, "auto", "defaults,nofail", "0", "2" ]',
            ],
        ),
    ],
)
def test_built_in_cloud_init_module_mounts(
    cobbler_api: CobblerAPI, input_meta: Dict[str, Any], expected_result: List[str]
):
    """
    Test to verify the rendering of the built-in Cloud-Init mounts snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-mounts"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    # Act
    result = cobbler_api.templar.render(
        target_template.content, input_meta, None, template_type="jinja"
    )

    # Assert
    if result:
        assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


@pytest.mark.parametrize(
    "input_meta,expected_result",
    [
        ({}, []),
        (
            {
                "cloud_init_network": {
                    "config": [{"type": "nameserver", "address": "8.8.8.8"}]
                }
            },
            [
                "network:",
                "  version: 1",
                "  config:",
                "    - type: nameserver",
                "      address:",
                "        - 8.8.8.8",
            ],
        ),
        (
            {
                "cloud_init_network": {
                    "config": [
                        {
                            "type": "nameserver",
                            "address": ["8.8.8.8", "8.8.4.4"],
                            "search": ["example.org"],
                            "interface": "eth0",
                        }
                    ]
                }
            },
            [
                "network:",
                "  version: 1",
                "  config:",
                "    - type: nameserver",
                "      address:",
                "        - 8.8.8.8",
                "        - 8.8.4.4",
                "      search:",
                "        - example.org",
                "      interface: eth0",
            ],
        ),
        (
            {
                "cloud_init_network": {
                    "config": [
                        {
                            "type": "route",
                            "network": "0.0.0.0/0",
                            "gateway": "192.0.2.1",
                        }
                    ]
                }
            },
            [
                "network:",
                "  version: 1",
                "  config:",
                "    - type: route",
                "      network: 0.0.0.0/0",
                "      gateway: 192.0.2.1",
            ],
        ),
        (
            {
                "cloud_init_network": {
                    "config": [
                        {
                            "type": "route",
                            "destination": "10.0.0.0/8",
                            "netmask": "255.0.0.0",
                            "gateway": "10.0.0.1",
                            "metric": 100,
                        }
                    ]
                }
            },
            [
                "network:",
                "  version: 1",
                "  config:",
                "    - type: route",
                "      destination: 10.0.0.0/8",
                "      netmask: 255.0.0.0",
                "      gateway: 10.0.0.1",
                "      metric: 100",
            ],
        ),
        (
            {
                "cloud_init_network": {
                    "config": [
                        {
                            "type": "physical",
                            "name": "eth0",
                            "mac_address": "aa:bb:cc:dd:ee:ff",
                            "mtu": 1500,
                            "accept-ra": True,
                            "keep_configuration": True,
                            "subnets": [
                                {
                                    "type": "static",
                                    "address": "192.0.2.5/24",
                                    "gateway": "192.0.2.1",
                                }
                            ],
                        }
                    ]
                }
            },
            [
                "network:",
                "  version: 1",
                "  config:",
                "    - type: physical",
                "      name: eth0",
                "      mac_address: aa:bb:cc:dd:ee:ff",
                "      mtu: 1500",
                "      accept-ra: true",
                "      keep_configuration: true",
                "      subnets:",
                "        - type: static",
                "          address: 192.0.2.5/24",
                "          gateway: 192.0.2.1",
            ],
        ),
        (
            {
                "cloud_init_network": {
                    "config": [
                        {
                            "type": "bond",
                            "name": "bond0",
                            "bond_interfaces": ["eth0", "eth1"],
                            "params": {"bond-miimon": 100, "bond-mode": "balance-rr"},
                        }
                    ]
                }
            },
            [
                "network:",
                "  version: 1",
                "  config:",
                "    - type: bond",
                "      name: bond0",
                "      bond_interfaces:",
                "        - eth0",
                "        - eth1",
                "      params:",
                "        bond-miimon: 100",
                "        bond-mode: balance-rr",
            ],
        ),
        (
            {
                "cloud_init_network": {
                    "config": [
                        {
                            "type": "bridge",
                            "name": "br0",
                            "bridge_interfaces": ["eth0"],
                            "params": {"bridge_fd": 30, "bridge_maxwait": 5},
                        }
                    ]
                }
            },
            [
                "network:",
                "  version: 1",
                "  config:",
                "    - type: bridge",
                "      name: br0",
                "      bridge_interfaces:",
                "        - eth0",
                "      params:",
                "        bridge_fd: 30",
                "        bridge_maxwait: 5",
            ],
        ),
        (
            {
                "cloud_init_network": {
                    "config": [
                        {
                            "type": "vlan",
                            "name": "v100",
                            "vlan_link": "eth0",
                            "vlan_id": 100,
                            "subnets": [{"type": "static", "address": "192.0.2.10/24"}],
                        }
                    ]
                }
            },
            [
                "network:",
                "  version: 1",
                "  config:",
                "    - type: vlan",
                "      name: v100",
                "      vlan_link: eth0",
                "      vlan_id: 100",
                "      subnets:",
                "        - type: static",
                "          address: 192.0.2.10/24",
            ],
        ),
        (
            {
                "cloud_init_network": {
                    "config": [
                        {
                            "type": "physical",
                            "name": "eth1",
                            "subnets": [
                                {
                                    "type": "static",
                                    "address": "10.0.0.5/24",
                                    "dns_nameservers": ["8.8.8.8"],
                                    "dns_search": ["example.com"],
                                    "routes": [
                                        {
                                            "destination": "10.0.1.0/24",
                                            "gateway": "10.0.0.1",
                                            "metric": 10,
                                        }
                                    ],
                                    "ipv4": True,
                                }
                            ],
                        }
                    ]
                }
            },
            [
                "network:",
                "  version: 1",
                "  config:",
                "    - type: physical",
                "      name: eth1",
                "      subnets:",
                "        - type: static",
                "          address: 10.0.0.5/24",
                "          dns_nameservers:",
                "            - 8.8.8.8",
                "          dns_search:",
                "            - example.com",
                "          routes:",
                "            - ",
                "              destination: 10.0.1.0/24",
                "              gateway: 10.0.0.1",
                "              metric: 10",
                "          ipv4: true",
            ],
        ),
    ],
)
def test_built_in_cloud_init_module_network_v1(
    cobbler_api: CobblerAPI, input_meta: Dict[str, Any], expected_result: List[str]
):
    """
    Parametrized tests for the built-in Cloud-Init network v1 snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-network-v1"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    # Act
    result = cobbler_api.templar.render(
        target_template.content, input_meta, None, template_type="jinja"
    )

    # Assert
    if result:
        assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


@pytest.mark.parametrize(
    "input_meta,expected_result",
    [
        ({}, []),
        (
            {"cloud_init_network_v2": {"renderer": "networkd"}},
            ["network:", "  version: 2", "  renderer: networkd"],
        ),
        (
            {"cloud_init_network_v2": {"ethernets": {"eth0": {"dhcp4": True}}}},
            [
                "network:",
                "  version: 2",
                "  ethernets:",
                "    eth0:",
                "      dhcp4: true",
            ],
        ),
        (
            {
                "cloud_init_network_v2": {
                    "ethernets": {
                        "eth0": {
                            "addresses": ["192.0.2.5/24"],
                            "gateway4": "192.0.2.1",
                            "nameservers": {"addresses": ["8.8.8.8"]},
                        }
                    }
                }
            },
            [
                "network:",
                "  version: 2",
                "  ethernets:",
                "    eth0:",
                "      addresses:",
                "        - 192.0.2.5/24",
                "      gateway4: 192.0.2.1",
                "      nameservers:",
                "        addresses:",
                "          - 8.8.8.8",
            ],
        ),
        (
            {
                "cloud_init_network_v2": {
                    "ethernets": {
                        "eth0": {
                            "routes": [
                                {"to": "0.0.0.0/0", "via": "192.0.2.1", "metric": 100}
                            ]
                        }
                    }
                }
            },
            [
                "network:",
                "  version: 2",
                "  ethernets:",
                "    eth0:",
                "      routes:",
                "        - to: 0.0.0.0/0",
                "          via: 192.0.2.1",
                "          metric: 100",
            ],
        ),
        (
            {
                "cloud_init_network_v2": {
                    "ethernets": {
                        "eth0": {
                            "match": {"macaddress": "aa:bb:cc:dd:ee:ff"},
                            "set-name": "net0",
                        }
                    }
                }
            },
            [
                "network:",
                "  version: 2",
                "  ethernets:",
                "    eth0:",
                "      match:",
                "        macaddress: aa:bb:cc:dd:ee:ff",
                "      set-name: net0",
            ],
        ),
        (
            {
                "cloud_init_network_v2": {
                    "bonds": {
                        "bond0": {
                            "interfaces": ["eth0", "eth1"],
                            "parameters": {
                                "mode": "active-backup",
                                "mii-monitor-interval": 100,
                            },
                        }
                    }
                }
            },
            [
                "network:",
                "  version: 2",
                "  bonds:",
                "    bond0:",
                "      interfaces:",
                "        - eth0",
                "        - eth1",
                "      parameters:",
                "        mode: active-backup",
                "        mii-monitor-interval: 100",
            ],
        ),
        (
            {
                "cloud_init_network_v2": {
                    "bridges": {
                        "br0": {
                            "interfaces": ["eth0"],
                            "parameters": {"stp": True, "forward-delay": 30},
                        }
                    }
                }
            },
            [
                "network:",
                "  version: 2",
                "  bridges:",
                "    br0:",
                "      interfaces:",
                "        - eth0",
                "      parameters:",
                "        stp: true",
                "        forward-delay: 30",
            ],
        ),
        (
            {
                "cloud_init_network_v2": {
                    "vlans": {
                        "v100": {
                            "id": 100,
                            "link": "eth0",
                            "addresses": ["192.0.2.10/24"],
                        }
                    }
                }
            },
            [
                "network:",
                "  version: 2",
                "  vlans:",
                "    v100:",
                "      id: 100",
                "      link: eth0",
                "      addresses:",
                "        - 192.0.2.10/24",
            ],
        ),
        (
            {
                "cloud_init_network_v2": {
                    "renderer": "NetworkManager",
                    "ethernets": {
                        "eth0": {
                            "dhcp6": "yes",
                            "nameservers": {
                                "search": ["example.org"],
                                "addresses": ["2001:db8::1"],
                            },
                        }
                    },
                }
            },
            [
                "network:",
                "  version: 2",
                "  renderer: NetworkManager",
                "  ethernets:",
                "    eth0:",
                "      dhcp6: yes",
                "      nameservers:",
                "        search:",
                "          - example.org",
                "        addresses:",
                "          - 2001:db8::1",
            ],
        ),
    ],
)
def test_built_in_cloud_init_module_network_v2(
    cobbler_api: CobblerAPI, input_meta: Dict[str, Any], expected_result: List[str]
):
    """
    Parametrized tests for the built-in Cloud-Init network v2 snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-network-v2"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    # Act
    result = cobbler_api.templar.render(
        target_template.content, input_meta, None, template_type="jinja"
    )

    # Assert
    if result:
        assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


@pytest.mark.parametrize(
    "input_meta,expected_result",
    [
        ({}, []),
        ({"cloud_init_ntp": {"enabled": True}}, ["ntp:", "  enabled: true"]),
        (
            {"cloud_init_ntp": {"servers": ["0.pool.ntp.org", "1.pool.ntp.org"]}},
            [
                "ntp:",
                "  servers:",
                "    - 0.pool.ntp.org",
                "    - 1.pool.ntp.org",
            ],
        ),
        (
            {
                "cloud_init_ntp": {
                    "pools": ["0.pool.ntp.org"],
                    "config": {
                        "service_name": "ntp",
                        "packages": ["ntp"],
                        "template": "driftfile /var/lib/ntp/ntp.drift\nserver 0.pool.ntp.org",
                    },
                }
            },
            [
                "ntp:",
                "  pools:",
                "    - 0.pool.ntp.org",
                "  config:",
                "    packages:",
                "      - ntp",
                "    service_name: ntp",
                "    template: |",
                "      driftfile /var/lib/ntp/ntp.drift",
                "      server 0.pool.ntp.org",
            ],
        ),
    ],
)
def test_built_in_cloud_init_module_ntp(
    cobbler_api: CobblerAPI, input_meta: Dict[str, Any], expected_result: List[str]
):
    """
    Test to verify the rendering of the built-in Cloud-Init ntp snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-ntp"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    # Act
    result = cobbler_api.templar.render(
        target_template.content, input_meta, None, template_type="jinja"
    )

    # Assert
    if result:
        assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


def test_built_in_cloud_init_module_packages(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init addons XML snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-packages"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_phone_home(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init phone home snippet.
    """
    # Arrange
    expected_result = [
        "phone_home:",
        '  url: "https://example.org"',
        '  post: "all"',
        "  tries: 0",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-phone-home"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {
        "cloud_init_phone_home_url": "https://example.org",
        "cloud_init_phone_home_post": "all",
        "cloud_init_phone_home_tries": 0,
    }

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


@pytest.mark.parametrize(
    "input_meta,expected_result",
    [
        ({}, []),
        ({"cloud_init_power_state": {"delay": 15}}, ["power_state:", "  delay: 15"]),
        (
            {"cloud_init_power_state": {"mode": "halt"}},
            ["power_state:", "  mode: halt"],
        ),
        (
            {"cloud_init_power_state": {"message": "Shutting down"}},
            ["power_state:", "  message: Shutting down"],
        ),
        (
            {"cloud_init_power_state": {"timeout": 30}},
            ["power_state:", "  timeout: 30"],
        ),
        (
            {"cloud_init_power_state": {"condition": ["ready", "ok"]}},
            [
                "power_state:",
                "  condition:",
                '    - "ready"',
                '    - "ok"',
            ],
        ),
        (
            {"cloud_init_power_state": {"condition": True}},
            ["power_state:", "  condition: true"],
        ),
        (
            {"cloud_init_power_state": {"condition": "on_event"}},
            ["power_state:", "  condition: on_event"],
        ),
        (
            {
                "cloud_init_power_state": {
                    "delay": 5,
                    "mode": "reboot",
                    "message": "Going down",
                    "timeout": 60,
                    "condition": ["a", 2],
                }
            },
            [
                "power_state:",
                "  delay: 5",
                "  mode: reboot",
                "  message: Going down",
                "  timeout: 60",
                "  condition:",
                '    - "a"',
                "    - 2",
            ],
        ),
    ],
)
def test_built_in_cloud_init_module_power_state_change(
    cobbler_api: CobblerAPI, input_meta: Dict[str, Any], expected_result: List[str]
):
    """
    Test to verify the rendering of the built-in Cloud-Init power state change snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-power-state-change"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    # Act
    result = cobbler_api.templar.render(
        target_template.content, input_meta, None, template_type="jinja"
    )

    # Assert
    if result:
        assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


def test_built_in_cloud_init_module_puppet(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init addons XML snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-puppet"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_redhat_subscription(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init RedHat subscription snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-redhat-subscription"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_resizefs(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init resizefs snippet.
    """
    # Arrange
    expected_result = "resize_rootfs: True"
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-resizefs"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {"cloud_init_resizefs": True}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == expected_result


def test_built_in_cloud_init_module_resolveconf(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init resolveconf snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-resolveconf"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_rpi(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init Raspberry Pi snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-rpi"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_rsyslog(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init rsyslog snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-rsyslog"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_runcmd(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init runcmd snippet.
    """
    # Arrange
    expected_result = [
        "runcmd:",
        '  - ["ls", "-l"]',
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-runcmd"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {"cloud_init_runcmd": [["ls", "-l"]]}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


def test_built_in_cloud_init_module_salt_minion(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init Salt Minion snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-salt-minion"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""



def test_built_in_cloud_init_module_seed_random(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init seed random snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-seed-random"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


@pytest.mark.parametrize(
    "input_meta,expected_result",
    [
        ({}, []),
        ({"cloud_init_set_hostname": {}}, []),
        (
            {"cloud_init_set_hostname": {"preserve_hostname": True}},
            ["preserve_hostname: true"],
        ),
        (
            {
                "cloud_init_set_hostname": {
                    "preserve_hostname": True,
                    "hostname": "example-host",
                }
            },
            ["preserve_hostname: true", 'hostname: "example-host"'],
        ),
        (
            {
                "cloud_init_set_hostname": {
                    "preserve_hostname": True,
                    "hostname": "example-host",
                    "fqdn": "example.org",
                }
            },
            [
                "preserve_hostname: true",
                'hostname: "example-host"',
                'fqdn: "example.org"',
            ],
        ),
        (
            {
                "cloud_init_set_hostname": {
                    "preserve_hostname": True,
                    "create_hostname_file": True,
                }
            },
            ["preserve_hostname: true", "create_hostname_file: true"],
        ),
    ],
)
def test_built_in_cloud_init_module_set_hostname(
    cobbler_api: CobblerAPI, input_meta: Dict[str, Any], expected_result: List[str]
):
    """
    Test to verify the rendering of the built-in Cloud-Init set hostname snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-set-hostname"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    # Act
    result = cobbler_api.templar.render(
        target_template.content, input_meta, None, template_type="jinja"
    )

    # Assert
    if result:
        assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


@pytest.mark.parametrize(
    "input_meta,expected_result",
    [
        ({}, []),
        ({"cloud_init_set_passwords": {"ssh_pwauth": False}}, ["ssh_pwauth: false"]),
        ({"cloud_init_set_passwords": {"ssh_pwauth": True}}, ["ssh_pwauth: true"]),
        (
            {
                "cloud_init_set_passwords": {
                    "ssh_pwauth": True,
                    "chpasswd": {"expire": False},
                }
            },
            ["ssh_pwauth: true", "chpasswd:", "  expire: false"],
        ),
        (
            {
                "cloud_init_set_passwords": {
                    "ssh_pwauth": True,
                    "chpasswd": {
                        "expire": False,
                        "users": [{"name": "SchoolGuy", "type": "RANDOM"}],
                    },
                }
            },
            [
                "ssh_pwauth: true",
                "chpasswd:",
                "  expire: false",
                "  users:",
                '  - name: "SchoolGuy"',
                '    type: "RANDOM"',
            ],
        ),
    ],
)
def test_built_in_cloud_init_module_set_passwords(
    cobbler_api: CobblerAPI, input_meta: Dict[str, Any], expected_result: List[str]
):
    """
    Test to verify the rendering of the built-in Cloud-Init set passwords snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-set-passwords"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    # Act
    result = cobbler_api.templar.render(
        target_template.content, input_meta, None, template_type="jinja"
    )

    # Assert
    print(result)
    if result:
        assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


def test_built_in_cloud_init_module_snap(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init snap snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-snap"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_spacewalk(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init Spacewalk snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-spacewalk"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_ssh_authkey_fingerprints(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init SSH authkey fingerprints snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-ssh-authkey-fingerprints"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_ssh_import_id(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init SSH import ID snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-ssh-import-id"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_ssh(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init SSH snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-ssh"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_timezone(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init timezone snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-timezone"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {"cloud_init_timezone": "America/New_York"}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    if result:
        assert yaml.safe_load(result)
    assert result == "timezone: America/New_York"


def test_built_in_cloud_init_module_ubuntu_autoinstall(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init Ubuntu autoinstall snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-ubuntu-autoinstall"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_ubuntu_drivers(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init Ubuntu drivers snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-ubuntu-drivers"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_ubuntu_pro(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init Ubuntu Pro snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-ubuntu-pro"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


def test_built_in_cloud_init_module_update_etc_hosts(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init update /etc/hosts snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-update-etc-hosts"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


@pytest.mark.parametrize(
    "input_meta,expected_result",
    [
        ({}, []),
        ({"cloud_init_update_hostname": {}}, []),
        (
            {"cloud_init_update_hostname": {"preserve_hostname": True}},
            ["preserve_hostname: true"],
        ),
    ],
)
def test_built_in_cloud_init_module_update_hostname(
    cobbler_api: CobblerAPI, input_meta: Dict[str, Any], expected_result: List[str]
):
    """
    Test to verify the rendering of the built-in Cloud-Init update hostname snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-update-hostname"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    # Act
    result = cobbler_api.templar.render(
        target_template.content, input_meta, None, template_type="jinja"
    )

    # Assert
    if result:
        assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


@pytest.mark.parametrize(
    "input_meta,expected_result",
    [
        ({}, []),
        (
            {"cloud_init_users_groups": {"groups": {"wheel": ["root", "admin"]}}},
            [
                "groups:",
                "  wheel:",
                "    - root",
                "    - admin",
            ],
        ),
        (
            {"cloud_init_users_groups": {"groups": ["wheel", "staff"]}},
            [
                "groups:",
                "  - wheel",
                "  - staff",
            ],
        ),
        (
            {"cloud_init_users_groups": {"groups": {"docker": "dev"}}},
            [
                "groups:",
                "  docker:",
                "    dev",
            ],
        ),
        (
            {"cloud_init_users_groups": {"user": "ubuntu"}},
            [
                "user:",
                "  ubuntu",
            ],
        ),
        (
            {
                "cloud_init_users_groups": {
                    "user": {
                        "name": "alice",
                        "ssh_authorized_keys": ["ssh-rsa AAA"],
                    }
                }
            },
            [
                "user:",
                "  name: alice",
                "  ssh_authorized_keys:",
                "    - ssh-rsa AAA",
            ],
        ),
        (
            {"cloud_init_users_groups": {"users": ["alice", "bob"]}},
            [
                "users:",
                "  - alice",
                "  - bob",
            ],
        ),
        (
            {"cloud_init_users_groups": {"users": {"bob": {"gecos": "Bob"}}}},
            [
                "users:",
                "  - name: bob",
                "    gecos: Bob",
            ],
        ),
        (
            {
                "cloud_init_users_groups": {
                    "user": {"name": "charlie", "hashed_passwd": "$6$hash"}
                }
            },
            [
                "user:",
                "  name: charlie",
                "  hashed_passwd: $6$hash",
            ],
        ),
        (
            {
                "cloud_init_users_groups": {
                    "user": {
                        "name": "ops",
                        "doas": ["permit nopass :wheel"],
                        "create_groups": False,
                    }
                }
            },
            [
                "user:",
                "  name: ops",
                "  create_groups: false",
                "  doas:",
                "    - permit nopass :wheel",
            ],
        ),
    ],
)
def test_built_in_cloud_init_module_user_and_groups(
    cobbler_api: CobblerAPI, input_meta: Dict[str, Any], expected_result: List[str]
):
    """
    Parametrized tests for the built-in Cloud-Init user and groups snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-user-and-groups"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    # Act
    result = cobbler_api.templar.render(
        target_template.content, input_meta, None, template_type="jinja"
    )

    # Assert
    if result:
        assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


def test_built_in_cloud_init_module_wireguard(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init Wireguard snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-wireguard"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


@pytest.mark.parametrize(
    "input_meta,expected_result",
    [
        ({}, []),
        (
            {"cloud_init_write_files": [{"path": "/tmp/test"}]},
            ["write_files:", "  - path: /tmp/test"],
        ),
        (
            {
                "cloud_init_write_files": [
                    {"path": "/etc/example", "content": "line1\nline2"}
                ]
            },
            [
                "write_files:",
                "  - path: /etc/example",
                "    content: |",
                "      line1",
                "      line2",
            ],
        ),
        (
            {
                "cloud_init_write_files": [
                    {
                        "path": "/etc/fromuri",
                        "source": {
                            "uri": "http://example.com/file",
                            "headers": {"X-Test": "val"},
                        },
                    }
                ]
            },
            [
                "write_files:",
                "  - path: /etc/fromuri",
                "    source:",
                "      uri: http://example.com/file",
                "      headers:",
                "        X-Test: val",
            ],
        ),
        (
            {
                "cloud_init_write_files": [
                    {
                        "path": "/etc/properties",
                        "owner": "user:group",
                        "permissions": "0640",
                        "encoding": "b64",
                        "append": True,
                        "defer": True,
                    }
                ]
            },
            [
                "write_files:",
                "  - path: /etc/properties",
                "    owner: user:group",
                "    permissions: 0640",
                "    encoding: b64",
                "    append: true",
                "    defer: true",
            ],
        ),
    ],
)
def test_built_in_cloud_init_module_write_files(
    cobbler_api: CobblerAPI, input_meta: Dict[str, Any], expected_result: List[str]
):
    """
    Test to verify the rendering of the built-in Cloud-Init write files snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-write-files"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    # Act
    result = cobbler_api.templar.render(
        target_template.content, input_meta, None, template_type="jinja"
    )

    # Assert
    if result:
        assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)


def test_built_in_cloud_init_module_yum_add_repo(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Cloud-Init YUM add repo snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-yum-add-repo"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert yaml.safe_load(result)
    assert result == ""


@pytest.mark.parametrize(
    "input_meta,expected_result",
    [
        ({}, []),
        (
            {"cloud_init_zypper": {"config": {"download.use_deltarpm": True}}},
            ["zypper:", "  config:", "    download.use_deltarpm: true"],
        ),
        (
            {
                "cloud_init_zypper": {
                    "config": {
                        "download.use_deltarpm": True,
                        "reposdir": "/etc/zypp/repos.dir",
                        "servicesdir": "/etc/zypp/services.d",
                    }
                }
            },
            [
                "zypper:",
                "  config:",
                "    download.use_deltarpm: true",
                "    reposdir: /etc/zypp/repos.dir",
                "    servicesdir: /etc/zypp/services.d",
            ],
        ),
        (
            {
                "cloud_init_zypper": {
                    "config": {"download.use_deltarpm": True},
                    "repos": [
                        {
                            "autorefresh": 1,
                            "baseurl": "http://dl.opensuse.org/dist/leap/v/repo/oss/",
                            "enabled": 1,
                            "id": "opensuse-oss",
                            "name": "os-oss",
                        }
                    ],
                }
            },
            [
                "zypper:",
                "  repos:",
                "    - autorefresh: 1",
                "      baseurl: http://dl.opensuse.org/dist/leap/v/repo/oss/",
                "      enabled: 1",
                "      id: opensuse-oss",
                "      name: os-oss",
                "  config:",
                "    download.use_deltarpm: true",
            ],
        ),
    ],
)
def test_built_in_cloud_init_module_zypper_add_repo(
    cobbler_api: CobblerAPI, input_meta: Dict[str, Any], expected_result: List[str]
):
    """
    Test to verify the rendering of the built-in Cloud-Init zypper add repo snippet.
    """
    # Arrange
    # Data validation must happen before data is handed to Jinja.
    target_template = cobbler_api.find_template(
        False, False, name="built-in-cloud-init-module-zypper-add-repo"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    # Act
    result = cobbler_api.templar.render(
        target_template.content, input_meta, None, template_type="jinja"
    )

    # Assert
    if result:
        assert yaml.safe_load(result)
    assert result == "\n".join(expected_result)
