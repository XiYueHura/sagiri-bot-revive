import asyncio
from pathlib import Path
from loguru import logger

from creart import it
from kayaku import create
from graia.saya import Channel
from graia.broadcast import Broadcast
from avilla.core.resource import RawResource
from avilla.core.event import RelationshipCreated
from graia.broadcast.interrupt import InterruptControl
from graiax.shortcut.saya import listen, decorate, dispatch
from avilla.core import Context, Message, Summary, Notice, MessageReceived, MessageChain, Picture
from avilla.twilight.twilight import Twilight, FullMatch, ElementMatch, ResultValue, RegexMatch, ElementResult

from .utils import gen_verification
from shared.models.plugin import PluginMeta
from shared.utils.emitter import EmitterDispatcher
from shared.utils.waiter import MessageWaiter, PictureWaiter
from shared.utils.image import get_md5, get_image_type, download_picture
from .models import AuthenticatorConfig, AuthenticatorSwitch, Authenticator
from shared.utils.control import SceneSwitch, Function, FunctionCall, Permission, PermissionLevel, Distribute

channel = Channel.current()
meta = PluginMeta.from_path(__file__)
channel.meta = meta.to_saya_meta()
create(AuthenticatorConfig)
create(AuthenticatorSwitch)
authenticator_path = Path.cwd() / "resources" / "authenticator"
authenticator_path.mkdir(parents=True, exist_ok=True)


@listen(RelationshipCreated)
@decorate(SceneSwitch.check())
@decorate(Function.require(channel.module))
@decorate(Distribute.distribute())
@dispatch(EmitterDispatcher())
async def scene_entrance_authenticator(ctx: Context):
    if not create(AuthenticatorSwitch).is_on(ctx.scene):
        return
    authenticator = create(AuthenticatorConfig, flush=True).get_authenticator()
    if not authenticator:
        logger.error("尚未配置任何Authenticator！")
        return
    group_name = (await ctx.pull(Summary, ctx.scene)).name
    _ = await ctx.scene.send_message(
        MessageChain([
            Notice(ctx.client),
            f"欢迎加入群{group_name}，请您完成下面的认证\n",
            "下图共有16个小图，小图编号及位置如下：\n",
            "A B C D\n",
            "E F G H\n",
            "I J K L\n",
            "M N O P\n",
            "请按照下图要求输入对应的图片代码，如AEHI（不区分大小写），您有3次机会，每次机会有45秒的思考时间：\n",
            Picture(RawResource(await asyncio.to_thread(authenticator.gen_verify_image)))
        ])
    )
    count = 3
    while count:
        received_message = await asyncio.wait_for(InterruptControl(it(Broadcast)).wait(MessageWaiter(ctx.client)), 45)
        if authenticator.verify(str(received_message)):
            return await ctx.scene.send_message("恭喜您，回答正确，验证通过")
        count -= 1
        _ = await ctx.scene.send_message(f"抱歉，您的回答有误，请仔细思考并重新发送您的答案，您还有{count}次机会")
    await ctx.scene.send_message(f"抱歉，您的回答有误，您已经用光3次机会，将把您移出该场景...")


@listen(MessageReceived)
@decorate(Permission.require(PermissionLevel.USER))
@decorate(Distribute.distribute())
@dispatch(EmitterDispatcher())
@dispatch(Twilight(
    FullMatch("添加验证"),
    FullMatch("#"),
    RegexMatch(r"[\w\W]+") @ "name", 
    FullMatch("#"),
    ElementMatch(Picture, optional=True) @ "image"
))
async def add_image(ctx: Context, message: Message, image: ElementResult, name: MessageChain = ResultValue()):
    name = str(name).strip()
    if not image.matched:
        image = await asyncio.wait_for(InterruptControl(it(Broadcast)).wait(PictureWaiter(message)), 30)
        if not image:
            return await ctx.scene.send_message("未检测到图片，请重新发送，进程退出", reply=message)
        image = image[0]
    else:
        image = image.result
    raw = await download_picture(image)
    md5, img_type = get_md5(raw), get_image_type(raw)
    path = authenticator_path / f"{md5}.{img_type}"
    path.write_bytes(raw)
    create(AuthenticatorConfig).add_authenticator(Authenticator(name, str(path.absolute().as_posix())))
    await ctx.scene.send_message(MessageChain(["图片添加成功，请前往后台编写配置，生成验证图如下：\n", Picture(RawResource(await asyncio.to_thread(gen_verification, name, raw)))]), reply=message)


@listen(MessageReceived)
@decorate(Permission.require(PermissionLevel.USER))
@decorate(Distribute.distribute())
@dispatch(EmitterDispatcher())
@dispatch(Twilight(
    FullMatch("生成谷歌验证码"),
    FullMatch("#"),
    RegexMatch(".*") @ "title",
    FullMatch("#"),
    RegexMatch("\r?\n?\r?"),
    ElementMatch(Picture, optional=True) @ "image"
))
async def test_gen_images(ctx: Context, message: Message, title: ElementResult, image: ElementResult):
    if image.matched:
        raw = await download_picture(image.result)
        title = title.result.content[0].text if title.matched else "title"
        await ctx.scene.send_message(Picture(RawResource(await asyncio.to_thread(gen_verification, title, raw))), reply=message)
