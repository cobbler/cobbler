"""
Test module to verify the built-in snippets for Agama.
"""

from typing import Any, Dict, List

import pytest

from cobbler.api import CobblerAPI


@pytest.mark.parametrize(
    "input_meta,expected_result",
    [
        ({}, []),
        (
            {"agama_bootloader_stop_on_boot_menu": True},
            ['"bootloader": {', '        "stopOnBootMenu": true', "    }"],
        ),
        (
            {"agama_bootloader_kernel_options": "test"},
            ['"bootloader": {', '        "extraKernelParams": "test"', "    }"],
        ),
        (
            {
                "agama_bootloader_stop_on_boot_menu": False,
                "agama_bootloader_kernel_options": "test",
            },
            [
                '"bootloader": {',
                '        "stopOnBootMenu": false,',
                '        "extraKernelParams": "test"',
                "    }",
            ],
        ),
    ],
)
def test_built_in_agama_bootloader(
    cobbler_api: CobblerAPI,
    input_meta: Dict[str, Any],
    expected_result: List[str],
):
    """
    Test to verify the rendering of the built-in Agama bootloader snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-agama-bootloader"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    # Act
    result = cobbler_api.templar.render(
        target_template.content, input_meta, None, template_type="jinja"
    )

    # Assert
    assert result == "\n".join(expected_result)


@pytest.mark.parametrize(
    "input_meta,expected_result",
    [
        ({}, []),
        (
            {"agama_dasd": []},
            ['"dasd": {', '        "devices": [', "        ]", "    }"],
        ),
        (
            {"agama_dasd": [{"channel": "0.0.0200"}]},
            [
                '"dasd": {',
                '        "devices": [',
                "            {",
                '                "channel": "0.0.0200"',
                "            }",
                "        ]",
                "    }",
            ],
        ),
    ],
)
def test_built_in_agama_dasd(
    cobbler_api: CobblerAPI,
    input_meta: Dict[str, Any],
    expected_result: List[str],
):
    """
    Test to verify the rendering of the built-in Agama dasd snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-agama-dasd"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    # Act
    result = cobbler_api.templar.render(
        target_template.content, input_meta, None, template_type="jinja"
    )

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_agama_files(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Agama files snippet.
    """
    # Arrange
    expected_result = [
        '"files": [',
        "        {",
        '            "url": "http://localhost/cblr/svc/op/script/system/testsys/?script=test",',
        '            "destination": "/etc/test",',
        '            "permissions": "0777",',
        '            "user": "test",',
        '            "group": "test"',
        "        }",
        "    ]",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-agama-files"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {
        "autoinstall_scheme": "http",
        "server": "localhost",
        "obj_type": "system",
        "name": "testsys",
        "agama_files": [
            {
                "template": "test",
                "destination": "/etc/test",
                "permissions": "0777",
                "user": "test",
                "group": "test",
            }
        ],
    }

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert result == "\n".join(expected_result)


@pytest.mark.parametrize(
    "input_meta,expected_result",
    [
        ({}, []),
        (
            {"hostname": "testhost"},
            ['"hostname": {', '        "static": "testhost"', "    }"],
        ),
    ],
)
def test_built_in_agama_hostname(
    cobbler_api: CobblerAPI,
    input_meta: Dict[str, Any],
    expected_result: List[str],
):
    """
    Test to verify the rendering of the built-in Agama hostname snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-agama-hostname"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    # Act
    result = cobbler_api.templar.render(
        target_template.content, input_meta, None, template_type="jinja"
    )

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_agama_localization(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Agama localization snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-agama-bootloader"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert result == ""


def test_built_in_agama_network(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Agama network snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-agama-network"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert result == ""


@pytest.mark.parametrize(
    "input_meta,expected_result",
    [
        ({}, ['"product": {', '        "id": "Tumbleweed"', "    }"]),
        (
            {"agama_product_id": "SLES"},
            ['"product": {', '        "id": "SLES"', "    }"],
        ),
        (
            {"agama_product_registration_code": "example-regcode"},
            [
                '"product": {',
                '        "id": "Tumbleweed",',
                '        "registrationCode": "example-regcode"',
                "    }",
            ],
        ),
        (
            {"agama_product_registration_email": "noreply@example.org"},
            [
                '"product": {',
                '        "id": "Tumbleweed",',
                '        "registrationEmail": "noreply@example.org"',
                "    }",
            ],
        ),
        (
            {"agama_product_registration_url": "https://example.org/rmt"},
            [
                '"product": {',
                '        "id": "Tumbleweed",',
                '        "registrationUrl": "https://example.org/rmt"',
                "    }",
            ],
        ),
        (
            {"agama_product_addons": [{"id": "addon1", "version": "SLES"}]},
            [
                '"product": {',
                '        "id": "Tumbleweed",',
                '        "addons": [',
                "            {",
                '                "id": "addon1",',
                '                "version": "SLES"',
                "            }",
                "        ]",
                "    }",
            ],
        ),
    ],
)
def test_built_in_agama_product(
    cobbler_api: CobblerAPI,
    input_meta: Dict[str, Any],
    expected_result: List[str],
):
    """
    Test to verify the rendering of the built-in Agama product snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-agama-product"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    # Act
    result = cobbler_api.templar.render(
        target_template.content, input_meta, None, template_type="jinja"
    )

    # Assert
    assert result == "\n".join(expected_result)


@pytest.mark.parametrize(
    "input_meta,expected_result",
    [
        ({}, []),
        (
            {"agama_questions": [], "agama_questions_policy": "auto"},
            [
                '"questions": {',
                '        "policy": "auto",',
                '        "answers": [',
                "        ]",
                "    }",
            ],
        ),
        (
            {
                "agama_questions": [
                    {"class": "autoyast.unsupported", "answer": "Continue"}
                ],
                "agama_questions_policy": "auto",
            },
            [
                '"questions": {',
                '        "policy": "auto",',
                '        "answers": [',
                "            {",
                '                "class": "autoyast.unsupported",',
                '                "answer": "Continue"',
                "            }",
                "        ]",
                "    }",
            ],
        ),
    ],
)
def test_built_in_agama_questions(
    cobbler_api: CobblerAPI,
    input_meta: Dict[str, Any],
    expected_result: List[str],
):
    """
    Test to verify the rendering of the built-in Agama questions snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-agama-questions"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    # Act
    result = cobbler_api.templar.render(
        target_template.content, input_meta, None, template_type="jinja"
    )

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_agama_root(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Agama root-user snippet.
    """
    # Arrange
    expected_result = [
        '"root": {',
        '        "hashedPassword": true,',
        '        "password": "passwordhash"',
        "    }",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-agama-root"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {"default_password_crypted": "passwordhash"}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert result == "\n".join(expected_result)


@pytest.mark.parametrize(
    "input_meta,expected_result",
    [
        ({}, []),
        (
            {"agama_scripts": {"pre": [], "post": [], "init": []}},
            [
                '"scripts": {',
                '        "pre": [',
                "        ]",
                '        "post": [',
                "        ]",
                '        "init": [',
                "        ]",
                "    }",
            ],
        ),
        (
            {
                "autoinstall_scheme": "http",
                "server": "localhost",
                "obj_type": "system",
                "name": "testsys",
                "agama_scripts": {"pre": ["myscript"], "post": [], "init": []},
            },
            [
                '"scripts": {',
                '        "pre": [',
                "            {",
                '                "name": "myscript",',
                '                "url": "http://localhost/cblr/svc/op/autoinstall/system/testsys/filename/myscript"',
                "            }",
                "        ]",
                '        "post": [',
                "        ]",
                '        "init": [',
                "        ]",
                "    }",
            ],
        ),
        (
            {
                "autoinstall_scheme": "http",
                "server": "localhost",
                "obj_type": "system",
                "name": "testsys",
                "agama_scripts": {
                    "pre": ["myscript", "testscript"],
                    "post": [],
                    "init": [],
                },
            },
            [
                '"scripts": {',
                '        "pre": [',
                "            {",
                '                "name": "myscript",',
                '                "url": "http://localhost/cblr/svc/op/autoinstall/system/testsys/filename/myscript"',
                "            },",
                "            {",
                '                "name": "testscript",',
                '                "url": "http://localhost/cblr/svc/op/autoinstall/system/testsys/filename/testscript"',
                "            }",
                "        ]",
                '        "post": [',
                "        ]",
                '        "init": [',
                "        ]",
                "    }",
            ],
        ),
    ],
)
def test_built_in_agama_scripts(
    cobbler_api: CobblerAPI,
    input_meta: Dict[str, Any],
    expected_result: List[str],
):
    """
    Test to verify the rendering of the built-in Agama scripts XML snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-agama-scripts"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    # Act
    result = cobbler_api.templar.render(
        target_template.content, input_meta, None, template_type="jinja"
    )

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_agama_security(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Agama security snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-agama-security"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert result == ""


def test_built_in_agama_software(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Agama software snippet.
    """
    # Arrange
    expected_result = [
        '"software": {',
        "    }",
    ]
    target_template = cobbler_api.find_template(
        False, False, name="built-in-agama-software"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_agama_storage_legacy(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Agama legacy storage snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-agama-storage-legacy"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert result == ""


@pytest.mark.parametrize(
    "input_meta,expected_result",
    [
        # Fully human test cases
        ({}, []),
        (
            {"agama_storage": ""},
            ['"storage": {', "    }"],
        ),
        (
            {"agama_storage": {"drives": []}},
            ['"storage": {', '        "drives": [', "        ]", "    }"],
        ),
        (
            {
                "agama_storage": {
                    "drives": [{"alias": "todo", "filesystem": {"type": "ext4"}}]
                }
            },
            [
                '"storage": {',
                '        "drives": [',
                "            {",
                '                "alias": "todo",',
                '                "filesystem": {',
                '                    "type": "ext4"',
                "                }",
                "            }",
                "        ]",
                "    }",
            ],
        ),
        (
            {
                "agama_storage": {
                    "drives": [
                        {"alias": "todo", "partitions": [{"generate": "default"}]}
                    ]
                }
            },
            [
                '"storage": {',
                '        "drives": [',
                "            {",
                '                "alias": "todo",',
                '                "partitions": [',
                '                    { "generate": "default" }',
                "                ]",
                "            }",
                "        ]",
                "    }",
            ],
        ),
        (
            {"agama_storage": {"vg": [{"name": "example"}]}},
            [
                '"storage": {',
                '        "volumeGroups": [',
                "            {",
                '                "name": "example"',
                "            }",
                "        ]",
                "    }",
            ],
        ),
        (
            {"agama_storage": {"md": [{"name": "example"}]}},
            [
                '"storage": {',
                '        "mdRaids": [',
                "            {",
                '                "name": "example"',
                "            }",
                "        ]",
                "    }",
            ],
        ),
        # AI generated test JSONs
        (
            {"agama_storage": {"boot": {"configure": "true"}}},
            [
                '"storage": {',
                '        "boot": {',
                '            "configure": true',
                "        }",
                "    }",
            ],
        ),
        (
            {"agama_storage": {"boot": {"configure": "true", "device": "boot_disk"}}},
            [
                '"storage": {',
                '        "boot": {',
                '            "configure": true,',
                '            "device": "boot_disk"',
                "        }",
                "    }",
            ],
        ),
        (
            {
                "agama_storage": {
                    "drives": [
                        {"search": "*", "filesystem": {"type": "ext4", "path": "/"}}
                    ]
                }
            },
            [
                '"storage": {',
                '        "drives": [',
                "            {",
                '                "search": "*",',
                '                "filesystem": {',
                '                    "type": "ext4",',
                '                    "path": "/"',
                "                }",
                "            }",
                "        ]",
                "    }",
            ],
        ),
        (
            {
                "agama_storage": {
                    "drives": [
                        {
                            "search": "/dev/sda",
                            "partitions": [{"generate": "default"}],
                            "ptabletype": "gpt",
                        }
                    ]
                }
            },
            [
                '"storage": {',
                '        "drives": [',
                "            {",
                '                "search": "/dev/sda",',
                '                "partitions": [',
                '                    { "generate": "default" }',
                "                ],",
                '                "ptableType": "gpt"',
                "            }",
                "        ]",
                "    }",
            ],
        ),
        (
            {
                "agama_storage": {
                    "drives": [
                        {
                            "alias": "encrypted1",
                            "filesystem": {"type": "ext4", "path": "/secret"},
                            "encryption": {
                                "type": "luks1",
                                "data": {
                                    "password": "s3cr3t",
                                    "cipher": "aes-xts-plain64",
                                    "keySize": 512,
                                },
                            },
                        }
                    ]
                }
            },
            [
                '"storage": {',
                '        "drives": [',
                "            {",
                '                "alias": "encrypted1",',
                '                "encryption": {',
                '                    "luks1": {',
                '                        "password": "s3cr3t",',
                '                        "cipher": "aes-xts-plain64",',
                '                        "keySize": 512',
                "                    }",
                "                },",
                '                "filesystem": {',
                '                    "type": "ext4",',
                '                    "path": "/secret"',
                "                }",
                "            }",
                "        ]",
                "    }",
            ],
        ),
        (
            {
                "agama_storage": {
                    "drives": [
                        {
                            "alias": "encrypted2",
                            "encryption": {
                                "type": "luks2",
                                "data": {
                                    "password": "pass2",
                                    "pbkdFunction": "argon2id",
                                },
                            },
                        }
                    ]
                }
            },
            [
                '"storage": {',
                '        "drives": [',
                "            {",
                '                "alias": "encrypted2",',
                '                "encryption": {',
                '                    "luks2": {',
                '                        "password": "pass2",',
                '                        "pbkdFunction": "argon2id"',
                "                    }",
                "                }",
                "            }",
                "        ]",
                "    }",
            ],
        ),
        (
            {
                "agama_storage": {
                    "drives": [
                        {
                            "search": "/dev/disk/by-id/sata-123456",
                            "ptabletype": "gpt",
                            "partitions": [
                                {
                                    "search": {"condition": {"name": "/dev/sda1"}},
                                    "id": "swap",
                                    "size": "2 GiB",
                                    "filesystem": {"type": "swap"},
                                },
                                {
                                    "search": {"condition": {"number": 2}},
                                    "id": "linux",
                                    "size": ["10 GiB", "current"],
                                    "filesystem": {"type": "ext4", "path": "/"},
                                },
                            ],
                        },
                    ]
                }
            },
            [
                '"storage": {',
                '        "drives": [',
                "            {",
                '                "search": "/dev/disk/by-id/sata-123456",',
                '                "partitions": [',
                "                    {",
                '                        "search": {',
                '                            "condition": {"name": "/dev/sda1"}',
                "                        },",
                '                        "id": "swap",',
                '                        "size": "2 GiB",',
                '                        "filesystem": {',
                '                            "type": "swap"',
                "                        }",
                "                    },",
                "                    {",
                '                        "search": {',
                '                            "condition": {"number": 2}',
                "                        },",
                '                        "id": "linux",',
                '                        "size": ["10 GiB", "current"],',
                '                        "filesystem": {',
                '                            "type": "ext4",',
                '                            "path": "/"',
                "                        }",
                "                    }",
                "                ],",
                '                "ptableType": "gpt"',
                "            }",
                "        ]",
                "    }",
            ],
        ),
        (
            {
                "agama_storage": {
                    "drives": [
                        {
                            "alias": "system",
                            "ptabletype": "gpt",
                            "partitions": [
                                {
                                    "generate": {
                                        "partitions": "mandatory",
                                        "encryption": {
                                            "type": "luks1",
                                            "data": {"password": "paz"},
                                        },
                                    }
                                }
                            ],
                        }
                    ]
                }
            },
            [
                '"storage": {',
                '        "drives": [',
                "            {",
                '                "alias": "system",',
                '                "partitions": [',
                "                    {",
                '                        "generate": {',
                '                            "partitions": "mandatory",',
                '                            "encryption": {',
                '                                "luks1": {',
                '                                    "password": "paz"',
                "                                }",
                "                            }",
                "                        }",
                "                    }",
                "                ],",
                '                "ptableType": "gpt"',
                "            }",
                "        ]",
                "    }",
            ],
        ),
        (
            {
                "agama_storage": {
                    "drives": [
                        {
                            "search": "/dev/sdb",
                            "encryption": "random_swap",
                            "filesystem": {"type": "swap"},
                        }
                    ]
                }
            },
            [
                '"storage": {',
                '        "drives": [',
                "            {",
                '                "search": "/dev/sdb",',
                '                "encryption": "random_swap",',
                '                "filesystem": {',
                '                    "type": "swap"',
                "                }",
                "            }",
                "        ]",
                "    }",
            ],
        ),
        (
            {
                "agama_storage": {
                    "drives": [
                        {
                            "search": "/dev/sdc",
                            "ptabletype": "msdos",
                            "partitions": [
                                {
                                    "delete": {"condition": {"number": 1}},
                                },
                                {
                                    "search": {"condition": {"number": 2}},
                                    "id": "linux",
                                    "size": "8 GiB",
                                    "filesystem": {"type": "ext4"},
                                },
                            ],
                        }
                    ]
                }
            },
            [
                '"storage": {',
                '        "drives": [',
                "            {",
                '                "search": "/dev/sdc",',
                '                "partitions": [',
                "                    {",
                '                        "search": {',
                '                            "condition": {"number": 1}',
                "                        },",
                '                        "delete": true',
                "                    },",
                "                    {",
                '                        "search": {',
                '                            "condition": {"number": 2}',
                "                        },",
                '                        "id": "linux",',
                '                        "size": "8 GiB",',
                '                        "filesystem": {',
                '                            "type": "ext4"',
                "                        }",
                "                    }",
                "                ],",
                '                "ptableType": "msdos"',
                "            }",
                "        ]",
                "    }",
            ],
        ),
        (
            {
                "agama_storage": {
                    "drives": [
                        {
                            "search": "/dev/sdd",
                            "ptabletype": "gpt",
                            "partitions": [
                                {
                                    "deleteIfNeeded": "/dev/sdd1",
                                    "size": "20 GiB",
                                },
                                {
                                    "search": "*",
                                    "id": "linux",
                                    "size": "current",
                                    "filesystem": {"type": "ext4"},
                                },
                            ],
                        }
                    ]
                }
            },
            [
                '"storage": {',
                '        "drives": [',
                "            {",
                '                "search": "/dev/sdd",',
                '                "partitions": [',
                "                    {",
                '                        "search": "/dev/sdd1",',
                '                        "size": "20 GiB",',
                '                        "deleteIfNeeded": true',
                "                    },",
                "                    {",
                '                        "search": "*",',
                '                        "id": "linux",',
                '                        "size": "current",',
                '                        "filesystem": {',
                '                            "type": "ext4"',
                "                        }",
                "                    }",
                "                ],",
                '                "ptableType": "gpt"',
                "            }",
                "        ]",
                "    }",
            ],
        ),
    ],
)
def test_built_in_agama_storage(
    cobbler_api: CobblerAPI,
    input_meta: Dict[str, Any],
    expected_result: List[str],
):
    """
    Test to verify the rendering of the built-in Agama storage snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-agama-storage"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    # Act
    result = cobbler_api.templar.render(
        target_template.content, input_meta, None, template_type="jinja"
    )

    # Assert
    assert result == "\n".join(expected_result)


@pytest.mark.parametrize(
    "input_meta,expected_result",
    [
        ({}, []),
        (
            {
                "agama_user_fullname": "John Doe",
                "agama_user_username": "jdoe",
            },
            [],
        ),
        (
            {
                "agama_user_fullname": "John Doe",
                "agama_user_username": "jdoe",
                "agama_user_password": "examplehash",
            },
            [
                '"user": {',
                '        "fullName": "John Doe",',
                '        "userName": "jdoe",',
                '        "hashedPassword": true,',
                '        "password": "examplehash"',
                "    }",
            ],
        ),
    ],
)
def test_built_in_agama_user(
    cobbler_api: CobblerAPI,
    input_meta: Dict[str, Any],
    expected_result: List[str],
):
    """
    Test to verify the rendering of the built-in Agama user snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-agama-user"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")

    # Act
    result = cobbler_api.templar.render(
        target_template.content, input_meta, None, template_type="jinja"
    )

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_agama_zfcp(cobbler_api: CobblerAPI):
    """
    Test to verify the rendering of the built-in Agama zfcp snippet.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-agama-zfcp"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    meta: Dict[str, Any] = {}

    # Act
    result = cobbler_api.templar.render(
        target_template.content, meta, None, template_type="jinja"
    )

    # Assert
    assert result == ""
