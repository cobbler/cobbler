import contextlib

import pytest

from cobbler.actions import report

from tests.conftest import does_not_raise


@pytest.fixture(scope="function")
def reporter(cobbler_api):
    return report.Report(cobbler_api)


def test_fielder(reporter):
    # Arrange
    input_structure = {}
    input_fields_list = []

    # Act
    result = reporter.fielder(input_structure, input_fields_list)

    # Assert
    assert result is not None


def test_reporting_csv(reporter):
    # Arrange
    input_info = [
        {"name": "test", "uid": "adsökjnvskpdjnbfpsn"},
        {"name": "test2", "uid": "asdkjnfdn"},
    ]
    input_order = ["name", "uid"]
    input_noheaders = False
    expected_result = "name,uid,\ntest,adsökjnvskpdjnbfpsn,\ntest2,asdkjnfdn,\n"

    # Act
    result = reporter.reporting_csv(input_info, input_order, input_noheaders)

    # Assert
    assert result == expected_result


def test_reporting_trac(reporter):
    # Arrange
    input_info = [
        {"name": "test", "uid": "adsökjnvskpdjnbfpsn"},
        {"name": "test2", "uid": "asdkjnfdn"},
    ]
    input_order = ["name", "uid"]
    input_noheaders = False
    expected_result = (
        "||name||uid||\n||test||adsökjnvskpdjnbfpsn||\n||test2||asdkjnfdn||\n"
    )

    # Act
    result = reporter.reporting_trac(input_info, input_order, input_noheaders)

    # Assert
    assert result == expected_result


def test_reporting_doku(reporter):
    # Arrange
    input_info = [
        {"name": "test", "uid": "adsökjnvskpdjnbfpsn"},
        {"name": "test2", "uid": "asdkjnfdn"},
    ]
    input_order = ["name", "uid"]
    input_noheaders = False
    expected_result = "^name^uid^\n|test|adsökjnvskpdjnbfpsn|\n|test2|asdkjnfdn|\n"

    # Act
    result = reporter.reporting_doku(input_info, input_order, input_noheaders)

    # Assert
    assert result == expected_result


def test_reporting_mediawiki(reporter):
    # Arrange
    input_info = [
        {"name": "test", "uid": "adsökjnvskpdjnbfpsn"},
        {"name": "test2", "uid": "asdkjnfdn"},
    ]
    input_order = ["name", "uid"]
    input_noheaders = False
    expected_result = '{| border="1"\n|name||uid\n|-\n|test||adsökjnvskpdjnbfpsn\n|-\n|test2||asdkjnfdn\n|-\n|}\n'

    # Act
    result = reporter.reporting_mediawiki(input_info, input_order, input_noheaders)

    # Assert
    assert result == expected_result


@pytest.mark.parametrize(
    "input_report_type,expected_exception",
    [
        ("csv", does_not_raise()),
        ("mediawiki", does_not_raise()),
        ("trac", does_not_raise()),
        ("doku", does_not_raise()),
        ("garbage", pytest.raises(ValueError)),
    ],
)
def test_print_formatted_data(mocker, reporter, input_report_type, expected_exception):
    # Arrange
    with contextlib.suppress(AttributeError):
        mock_reporting = mocker.patch.object(reporter, f"reporting_{input_report_type}")

    # Act
    with expected_exception:
        reporter.print_formatted_data([], [], input_report_type, True)

        # Assert
        if input_report_type == "garbarge":
            pytest.fail("Test did not match any of the expected assertions!")
        else:
            mock_reporting.assert_called_with([], [], True)


class MockTestItem:
    def __init__(self, name):
        self.name = name

    def to_string(self):
        return "mytest"


def test_reporting_print_sorted(mocker, reporter):
    # Arrange
    input_collection = [MockTestItem("test1")]
    mock_print = mocker.patch("builtins.print")

    # Act
    reporter.reporting_print_sorted(input_collection)

    # Assert
    assert mock_print.call_count == 1
    assert mock_print.called_with("mytest")


