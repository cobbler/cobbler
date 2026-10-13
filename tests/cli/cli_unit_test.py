import optparse
import threading
import time
import xmlrpc.client

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


def test_follow_task_waits_instead_of_busy_looping(mocker, tmp_path):
    # Regression test for https://github.com/cobbler/cobbler/issues/3866 : on EOF the original
    # implementation never reached its "time.sleep(1)" branch and busy-looped at 100% CPU instead.
    # Whether the task is done is decided solely by the (here: mocked) XML-RPC status, not the log.
    # Arrange
    logfile = tmp_path / "cobbler.log"
    logfile.write_text("")
    fake_self = mocker.Mock()
    fake_self.remote.get_task_status.return_value = [0, "test", "running", []]

    sleep_calls = []

    def fake_sleep(seconds):
        sleep_calls.append(seconds)
        if len(sleep_calls) >= 3:
            fake_self.remote.get_task_status.return_value = [0, "test", "complete", []]

    mocker.patch("cobbler.cli.time.sleep", side_effect=fake_sleep)

    # Act
    result = cli.CobblerCLI.follow_task(fake_self, "TASKID", logfile=str(logfile), status_poll_interval=0)

    # Assert
    assert len(sleep_calls) >= 3
    assert result == 0


def test_follow_task_follows_rotated_log(mocker, tmp_path, capsys):
    # Regression test for https://github.com/cobbler/cobbler/issues/3866 and
    # https://github.com/cobbler/cobbler/issues/3888 : a log rotation (the live file renamed away, a fresh
    # one created at the same path) must not leave follow_task reading forever from the orphaned inode -
    # progress lines written to the new file must still be picked up.
    # Arrange
    logfile = tmp_path / "cobbler.log"
    logfile.write_text("")
    fake_self = mocker.Mock()
    fake_self.remote.get_task_status.return_value = [0, "test", "running", []]

    result = {}

    def run():
        result["rc"] = cli.CobblerCLI.follow_task(
            fake_self, "TASKID", logfile=str(logfile), status_poll_interval=0.2
        )

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    time.sleep(0.3)

    # Act: simulate what logrotate does - rename the live file away, create a fresh one at the same path.
    logfile.rename(tmp_path / "cobbler.log.rotated")
    logfile.write_text("[TASKID] 2026-10-13 - INFO | progress after rotation\n")
    time.sleep(0.5)
    # The task's authoritative state (not the log) is what ends the loop.
    fake_self.remote.get_task_status.return_value = [0, "test", "complete", []]
    thread.join(timeout=5)

    # Assert
    assert not thread.is_alive()
    assert result["rc"] == 0
    assert "progress after rotation" in capsys.readouterr().out


def test_follow_task_aborts_when_daemon_forgets_task(tmp_path, mocker):
    # If cobblerd itself was restarted while the task was running (e.g. a logrotate postrotate hook
    # running "systemctl try-reload-or-restart cobblerd", which falls back to a full restart since
    # cobblerd.service defines no ExecReload=), the task's in-memory state is gone and nobody will ever
    # write a completion/failure marker. follow_task must notice this via get_task_status and bail out
    # instead of waiting forever.
    # Arrange
    logfile = tmp_path / "cobbler.log"
    logfile.write_text("")
    fake_self = mocker.Mock()
    fake_self.remote.get_task_status.side_effect = xmlrpc.client.Fault(1, "no event with that id")

    result = {}

    def run():
        result["rc"] = cli.CobblerCLI.follow_task(
            fake_self, "TASKID", logfile=str(logfile), status_poll_interval=0.2
        )

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    thread.join(timeout=5)

    # Assert
    assert not thread.is_alive()
    assert result["rc"] == 1


def test_follow_task_completes_via_status_poll(tmp_path, mocker):
    # Task completion is decided solely by the XML-RPC status poll, not by anything in the log.
    # Arrange
    logfile = tmp_path / "cobbler.log"
    logfile.write_text("")
    fake_self = mocker.Mock()
    fake_self.remote.get_task_status.return_value = [0, "test", "complete", []]

    result = {}

    def run():
        result["rc"] = cli.CobblerCLI.follow_task(
            fake_self, "TASKID", logfile=str(logfile), status_poll_interval=0.2
        )

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    thread.join(timeout=5)

    # Assert
    assert not thread.is_alive()
    assert result["rc"] == 0


def test_follow_task_does_not_print_raw_completion_marker_line(tmp_path, mocker, capsys):
    # Regression test: the "### TASK COMPLETE ###"/"### TASK FAILED ###" lines written to the log are an
    # internal signal, not progress output. Since completion is now decided solely by the status poll, these
    # marker lines must not also fall through to the generic per-line "print(line)" path, or the user sees
    # both the raw marker text and the clean "*** TASK COMPLETE ***"/"!!! TASK FAILED !!!" message.
    # Arrange
    logfile = tmp_path / "cobbler.log"
    logfile.write_text(
        "[TASKID] 2026-10-13 - INFO | some progress\n"
        "[TASKID] 2026-10-13 - INFO | ### TASK COMPLETE ###\n"
    )
    fake_self = mocker.Mock()
    fake_self.remote.get_task_status.return_value = [0, "test", "complete", []]

    # Act
    result = cli.CobblerCLI.follow_task(fake_self, "TASKID", logfile=str(logfile), status_poll_interval=0.2)

    # Assert
    out = capsys.readouterr().out
    assert result == 0
    assert "some progress" in out
    assert "### TASK COMPLETE ###" not in out
    assert out.count("*** TASK COMPLETE ***") == 1


def test_follow_task_fails_via_status_poll(tmp_path, mocker):
    # Same as above, for the failure outcome.
    # Arrange
    logfile = tmp_path / "cobbler.log"
    logfile.write_text("")
    fake_self = mocker.Mock()
    fake_self.remote.get_task_status.return_value = [0, "test", "failed", []]

    result = {}

    def run():
        result["rc"] = cli.CobblerCLI.follow_task(
            fake_self, "TASKID", logfile=str(logfile), status_poll_interval=0.2
        )

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    thread.join(timeout=5)

    # Assert
    assert not thread.is_alive()
    assert result["rc"] == 1
