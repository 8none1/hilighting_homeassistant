import asyncio
from homeassistant.components import bluetooth
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.components.light import (ColorMode)
from homeassistant.components.light import EFFECT_OFF
from bleak.backends.device import BLEDevice
from bleak.backends.service import BleakGATTCharacteristic, BleakGATTServiceCollection
from bleak.exc import BleakDBusError
from bleak_retry_connector import BLEAK_RETRY_EXCEPTIONS as BLEAK_EXCEPTIONS
from bleak_retry_connector import (
    BleakClientWithServiceCache,
    #BleakError,
    BleakNotFoundError,
    #ble_device_has_changed,
    establish_connection,
)
from typing import Any, TypeVar, cast, Tuple
from collections.abc import Callable
import logging
#import colorsys


LOGGER = logging.getLogger(__name__)

EFFECT_MAP = {}
for e in range(10):
    EFFECT_MAP[f"Effect {e}"] = e
EFFECT_LIST = sorted(EFFECT_MAP)
EFFECT_ID_TO_NAME = {v: k for k, v in EFFECT_MAP.items()}

NAME_ARRAY = ["L7161", "L7183"]
WRITE_CHARACTERISTIC_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
FIRMWARE_REVISION_UUID    = "00002a26-0000-1000-8000-00805f9b34fb"
SW_NUMBER_UUID            = "00002a28-0000-1000-8000-00805f9b34fb"
MANUFACTURER_NAME_UUID    = "00002a29-0000-1000-8000-00805f9b34fb"
TURN_ON_CMD               = [bytearray.fromhex("55 01 02 01")]
TURN_OFF_CMD              = [bytearray.fromhex("55 01 02 00")]
DEFAULT_ATTEMPTS = 3
BLEAK_BACKOFF_TIME = 0.25
RETRY_BACKOFF_EXCEPTIONS = (BleakDBusError)

WrapFuncType = TypeVar("WrapFuncType", bound=Callable[..., Any])

def retry_bluetooth_connection_error(func: WrapFuncType) -> WrapFuncType:
    async def _async_wrap_retry_bluetooth_connection_error(
        self: "HILIGHTINGInstance", *args: Any, **kwargs: Any
    ) -> Any:
        attempts = DEFAULT_ATTEMPTS
        max_attempts = attempts - 1

        for attempt in range(attempts):
            try:
                return await func(self, *args, **kwargs)
            except BleakNotFoundError:
                # The lock cannot be found so there is no
                # point in retrying.
                raise
            except RETRY_BACKOFF_EXCEPTIONS as err:
                if attempt >= max_attempts:
                    LOGGER.debug(
                        "%s: %s error calling %s, reach max attempts (%s/%s)",
                        self.name,
                        type(err),
                        func,
                        attempt,
                        max_attempts,
                        exc_info=True,
                    )
                    raise
                LOGGER.debug(
                    "%s: %s error calling %s, backing off %ss, retrying (%s/%s)...",
                    self.name,
                    type(err),
                    func,
                    BLEAK_BACKOFF_TIME,
                    attempt,
                    max_attempts,
                    exc_info=True,
                )
                await asyncio.sleep(BLEAK_BACKOFF_TIME)
            except BLEAK_EXCEPTIONS as err:
                if attempt >= max_attempts:
                    LOGGER.debug(
                        "%s: %s error calling %s, reach max attempts (%s/%s): %s",
                        self.name,
                        type(err),
                        func,
                        attempt,
                        max_attempts,
                        err,
                        exc_info=True,
                    )
                    raise
                LOGGER.debug(
                    "%s: %s error calling %s, retrying  (%s/%s)...: %s",
                    self.name,
                    type(err),
                    func,
                    attempt,
                    max_attempts,
                    err,
                    exc_info=True,
                )

    return cast(WrapFuncType, _async_wrap_retry_bluetooth_connection_error)


