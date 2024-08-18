from contextlib import suppress
from sqlalchemy.exc import IntegrityError

from kayaku import create
from avilla.core import Avilla
from launart import Launart, Service

from shared.database import get_interface
from shared.models.config import GlobalConfig
from shared.models.permission import PermissionLevel
from shared.database.tables import UserPermission, User


class PermissionInitService(Service):
    id = "sagiri.service.launch_time"

    @property
    def required(self):
        return set()

    @property
    def stages(self):
        return {"blocking"}

    async def launch(self, _mgr: Launart):
        async with self.stage("blocking"):
            db = get_interface()
            owner = create(GlobalConfig).owner
            avilla = Avilla.current()
            for account in avilla.accounts:
                async for scene in account:
                    with suppress(IntegrityError):
                        _ = await get_interface().update_or_add(UserPermission(level=int(PermissionLevel.OWNER.value)))
