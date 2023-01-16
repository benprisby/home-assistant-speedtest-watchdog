"""Home Assistant integration reloader."""

import logging
import requests

import bdp.homeassistant.speedtestwatchdog.connections

logger = logging.getLogger(__name__)


class IntegrationReloader:
    """Class to handle making requests to a Home Assistant server to reload an integration using its entry ID."""

    def __init__(self, connection: bdp.homeassistant.speedtestwatchdog.connections.HomeAssistantConnection,
                 config_entry_id: str) -> None:
        if not connection.is_valid():
            raise RuntimeError('Invalid connection configuration for reloader')
        if not config_entry_id:
            raise RuntimeError('Empty config entry ID when trying to initialize reloader')

        scheme = 'https' if connection.https else 'http'
        self._url = f'{scheme}://{connection.address}:{connection.port}/api/services/homeassistant/reload_config_entry'
        self._headers = {'Authorization': f'Bearer {connection.api_token}'}
        self._payload = {'entry_id': config_entry_id}
        self._verify_certificate = connection.verify_certificate

        logger.debug('Initialized reloader for Home Assistant server at: %s:%d', connection.address, connection.port)

    def reload(self) -> bool:
        try:
            with requests.post(self._url,
                               headers=self._headers,
                               json=self._payload,
                               verify=self._verify_certificate,
                               timeout=30) as response:
                response.raise_for_status()
                return True
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError, requests.exceptions.Timeout):
            return False