class HILIGHTINGInstance:
    def __init__(self, address, delay: int, hass, data={}, options={}) -> None:
        self.loop = asyncio.get_running_loop()
        self._mac = address
        self._delay = delay
        self._hass = hass
        #self._data = data
        self._options = options
        
        self._device: BLEDevice | None = None
        self._device = bluetooth.async_ble_device_from_address(self._hass, address)
        if not self._device:
            raise ConfigEntryNotReady(
                f"You need to add bluetooth integration (https://www.home-assistant.io/integrations/bluetooth) or couldn't find a nearby device with address: {address}"
            )
        self._connect_lock: asyncio.Lock = asyncio.Lock()
        self._client: BleakClientWithServiceCache | None = None
        self._disconnect_timer: asyncio.TimerHandle | None = None
        self._cached_services: BleakGATTServiceCollection | None = None
        self._expected_disconnect = False
        self._is_on = None
        self._rgb_color = None
        self._brightness = 255
        self._effect = None
        self._effect_speed = 0x64
        self._color_mode = ColorMode.RGB
        self._write_uuid = None
        self._manufacturer_name_char = None
        self._firmware_revision_char = None
        self._model_number_char      = None
        self._turn_on_cmd  = bytearray.fromhex("55 01 02 01")
        self._turn_off_cmd = bytearray.fromhex("55 01 02 00")
        self._model             = data.get("model", None)
        self._manufacturer_name = data.get("manufacturer_name", None)
        self._firmware_version  = data.get("firmware_version", None)

        LOGGER.debug(
            f"Model information for device {self._device.name} : ModelNo {self._model}. MAC: {self._mac}. Data: {data}. Options: {self._options}"
        )
        LOGGER.debug(f"Manufacturer name: {self._manufacturer_name}")
        LOGGER.debug(f"Firmware version: {self._firmware_version}")
        LOGGER.debug(f"Model number: {self._model}")

    async def _retrieve_device_info(self):
        if self._model is None:
            LOGGER.debug("Looking up model number")
            m = await self._read_characteristic(self._model_number_char)
            LOGGER.debug(f"Model number: {m}")
            if m: self._model = m.decode('ascii')
        if self._manufacturer_name is None:
            LOGGER.debug("Looking up manu name")
            m = await self._read_characteristic(self._manufacturer_name_char)
            LOGGER.debug(f"Manufacturer name: {m}")
            if m: self._manufacturer_name = m.decode('ascii')
        if self._firmware_version is None:
            LOGGER.debug("Looking up fw number")
            m = await self._read_characteristic(self._firmware_revision_char)
            LOGGER.debug(f"Firmware version: {m}")
            if m: self._firmware_version = m.decode('ascii')
        
        return bool(self._model and self._manufacturer_name and self._firmware_version)

    async def _read_characteristic(self, char: BleakGATTCharacteristic):
        if not char:
            LOGGER.error(f"No characteristic to read")
            return None
        if self._client is not None:
            data = await self._client.read_gatt_char(char.uuid)
            LOGGER.debug(f"Char read data: {data}")
            return data
        return None
    
    async def _write(self, data: bytearray):
        """Send command to device and read response."""
        await self._ensure_connected()
        await self._write_while_connected(data)

    async def _write_while_connected(self, data: bytearray):
        LOGGER.debug(f"Writing data to {self.name}: {data.hex()}")
        await self._client.write_gatt_char(self._write_uuid, data, False)
    
    @property
    def mac(self):
        return self._device.address

    @property
    def name(self):
        return self._device.name

    @property
    def rssi(self):
        return self._device.rssi

    @property
    def is_on(self):
        return self._is_on

    @property
    def brightness(self):
        return self._brightness 

    @property
    def rgb_color(self):
        return self._rgb_color

    @property
    def effect_list(self) -> list[str]:
        return EFFECT_LIST

    @property
    def effect(self):
        return self._effect
    
    @property
    def color_mode(self):
        return self._color_mode

    @retry_bluetooth_connection_error
    async def turn_on(self):
        await self._write(self._turn_on_cmd)
        self._is_on = True
                
    @retry_bluetooth_connection_error
    async def turn_off(self):
        await self._write(self._turn_off_cmd)
        self._is_on = False

    @retry_bluetooth_connection_error
    async def set_rgb_color(self, rgb: Tuple[int, int, int]):
        """
            |------|------------------------ header
            |      | ||--------------------- red
            |      | || ||------------------ green
            |      | || || ||--------------- blue
            55 07 01 ff 00 00
            55 07 01 00 ff 00
            55 07 01 00 00 ff
        """
        self._rgb_color = rgb
        red = int(rgb[0])
        green = int(rgb[1])
        blue = int(rgb[2])
        rgb_packet = bytearray.fromhex("55 07 01 00 00 00")
        rgb_packet[3] = red
        rgb_packet[4] = green
        rgb_packet[5] = blue
        await self._write(rgb_packet)
        self._effect = EFFECT_OFF
    
    @retry_bluetooth_connection_error
    async def set_brightness(self, brightness: int):
        self._brightness = brightness
        brightness_packet = bytearray.fromhex("55 03 01 ff 03")
        b = int(brightness * 0.06)
        if b > 0x0f:
            b = 0x0f
        brightness_packet[4] = b
        await self._write(brightness_packet)
    
    @retry_bluetooth_connection_error
    async def set_effect(self, effect: str):
        if effect not in EFFECT_LIST:
            LOGGER.error("Effect %s not supported", effect)
            return
        self._effect = effect
        effect_packet = bytearray.fromhex("55 04 01 00")
        effect_id = EFFECT_MAP.get(effect)
        LOGGER.debug('Effect ID: %s', effect_id)
        LOGGER.debug('Effect name: %s', effect)
        effect_packet[3] = effect_id
        await self._write(effect_packet)
    
    @retry_bluetooth_connection_error
    async def set_effect_speed(self, speed: int):
        speed_packet = bytearray.fromhex("55 04 04 7f")
        speed_packet[3] = int(speed * 2.55)
        LOGGER.debug(f"Speed packet: {speed_packet}")
        speed_packet_str = "0x" + "".join(f"{byte:02x}" for byte in speed_packet)
        LOGGER.debug(f"Speed packet: {speed_packet_str}")
        await self._write(speed_packet)

    @retry_bluetooth_connection_error
    async def update(self):
        LOGGER.debug("%s: Update in hilighting called", self.name)
        # if self._model is None:
        #     self._model = await self._detect_model()
        #     LOGGER.debug(f"Model: {self._model}")
        

    async def _ensure_connected(self) -> None:
        """Ensure connection to device is established."""
        if self._connect_lock.locked():
            LOGGER.debug(
                "%s: Connection already in progress, waiting for it to complete",
                self.name,
            )
        if self._client and self._client.is_connected:
            self._reset_disconnect_timer()
            return
        async with self._connect_lock:
            # Check again while holding the lock
            if self._client and self._client.is_connected:
                self._reset_disconnect_timer()
                return
            LOGGER.debug("%s: Connecting", self.name)
            client = await establish_connection(
                BleakClientWithServiceCache,
                self._device,
                self.name,
                self._disconnected,
                # cached_services=self._cached_services,
                use_cached_services=True,
                ble_device_callback=lambda: self._device,
            )
            LOGGER.debug("%s: Connected", self.name)
            resolved = self._resolve_characteristics(client.services)
            
            LOGGER.debug(f"Resolved: {resolved}")
            if not resolved:
                # Try to handle services failing to load
                #resolved = self._resolve_characteristics(await client.get_services())
                LOGGER.debug(f"Chars were not resolved.  Trying again...")
                resolved = self._resolve_characteristics(client.services)
                LOGGER.debug(f"After trying to resolve: Resolved: {resolved}")
            self._cached_services = client.services if resolved else None

            self._client = client
            await self._retrieve_device_info()
            self._reset_disconnect_timer()

    def _resolve_characteristics(self, services: BleakGATTServiceCollection) -> bool:
        """Resolve characteristics."""
        LOGGER.debug(f"Resolving characteristics for {self.name}")
        if char := services.get_characteristic(WRITE_CHARACTERISTIC_UUID):
                self._write_uuid = char
        if char := services.get_characteristic(MANUFACTURER_NAME_UUID):
            self._manufacturer_name_char = char
        if char := services.get_characteristic(FIRMWARE_REVISION_UUID):
            self._firmware_revision_char = char
        if char := services.get_characteristic(SW_NUMBER_UUID):
            self._model_number_char = char
            LOGGER.debug(f"Model number char: {char}")
            LOGGER.debug(f"Model number char UUID: {char.uuid}")
            LOGGER.debug(f"Type of char: {type(char)}")
        LOGGER.debug(f"Chars: Write: {self._write_uuid} Manu name: {self._manufacturer_name_char} Firmware rev: {self._firmware_revision_char} Model num: {self._model_number_char}")
        return bool(self._write_uuid and self._manufacturer_name_char and self._firmware_revision_char and self._model_number_char)

    def _reset_disconnect_timer(self) -> None:
        """Reset disconnect timer."""
        if self._disconnect_timer:
            self._disconnect_timer.cancel()
        self._expected_disconnect = False
        if self._delay is not None and self._delay != 0:
            LOGGER.debug(
                "%s: Configured disconnect from device in %s seconds",
                self.name,
                self._delay
            )
            self._disconnect_timer = self.loop.call_later(self._delay, self._disconnect)

    def _disconnected(self, client: BleakClientWithServiceCache) -> None:
        """Disconnected callback."""
        if self._expected_disconnect:
            LOGGER.debug("%s: Disconnected from device", self.name)
            return
        LOGGER.warning("%s: Device unexpectedly disconnected", self.name)

    def _disconnect(self) -> None:
        """Disconnect from device."""
        self._disconnect_timer = None
        asyncio.create_task(self._execute_timed_disconnect())

    async def stop(self) -> None:
        """Stop the LEDBLE."""
        LOGGER.debug("%s: Stop", self.name)
        await self._execute_disconnect()

    async def _execute_timed_disconnect(self) -> None:
        """Execute timed disconnection."""
        LOGGER.debug(
            "%s: Disconnecting after timeout of %s",
            self.name,
            self._delay
        )
        await self._execute_disconnect()

    async def _execute_disconnect(self) -> None:
        """Execute disconnection."""
        async with self._connect_lock:
            client = self._client
            self._expected_disconnect = True
            self._client = None
            self._write_uuid = None
            if client and client.is_connected:
                await client.disconnect()
            LOGGER.debug("%s: Disconnected", self.name)
    
