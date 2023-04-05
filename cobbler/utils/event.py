"""
This module contains logic to support the events Cobbler generates in its XML-RPC API.
"""

import time
import uuid
from typing import List, Union

from cobbler import enums


class CobblerEvent:
    """
    This is a small helper class that represents an event in Cobbler.
    """

    def __init__(self, name: str = "", statetime: float = 0.0) -> None:
        """
        Default Constructor that initializes the event id.

        :param name: The human-readable name of the event
        :statetime: The time the event was created.
        """
        self.__event_id = ""
        self.statetime = statetime
        self.__name = name
        self.state = enums.EventStatus.INFO
        self.read_by_who: List[str] = []
        # Initialize the even_id
        self.__generate_event_id()

    def __len__(self) -> int:
        return len(self.__members())

    def __getitem__(self, idx: int) -> Union[str, List[str], float]:
        return self.__members()[idx]

    def __members(self) -> List[Union[str, float, List[str]]]:
        """
        Lists the members with their current values.

        :returns: This converts all members to scalar types that can be passed via XML-RPC.
        """
        return [self.statetime, self.name, self.state.value, self.read_by_who]

    @property
    def event_id(self) -> str:
        """
        Read only property to retrieve the internal ID of the event.
        """
        return self.__event_id

    @property
    def name(self) -> str:
        """
        Read only property to retrieve the human-readable name of the event.
        """
        return self.__name

    def __generate_event_id(self) -> None:
        """
        Generate an event id based on the current timestamp

        :return: An id in the format: "<4 digit year>-<2 digit month>-<two digit day>_<2 digit hour><2 digit minute>
                 <2 digit second>_<optional string>"
        """
        (
            year,
            month,
            day,
            hour,
            minute,
            second,
            _,
            _,
            _,
        ) = time.localtime()
        task_uuid = uuid.uuid4().hex
        self.__event_id = f"{year:04d}-{month:02d}-{day:02d}_{hour:02d}{minute:02d}{second:02d}_{self.name}_{task_uuid}"
