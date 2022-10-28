import abc
import logging
import paho.mqtt.client
import requests
import socket
import threading
import typing

import watchdog.connections
import watchdog.reloader

logger = logging.getLogger(__name__)


class BaseMonitor(metaclass=abc.ABCMeta):

    def __init__(self, reloader: watchdog.reloader.IntegrationReloader, sensor_name: str,
                 connection: watchdog.connections.BaseConnection) -> None:
        if not connection.is_valid():
            raise RuntimeError('Invalid connection configuration for monitor')

        self.reloader = reloader
        self.sensor_name = sensor_name
        self.connection = connection

        self._backoff_timer: typing.Optional[threading.Timer] = None

    def run(self, stop_signal: threading.Event) -> None:
        if stop_signal.is_set():
            raise RuntimeError('Stop signal already set when trying to run monitor')
        logger.debug('Starting monitor')
        self._start()
        stop_signal.wait()
        logger.debug('Stopping monitor')
        self._stop()
        if self._backoff_timer is not None:
            self._backoff_timer.cancel()

    @abc.abstractmethod
    def _start(self) -> None:
        pass

    @abc.abstractmethod
    def _stop(self) -> None:
        pass

    def _reload(self) -> None:
        if self._backoff_timer is None or self._backoff_timer.finished.is_set():
            if self.reloader.reload():
                logger.info('Successfully reloaded integration')
                logger.debug('Starting backoff timer')
                self._backoff_timer = threading.Timer(60.0, lambda: logger.debug('Backoff timer finished'))
                self._backoff_timer.start()
            else:
                # TODO(BDP): Schedule a retry.
                logger.warning('Failed to reload integration')
        else:
            logger.debug('Ignoring sensor value because backoff timer is running')


class MqttMonitor(BaseMonitor):

    def __init__(self, reloader: watchdog.reloader.IntegrationReloader, sensor_name: str,
                 connection: watchdog.connections.MqttConnection) -> None:
        super().__init__(reloader, sensor_name, connection)
        self.connection: watchdog.connections.MqttConnection

        self._mqtt_client = paho.mqtt.client.Client('integration-monitor')
        self._mqtt_client.on_connect = self._handle_connect
        self._mqtt_client.on_disconnect = self._handle_disconnect
        self._mqtt_client.on_message = self._handle_message
        if self.connection.username and self.connection.password:
            self._mqtt_client.username_pw_set(self.connection.username, self.connection.password)

        logger.debug('Initialized sensor monitor for %s on MQTT broker at: %s', self.sensor_name,
                     self.connection.address)

    def _start(self) -> None:
        try:
            self._mqtt_client.connect(self.connection.address, self.connection.port)
        except socket.gaierror:
            logger.warning('Failed to find MQTT broker at: %s', self.connection.address)
        except TimeoutError:
            logger.warning('Timed out trying to connect to MQTT broker at: %s', self.connection.address)
        self._mqtt_client.loop_start()

    def _stop(self) -> None:
        self._mqtt_client.disconnect()
        self._mqtt_client.loop_stop()

    def _handle_connect(self, client: paho.mqtt.client.Client, flags: dict[str, typing.Any], user_data: None,
                        rc: int) -> None:
        del client, flags, user_data, rc  # Unused
        logger.info('Connected to MQTT broker')
        self._mqtt_client.subscribe(f'homeassistant/sensor/{self.sensor_name}/state')
        logger.debug('Subscribed for sensor value')

    def _handle_disconnect(self, client: paho.mqtt.client.Client, user_data: None, rc: int) -> None:
        del client, user_data, rc  # Unused
        logger.info('Disconnected from MQTT broker')

    def _handle_message(self, client: paho.mqtt.client.Client, user_data: None,
                        message: paho.mqtt.client.MQTTMessage) -> None:
        del client, user_data  # Unused
        if message.payload.decode() == 'unavailable':
            self._reload()


class RestMonitor(BaseMonitor):

    def __init__(self,
                 reloader: watchdog.reloader.IntegrationReloader,
                 sensor_name: str,
                 connection: watchdog.connections.HomeAssistantConnection,
                 poll_interval_seconds: int = 10) -> None:
        super().__init__(reloader, sensor_name, connection)
        self.connection: watchdog.connections.HomeAssistantConnection

        self.poll_interval_seconds = poll_interval_seconds
        self._poll_timer: typing.Optional[threading.Timer] = None

        scheme = 'https' if self.connection.https else 'http'
        self._url = f'{scheme}://{self.connection.address}:{self.connection.port}/api/states/sensor.{self.sensor_name}'
        self._headers = {'Authorization': f'Bearer {self.connection.api_token}'}
        self._verify_certificate = self.connection.verify_certificate

        logger.debug('Initialized sensor monitor for %s on Home Assistant server at: %s', self.sensor_name,
                     self.connection.address)

    def _start(self) -> None:
        self._check_sensor()

    def _stop(self) -> None:
        if self._poll_timer is not None:
            self._poll_timer.cancel()

    def _check_sensor(self) -> None:
        try:
            with requests.get(self._url, headers=self._headers, verify=self._verify_certificate,
                              timeout=30) as response:
                response.raise_for_status()
                if response.json()['state'] == 'unavailable':
                    self._reload()
        except requests.exceptions.HTTPError:
            logger.warning('Failed to get sensor value')

        self._poll_timer = threading.Timer(self.poll_interval_seconds, self._check_sensor)
        self._poll_timer.start()