def test_reporting_names2(mocker, reporter):
    # Arrange
    input_collection = {"test1": MockTestItem("test1")}
    input_name = "test1"
    mock_print = mocker.patch("builtins.print")

    # Act
    reporter.reporting_list_names2(input_collection, input_name)

    # Assert
    assert mock_print.call_count == 1
    assert mock_print.called_with("mytest")


def test_reporting_print_all_fields(mocker, reporter):
    # Arrange
    input_collection = []
    input_report_name = ""
    input_report_type = ""
    input_report_noheaders = True
    mock_print_formatted_data = mocker.patch.object(reporter, "print_formatted_data")

    # Act
    reporter.reporting_print_all_fields(
        input_collection,
        input_report_name,
        input_report_type,
        input_report_noheaders,
    )

    # Assert
    assert mock_print_formatted_data.call_count == 1
    # TODO: Tighter checking
    assert mock_print_formatted_data.called_with(
        mocker.ANY, mocker.ANY, mocker.ANY, mocker.ANY
    )


def test_reporting_print_x_fields(mocker, reporter):
    # Arrange
    input_collection = []
    input_report_name = ""
    input_report_type = ""
    input_report_fields = ""
    input_report_noheaders = True
    fake_fielder_return = {"key1": "fake data"}
    expected_result = [fake_fielder_return]
    mocker.patch.object(reporter, "fielder", return_value=fake_fielder_return)
    mock_formatted_data = mocker.patch.object(reporter, "print_formatted_data")

    # Act
    reporter.reporting_print_x_fields(
        input_collection,
        input_report_name,
        input_report_type,
        input_report_fields,
        input_report_noheaders,
    )

    # Assert
    assert mock_formatted_data.call_count == 1
    # TODO: Tighter checking
    assert mock_formatted_data.called_with(
        expected_result, mocker.ANY, mocker.ANY, mocker.ANY
    )


@pytest.mark.parametrize(
    "input_report_what,input_report_name,input_report_type,input_report_fields,expected_print_all_fields_count,"
    "expected_print_x_fields_count,expected_print_sorted_count,expected_list_names2_count",
    [
        ("text", "", "", "", 0, 0, 0, 0),
        ("", "", "", "", 0, 0, 0, 0),
    ],
)
def test_run(
    mocker,
    reporter,
    input_report_what,  # symbols the collection to report
    input_report_name,  # symbols the name of the collection items to report
    input_report_type,  # valid values: all, csv, mediawiki, trac, doku
    input_report_fields,  # valid values: all or a comma delimited str where spaces get removed
    expected_print_all_fields_count,
    expected_print_x_fields_count,
    expected_print_sorted_count,
    expected_list_names2_count,
):
    # Arrange
    input_report_noheaders = True
    mock_reporting_print_all_fields = mocker.patch.object(
        reporter, "reporting_print_all_fields", return_value=None
    )
    mock_reporting_print_x_fields = mocker.patch.object(
        reporter, "reporting_print_x_fields", return_value=None
    )
    mock_reporting_print_sorted = mocker.patch.object(
        reporter, "reporting_print_sorted", return_value=None
    )
    mock_reporting_list_names2 = mocker.patch.object(
        reporter, "reporting_list_names2", return_value=None
    )

    # Act
    reporter.run(
        input_report_what,
        input_report_name,
        input_report_type,
        input_report_fields,
        input_report_noheaders,
    )

    # Assert
    # TODO: Tighter checking
    assert mock_reporting_print_all_fields.call_count == expected_print_all_fields_count
    assert mock_reporting_print_x_fields.call_count == expected_print_x_fields_count
    assert mock_reporting_print_sorted.call_count == expected_print_sorted_count
    assert mock_reporting_list_names2.call_count == expected_list_names2_count
