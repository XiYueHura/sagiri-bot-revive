import uuid
import json
import aiofiles
from enum import Enum
from pathlib import Path
from asyncio import Lock
from datetime import datetime

from kayaku import create
from avilla.core import Selector
from graia.broadcast.entities.event import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface

from shared.models.config import GlobalConfig
from shared.utils.models import selector2pattern

lock = Lock()


class LogLevel(Enum):
    INFO = "INFO"
    DEBUG = "DEBUG"
    WARNING = "WARNING"
    ERROR = "ERROR"


class EmitterDispatcher(BaseDispatcher):

    async def beforeExecution(self, interface: DispatcherInterface):
        interface.local_storage["emitter"] = Emitter()

    async def catch(self, interface: DispatcherInterface):
        return interface.local_storage["emitter"]

    async def afterExecution(self, interface: DispatcherInterface, *args):
        await interface.local_storage["emitter"].done()


class Emitter:
    def __init__(self, entry_point: str = ""):
        # land: str, scene: Selector | str,
        self.create_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        base_log_path = Path(create(GlobalConfig).logger_setting.chain_log_path) / datetime.now().strftime('%Y-%m-%d') / "chain_log"
        base_log_path.mkdir(parents=True, exist_ok=True)
        self.base_log_path = base_log_path
        self.entry_point = entry_point
        self.uuid = uuid.uuid4()
        self.chain = []
        self.level = LogLevel.INFO

    def emit(self, entry_point: str, content: str = "", params: dict = None):
        params = params or {}
        data = {
            "emit_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "entry_point": entry_point
        }
        if content:
            data["content"] = content
        if params:
            data["params"] = params
        self.chain.append(json.dumps(data, ensure_ascii=False))

    def set_level(self, level: LogLevel):
        self.level = level

    async def done(self):
        if not self.chain:
            return
        async with lock:
            level = self.level.value
            log_path = self.base_log_path / f"{level}.log"
            if not log_path.exists():
                async with aiofiles.open(log_path, "w", encoding="utf-8") as f:
                    await f.write("")
            async with aiofiles.open(log_path, "a", encoding="utf-8") as f:
                data = {
                    "uuid": str(self.uuid),
                    "level": self.level.value,
                    "create_time": self.create_time,
                    "entry_point": self.entry_point,
                    "chain": self.chain
                }
                await f.write(json.dumps(data, ensure_ascii=False) + "\n")
