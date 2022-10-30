"""Data models for connection information."""

import dataclasses


@dataclasses.dataclass()
class BaseConnection:
    address: str
    port: int

    def is_valid(self) -> bool:
        return bool(self.address) and self.port > 0 and self.port <= 65535


@dataclasses.dataclass()
class HomeAssistantConnection(BaseConnection):
    port: int = 8123
    https: bool = True
    verify_certificate: bool = True
    api_token: str = ''  # BDP: Must have default argument until bumping to Python 3.10, where kw_only is available

    def is_valid(self) -> bool:
        return BaseConnection.is_valid(self) and bool(self.api_token)


@dataclasses.dataclass()
class MqttConnection(BaseConnection):
    port: int = 1883
    username: str = ''
    password: str = ''

    def is_valid(self) -> bool:
        return BaseConnection.is_valid(self) and (not bool(self.username) or bool(self.password))
