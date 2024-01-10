from __future__ import annotations

import logging
import math
import struct
from abc import ABC
from collections import namedtuple
from enum import IntEnum
from typing import Callable, Optional, Union

import msmart.crc8 as crc8
from msmart.base_command import Command
from msmart.const import DeviceType, FrameType

_LOGGER = logging.getLogger(__name__)


class ControlType(IntEnum):
    CONTROL_BASIC = 0x1
    CONTROL_DAY_TIMER = 0x2
    CONTROL_WEEKS_TIMER = 0x3
    CONTROL_HOLIDAY_AWAY = 0x4
    CONTROL_SILENCE = 0x05
    CONTROL_HOLIDAY_HOME = 0x6
    CONTROL_ECO = 0x7
    CONTROL_INSTALL = 0x8
    CONTROL_DISINFECT = 0x9


class QueryType(IntEnum):
    QUERY_BASIC = 0x1
    QUERY_DAY_TIMER = 0x2
    QUERY_WEEKS_TIMER = 0x3
    QUERY_HOLIDAY_AWAY = 0x4
    QUERY_SILENCE = 0x05
    QUERY_HOLIDAY_HOME = 0x6
    QUERY_ECO = 0x7
    QUERY_INSTALL = 0x8
    QUERY_DISINFECT = 0x9


class QueryCommand(Command, ABC):
    """Base class for query commands."""

    def __init__(self, type: QueryType) -> None:
        super().__init__(DeviceType.HEAT_PUMP, frame_type=FrameType.REQUEST)

        self._type = type

    @property
    def payload(self) -> bytes:
        return bytes([
            self._type
        ])


class QueryBasicCommand(QueryCommand):
    """Command to query basic device state."""

    def __init__(self) -> None:
        super().__init__(QueryType.QUERY_BASIC)


class QueryEcoCommand(QueryCommand):
    """Command to query ECO state."""

    def __init__(self) -> None:
        super().__init__(QueryType.QUERY_ECO)
