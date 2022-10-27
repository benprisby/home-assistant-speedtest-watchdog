import logging
import paho.mqtt.client
import socket
import threading
import typing

import watchdog.integration_reloader

logger = logging.getLogger(__name__)


class SensorMonitor:

    def __init__(self,
                 reloader: watchdog.integration_reloader.IntegrationReloader,
                 sensor_name: str,
                 mqtt_address: str = 'localhost',
                 mqtt_port: int = 1883,
                 mqtt_username: str = '',
                 mqtt_password: str = ''):
        self.reloader = reloader
        self.sensor_name = sensor_name

        self.mqtt_address = mqtt_address
        self.mqtt_port = mqtt_port

        self._mqtt_client = paho.mqtt.client.Client('integration-monitor')
        self._mqtt_client.on_connect = self._handle_connect
        self._mqtt_client.on_disconnect = self._handle_disconnect
        self._mqtt_client.on_message = self._handle_message
        if mqtt_username and mqtt_password:
            self._mqtt_client.username_pw_set(mqtt_username, mqtt_password)

        self._backoff_timer: typing.Optional[threading.Timer] = None

        logger.debug('Initialized sensor monitor for %s on MQTT broker at: %s', self.sensor_name, self.mqtt_address)

    def run(self, stop_signal: threading.Event) -> None:
        if stop_signal.is_set():
            raise RuntimeError('Stop signal already set when trying to run monitor')
        try:
            self._mqtt_client.connect(self.mqtt_address, self.mqtt_port)
        except socket.gaierror:
            logger.warning('Failed to find MQTT broker at: %s', self.mqtt_address)
        except TimeoutError:
            logger.warning('Timed out trying to connect to MQTT broker at: %s', self.mqtt_address)
        self._mqtt_client.loop_start()
        stop_signal.wait()
        self._mqtt_client.disconnect()
        self._mqtt_client.loop_stop()
        if self._backoff_timer is not None:
            self._backoff_timer.cancel()

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
            if self._backoff_timer is None or self._backoff_timer.finished.is_set():
                logger.debug('Sensor died')
                if self.reloader.reload():
                    logger.info('Successfully reloaded integration')
                    self._backoff_timer = threading.Timer(60.0, lambda: None)
                    self._backoff_timer.start()
                else:
                    logger.warning('Failed to reload integration')
            else:
                logger.debug('Waiting for backoff timer to complete')
