from abc import ABC
from typing import Type
from datetime import datetime
from collections import defaultdict

from avilla.core import Selector
from creart import add_creator, exists_module
from creart.creator import AbstractCreator, CreateTargetInfo

from shared.utils.models import selector2pattern


class BotStatus:
    launch_time: datetime
    sent_count: int
    received_count: int
    scene_receive_count: dict
    scene_sent_count: dict
    
    def __init__(self, launch_time: datetime | None = None, sent_count: int = 0, received_count: int = 0) -> None:
        self.launch_time = launch_time or datetime.now()
        self.sent_count = sent_count
        self.received_count = received_count
        self.scene_receive_count = defaultdict(lambda: defaultdict(int))
        self.scene_sent_count = defaultdict(lambda: defaultdict(int))
    
    def received(self, scene: Selector | str):
        scene = selector2pattern(scene) if isinstance(scene, Selector) else scene
        self.received_count += 1
        self.scene_receive_count[datetime.now().strftime("%Y-%m-%d %H:%M:%S")][scene] += 1
    
    def sent(self, scene: Selector | str):
        self.sent_count += 1
        scene = selector2pattern(scene) if isinstance(scene, Selector) else scene
        self.scene_sent_count[datetime.now().strftime("%Y-%m-%d %H:%M:%S")][scene] += 1


class BotStatusClassCreator(AbstractCreator, ABC):
    targets = (CreateTargetInfo("shared.models.status", "BotStatus"),)

    @staticmethod
    def available() -> bool:
        return exists_module("shared.models.status")

    @staticmethod
    def create(create_type: Type[BotStatus]) -> BotStatus:
        return BotStatus()


add_creator(BotStatusClassCreator)
