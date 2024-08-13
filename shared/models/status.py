from abc import ABC
from typing import Type
from datetime import datetime

from creart import add_creator, exists_module, create
from creart.creator import AbstractCreator, CreateTargetInfo


class BotStatus:
    launch_time: datetime
    sent_count: int
    received_count: int
    
    def __init__(self, launch_time: datetime | None = None, sent_count: int = 0, received_count: int = 0) -> None:
        self.launch_time = launch_time or datetime.now()
        self.sent_count = sent_count
        self.received_count = received_count
    
    def received(self):
        self.received_count += 1
    
    def sent(self):
        self.sent_count += 1


class BotStatusClassCreator(AbstractCreator, ABC):
    targets = (CreateTargetInfo("shared.models.status", "BotStatus"),)

    @staticmethod
    def available() -> bool:
        return exists_module("shared.models.status")

    @staticmethod
    def create(create_type: Type[BotStatus]) -> BotStatus:
        return BotStatus()


add_creator(BotStatusClassCreator)
