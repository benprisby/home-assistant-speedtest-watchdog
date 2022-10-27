import logging
import requests

logger = logging.getLogger(__name__)


class IntegrationReloader:

    def __init__(self,
                 address: str,
                 port: int,
                 api_token: str,
                 entry_id: str,
                 https: bool = True,
                 verify_certificate: bool = False) -> None:
        scheme = 'https' if https else 'http'
        self._url = f'{scheme}://{address}:{port}/api/services/homeassistant/reload_config_entry'
        self._headers = {'Authorization': f'Bearer {api_token}'}
        self._payload = {'entry_id': entry_id}
        self._verify = verify_certificate

        logger.debug('Initialized reloader for server at: %s', address)

    def reload(self) -> bool:
        try:
            response = requests.post(self._url,
                                     headers=self._headers,
                                     json=self._payload,
                                     verify=self._verify,
                                     timeout=30)
            response.raise_for_status()
            return True
        except requests.exceptions.HTTPError:
            return False
