import logging
import requests

import watchdog.connections

logger = logging.getLogger(__name__)


class IntegrationReloader:

    def __init__(self, connection: watchdog.connections.HomeAssistantConnection, config_entry_id: str) -> None:
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
        except requests.exceptions.HTTPError:
            return False
