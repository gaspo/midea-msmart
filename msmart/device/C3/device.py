from __future__ import annotations

import logging
from enum import IntEnum
from typing import Any, List, Optional, cast

from msmart.base_device import Device
from msmart.const import DeviceType
from msmart.frame import InvalidFrameException

from .command import QueryBasicCommand, QueryBasicResponse, QueryType, Response

_LOGGER = logging.getLogger(__name__)


class HeatPump(Device):

    class RunMode(IntEnum):
        # TODO is 0 off?
        AUTO = 1
        COOL = 2
        HEAT = 3
        DHW = 5

    class TerminalType(IntEnum):
        FAN_COIL = 0
        FLOOR_HEAT = 1
        RADIATOR = 2

    class TemperatureType(IntEnum):
        AIR = 0
        WATER = 1

    class Zone:
        """A zone within the heat pump system."""

        def __init__(self) -> None:
            # TODO properties?
            self._power_state = False
            self._curve_state = False
            self._temperature_type = None
            self._terminal_type = None

            self._target_temperature = 25

            self._min_heat_temperature = 25
            self._max_heat_temperature = 55

            self._min_cool_temperature = 5
            self._max_cool_temperature = 25

    def __init__(self, ip: str, device_id: int,  port: int, **kwargs) -> None:
        # Remove possible duplicate device_type kwarg
        kwargs.pop("device_type", None)

        super().__init__(ip=ip, port=port, device_id=device_id,
                         device_type=DeviceType.HEAT_PUMP, **kwargs)

        self._run_mode = None
        self._heat_enable = False
        self._cool_enable = False
        self._zone2_enable = False

        self._zone_1 = HeatPump.Zone()
        self._zone_2 = HeatPump.Zone()

        # Domestic hot water
        self._dhw_enable = False
        self._dhw_power_state = False
        self._dhw_target_temperature = 25
        self._dhw_min_temperature = 20
        self._dhw_max_temperature = 60

        # Room thermostat
        self._room_thermostat_enable = False
        self._room_termostate_power_state = False
        self._room_target_temperature = 25
        self._room_min_temperature = 17
        self._room_max_temperature = 30

        # Misc
        self._tbh_state = False
        self._fastdhw_state = False

        self._tank_temperature = None

    def _update_state(self, res: QueryBasicResponse) -> None:

        self._run_mode = HeatPump.RunMode(res.run_mode)
        # TODO Run mode in auto?
        self._heat_enable = res.heat_enable
        self._cool_enable = res.cool_enable
        self._zone2_enable = res.zone2_enable

        for i, zone in enumerate([self._zone_1, self._zone_2], start=1):
            zone._power_state = getattr(res, f"zone{i}_power_state")
            zone._curve_state = getattr(res, f"zone{i}_curve_state")
            zone._temperature_type = HeatPump.TemperatureType(
                getattr(res, f"zone{i}_temp_type)"))
            zone._terminal_type = getattr(
                res, f"zone{i}_terminal_type")  # TODO enum

            zone._target_temperature = getattr(
                res, f"zone{i}_target_temperature")

            zone._min_heat_temperature = getattr(
                res, f"zone{i}_heat_min_temperature")
            zone._max_heat_temperature = getattr(
                res, f"zone{i}_heat_max_temperature")

            zone._min_cool_temperature = getattr(
                res, f"zone{i}_cool_min_temperature")
            zone._max_cool_temperature = getattr(
                res, f"zone{i}_cool_max_temperature")

        self._dhw_enable = res.dhw_enable
        self._dhw_power_state = res.dhw_power_state
        self._dhw_target_temperature = res.dhw_target_temperature
        self._dhw_min_temperature = res.dhw_min_temperature
        self._dhw_max_temperature = res.dhw_max_temperature

        self._room_thermostat_enable = res.room_thermostat_enable
        self._room_thermostat_power_state = res.room_thermostat_power_state
        self._room_thermostat_target_temperature = res.room_target_temperature
        self._room_thermostat_min_temperature = res.room_min_temperature
        self._room_thermostat_max_temperature = res.room_max_temperature

        self._tbh_state = res.tbh_state
        self._fastdhw_state = res.fastdhw_state

        # TODO time set state, silence state, holiday state, eco state
        # TODO error code

        self._tank_temperature = res.tank_temperature

    def _process_state_response(self, response: Response) -> None:
        """Update the local state from a device state response."""

        if response.type == QueryType.QUERY_BASIC:
            self._update_state(cast(QueryBasicResponse, response))
        else:
            _LOGGER.debug("Ignored unknown response from %s:%d: %s",
                          self.ip, self.port, response.payload.hex())

    async def _send_command_get_responses(self, command) -> List[Response]:
        """Send a command and return a list of valid response."""

        responses = await super()._send_command(command)

        # No response from device
        if responses is None:
            self._online = False
            return []

        # Device is online if we received any response
        self._online = True

        valid_responses = []
        for data in responses:
            try:
                # Construct response from data
                response = Response.construct(data)
            except InvalidFrameException as e:
                _LOGGER.error(e)
                continue

            # Device is supported if we can process a response
            self._supported = True

            valid_responses.append(response)

        return valid_responses

    async def refresh(self) -> None:
        """Refresh the local copy of the device state."""

        cmd = QueryBasicCommand()
        # Process any state responses from the device
        for response in await self._send_command_get_responses(cmd):
            self._process_state_response(response)
