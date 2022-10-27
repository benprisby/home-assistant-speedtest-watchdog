import dataclasses


@dataclasses.dataclass(kw_only=True)
class BaseConnection:
    address: str
    port: int

    def is_valid(self) -> bool:
        return bool(self.address) and self.port > 0 and self.port <= 65535


@dataclasses.dataclass(kw_only=True)
class HomeAssistantConnection(BaseConnection):
    port: int = 8123
    api_token: str
    https: bool = True
    verify_certificate: bool = True

    def is_valid(self) -> bool:
        return BaseConnection.is_valid(self) and bool(self.api_token)


@dataclasses.dataclass(kw_only=True)
class MqttConnection(BaseConnection):
    port: int = 1883
    username: str = ''
    password: str = ''

    def is_valid(self) -> bool:
        return BaseConnection.is_valid(self) and (not bool(self.username) or bool(self.password))
