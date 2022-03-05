import optparse

import pytest

from cobbler import cli


@pytest.mark.parametrize("input_data,expected_result", [
    ("", ""),
    (0, 0),
    (None, "")
])
def test_n2s(input_data, expected_result):
    # Arrange
    # Act
    result = cli.n2s(input_data)

    # Assert
    assert result == expected_result


@pytest.mark.skip("TODO: Does not work yet.")
@pytest.mark.parametrize("input_options,input_k,expected_result", [
    (None, None, None),
    ("--dns", "name", ""),
    ("--dhcp", "name", ""),
    ("--system", "name", "")
])
def test_opt(input_options, input_k, expected_result, mocker):
    # Arrange
    # TODO: Create Mock which replaces n2s
    # mocker.patch.object(cli, "n2s")

    # Act
    print(cli.opt(input_options, input_k))

    # Assert
    # TODO: Assert args for n2s not the function return
    assert False


@pytest.mark.parametrize("input_parser,expected_result", [
    (["--systems=a.b.c"], {'systems': ['a.b.c']}),
    (["--systems=a.b.c,a.d.c"], {'systems': ['a.b.c', 'a.d.c']}),
    (["--systems=t1.example.de"], {'systems': ['t1.example.de']})
])
def test_get_comma_separated_args(input_parser, expected_result):
    # Arrange
    parser_obj = optparse.OptionParser()
    parser_obj.add_option("--systems", dest="systems", type='string', action="callback",
                          callback=cli.get_comma_separated_args)

    # Act
    (options, args) = parser_obj.parse_args(args=input_parser)

    # Assert
    assert expected_result == parser_obj.values.__dict__
