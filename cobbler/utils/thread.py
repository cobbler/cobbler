"""
This module is responsible for managing the custom common threading logic Cobbler has.
"""

import logging
import pathlib
from threading import Thread
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union

from cobbler import enums, utils

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.remote import CobblerXMLRPCInterface


class CobblerThread(Thread):
    """
    This is a custom thread that has a custom logger as well as logic to execute Cobbler triggers.
    """

    def __init__(
        self,
        event_id: str,
        remote: "CobblerXMLRPCInterface",
        options: Optional[Union[List[str], Dict[str, Any]]],
        task_name: str,
        api: "CobblerAPI",
        run: Callable[["CobblerThread"], None],
        on_done: Optional[Callable[["CobblerThread"], None]] = None,
    ):
        """
        This constructor creates a Cobbler thread which then may be run by calling ``run()``.

        :param event_id: The event-id which is associated with this thread. Also used as thread name
        :param remote: The Cobbler remote object to execute actions with.
        :param options: Additional options which can be passed into the Thread.
        :param task_name: The high level task name which is used to trigger pre- and post-task triggers
        :param api: The Cobbler api object to resolve information with.
        :param run: The callable that is going to be executed with this thread.
        :param on_done: An optional callable that is going to be executed after ``run`` but before the triggers.
        """
        super().__init__(name=event_id)
        self.event_id = event_id
        self.remote = remote
        self.logger = logging.getLogger()
        self.__task_log_handler: Optional[logging.FileHandler] = None
        self.__setup_logger()
        self._run = run
        self.on_done = on_done
        if options is None:
            options = []
        self.options = options
        self.task_name = task_name
        self.api = api

    def __setup_logger(self):
        """
        Utility function that will set up the Python logger for the tasks in a special directory.
        """
        filename = pathlib.Path("/var/log/cobbler/tasks") / f"{self.event_id}.log"
        self.__task_log_handler = logging.FileHandler(str(filename), encoding="utf-8")
        task_log_formatter = logging.Formatter(
            "[%(threadName)s] %(asctime)s - %(levelname)s | %(message)s"
        )
        self.__task_log_handler.setFormatter(task_log_formatter)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(self.__task_log_handler)

    def _set_task_state(self, new_state: enums.EventStatus):
        """
        Set the state of the task. (For internal use only)

        :param new_state: The new state of the task.
        """
        if not isinstance(new_state, enums.EventStatus):  # type: ignore
            raise TypeError('"new_state" needs to be of type enums.EventStatus!')
        if self.event_id not in self.remote.events:
            raise ValueError('"event_id" not existing!')
        self.remote.events[self.event_id].state = new_state
        # clear the list of who has read it
        self.remote.events[self.event_id].read_by_who = []
        if new_state == enums.EventStatus.COMPLETE:
            self.logger.info("### TASK COMPLETE ###")
        elif new_state == enums.EventStatus.FAILED:
            self.logger.error("### TASK FAILED ###")

    def run(self) -> None:
        """
        Run the thread.

        :return: The return code of the action. This may a boolean or a Linux return code.
        """
        self.logger.info("start_task(%s); event_id(%s)", self.task_name, self.event_id)
        try:
            if utils.run_triggers(
                api=self.api,
                globber=f"/var/lib/cobbler/triggers/task/{self.task_name}/pre/*",
                additional=self.options if isinstance(self.options, list) else [],
            ):
                self._set_task_state(enums.EventStatus.FAILED)
                return
            return_code = self._run(self)
            if return_code is not None and not return_code:
                self._set_task_state(enums.EventStatus.FAILED)
            else:
                self._set_task_state(enums.EventStatus.COMPLETE)
                if self.on_done is not None:
                    self.on_done(self)
                utils.run_triggers(
                    api=self.api,
                    globber=f"/var/lib/cobbler/triggers/task/{self.task_name}/post/*",
                    additional=self.options if isinstance(self.options, list) else [],
                )
            return return_code
        except Exception:
            utils.log_exc()
            self._set_task_state(enums.EventStatus.FAILED)
            return
        finally:
            if self.__task_log_handler is not None:
                self.logger.removeHandler(self.__task_log_handler)
