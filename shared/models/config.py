from pathlib import Path

from kayaku import config
from typing import Literal
from dataclasses import dataclass, field, asdict


PROTOCOLS = Literal["mirai_api_http", "onebot_v11", "onebot_v12", "telegram", "discord", "qqguild", "red", "kook"]


@dataclass
class MiraiApiHttpAccount:
    qq: int = 0
    host: str = "localhost"
    port: int = 23456
    access_token: str = "1234567890"


@dataclass
class MiraiApiHttpConfig:
    host: int = field(default_factory=int)
    accounts: list[MiraiApiHttpAccount] = field(default_factory=lambda: [asdict(MiraiApiHttpAccount())])


@dataclass
class OnebotV11Account:
    endpoint: str = field(default_factory=str)
    access_token: str = field(default_factory=str)


@dataclass
class OnebotV11Config:
    accounts: list[OnebotV11Account] = field(default_factory=lambda: [asdict(OnebotV11Account())])


@dataclass
class LoggerSetting:
    error_retention: int = 14
    common_retention: int = 7
    enable_chain_log: bool = False
    chain_log_path: str = str(Path(__file__).parent.parent.parent / "log")


@dataclass
class MysqlAdapter:
    disable_pooling: bool = False
    pool_size: int = 40
    max_overflow: int = 60


@dataclass
class DatabaseSetting:
    db_link: str = "sqlite+aiosqlite:///data.db"
    mysql: MysqlAdapter = field(default_factory=MysqlAdapter)


@config("config")
class GlobalConfig:
    protocols: list[PROTOCOLS] = field(default_factory=list)
    mirai_api_http: MiraiApiHttpConfig = field(default_factory=MiraiApiHttpConfig)
    onebot_v11: OnebotV11Config = field(default_factory=OnebotV11Config)
    logger_setting: LoggerSetting = field(default_factory=LoggerSetting)
    database_setting: DatabaseSetting = field(default_factory=DatabaseSetting)
    proxy: str = field(default_factory=str)
    auto_upgrade: bool = field(default=False)
