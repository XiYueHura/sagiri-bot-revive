import time
from abc import ABC
from typing import Type
from asyncio import Lock
from loguru import logger
from creart import add_creator, exists_module
from avilla.core import BaseAccount, Message, Selector
from creart.creator import AbstractCreator, CreateTargetInfo

from shared.utils.models import selector2pattern
from shared.utils.string import string_to_unique_number

scene_dict = {
    "qq": "group"
}


class DistributeData:
    """
    dict {
        land {
            scene: [account]
        }
    } 
    """
    data: dict[str, dict[str, list[str]]]
    inited_account: set[str]
    lock: Lock

    def __init__(self) -> None:
        self.data = {}
        self.inited_account = set()
        self.lock = Lock()

    async def add_account(self, base_account: BaseAccount):
        land = base_account.route["land"]
        account = base_account.route["account"]
        
        # 检查账户是否已经初始化，如果已初始化则直接返回，避免重复添加
        if account in self.inited_account:
            return
        
        _ = await self.add_land(land)
        if land not in scene_dict:
            logger.error(f"暂不支持的协议：{land}")
            return
        async for scene in base_account.staff.query_entities(f"::{scene_dict[land]}"):
            scene = selector2pattern(scene)
            async with self.lock:
                if scene in self.data[land]:
                    if account not in self.data[land][scene]:
                        self.data[land][scene].append(account)
                else:
                    self.data[land][scene] = [account]
        
        # 只在首次添加时标记为已初始化并记录日志
        self.inited_account.add(account)
        logger.warning(self.data)
        logger.success(f"DistributeData 成功添加账号{account}<{land}>")

    async def add_land(self, land: str):
        async with self.lock:
            if land not in self.data:
                self.data[land] = {}

    async def add_scene(self, scene: Selector | str, land: str, account: str | None):
        if isinstance(scene, Selector):
            scene = selector2pattern(scene)
        _ = await self.add_land(land)
        async with self.lock:
            if scene not in self.data[land]:
                self.data[land][scene] = [account] if account else []

    def need_distribute(self, land: str, scene: Selector | str) -> bool:
        if isinstance(scene, Selector):
            scene = selector2pattern(scene)
        if land in self.data and scene in self.data[land]:
            return len(self.data[land][scene]) > 1
        return False

    def get_index(self, base_account: BaseAccount, scene: Selector | str) -> int:
        land = base_account.route["land"]
        account = base_account.route["account"]
        scene = selector2pattern(scene) if isinstance(scene, Selector) else scene
        if land in self.data and scene in self.data[land] and account in self.data[land][scene]:
            return self.data[land][scene].index(account)
        print(self.data)
        raise ValueError

    def account_initialized(self, account: str):
        return account in self.inited_account

    async def execution_stop(self, base_account: BaseAccount, scene: Selector | str, 
                             message: Message | None = None) -> bool:
        scene = selector2pattern(scene) if isinstance(scene, Selector) else scene
        land = base_account.route["land"]
        account = base_account.route["account"]
        if land not in self.data:
            _ = await self.add_land(land)
            return True
        if scene not in self.data[land]:
            _ = await self.add_scene(scene, land, account)
            return True
        
        # 获取场景对应的账号列表
        scene_accounts = self.data[land][scene]
        
        # 检查列表是否为空，避免除零错误
        if len(scene_accounts) == 0:
            # 如果列表为空，确保当前账号被添加进去
            _ = await self.add_scene(scene, land, account)
            return True
            
        # 确保当前账号在列表中
        if account not in scene_accounts:
            scene_accounts.append(account)
        
        try:
            # 安全地进行模运算
            return int(time.mktime(message.time.timetuple())) % len(scene_accounts) != self.get_index(base_account, scene)
        except (ValueError, KeyError):
            # 处理可能的异常，确保消息能正常处理
            return True

    async def is_bot(self, base_account: BaseAccount, message: Message) -> bool:
        scene = selector2pattern(message.scene)
        land = base_account.route["land"]
        if land not in self.data:
            _ = await self.add_land(land)
        if scene not in self.data[land]:
            _ = await self.add_scene(scene, land, None)
        
        # 兼容不同类型的消息（好友消息、群消息等）
        sender_pattern = message.sender.pattern
        # 尝试获取发送者ID，根据不同消息类型使用不同的键
        if "member" in sender_pattern:
            sender = sender_pattern["member"]
        elif "friend" in sender_pattern:
            sender = sender_pattern["friend"]
        else:
            # 回退到获取第一个可用的值
            sender = next(iter(sender_pattern.values()), None)
            
        if sender and sender in self.data[land][scene]:
            return True
        return False


class DistributeDataClassCreator(AbstractCreator, ABC):
    targets = (CreateTargetInfo("shared.services.distribute", "DistributeData"),)

    @staticmethod
    def available() -> bool:
        return exists_module("shared.services.distribute")

    @staticmethod
    def create(create_type: Type[DistributeData]) -> DistributeData:
        return DistributeData()


add_creator(DistributeDataClassCreator)
