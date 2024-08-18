import ujson
from loguru import logger
from contextlib import suppress
from sqlalchemy.exc import IntegrityError

from creart import it
from kayaku import create
from avilla.core import BaseAccount
from graia.broadcast import Broadcast
from avilla.core.exceptions import InvalidAuthentication
from avilla.standard.core.account import AccountAvailable

from shared.database import get_interface
from shared.models.config import GlobalConfig
from shared.services.distribute import DistributeData, scene_dict
from shared.database.tables import PermissionLevel, UserPermission, User

bcc = it(Broadcast)


@bcc.receiver(AccountAvailable)
async def account_init(base_account: BaseAccount):
    logger.success("AccountAvailable")
    with suppress(InvalidAuthentication):
        await it(DistributeData).add_account(base_account)
    db = get_interface()
    land = base_account.route["land"]
    owner = create(GlobalConfig).owner_dict.get(land)
    if not owner:
        return
    async for scene in base_account.staff.query_entities(f"::{scene_dict[land]}"):
        scene = dict(scene.pattern)
        logger.error(str(scene))
        owner = ujson.dumps({**scene, "member": owner})
        with suppress(IntegrityError):
            _ = await db.update_or_add(User(data_json=owner, user_permission=UserPermission(level=PermissionLevel.OWNER.value)))
