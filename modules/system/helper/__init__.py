import jinja2
import random
import base64
from pathlib import Path
from typing import Mapping

from creart import it
from kayaku import create
from graia.saya import Channel, Saya
from avilla.core.resource import RawResource
from graiax.shortcut.saya import listen, dispatch, decorate
from avilla.twilight.twilight import Twilight, RegexMatch, ResultValue
from avilla.core import Context, Message, Picture, Selector, MessageReceived, MessageChain

from shared.models.plugin import PluginMeta
from shared.utils.text2img import template2img
from shared.models.plugin_data import PluginData
from shared.utils.models import selector2pattern
from shared.utils.control import (
    Blacklist,
    Function,
    FunctionCall
)

channel = Channel.current()
meta = PluginMeta.from_path(__file__)
channel.meta = meta.to_saya_meta()

env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(
        Path(__file__).parent / "templates"
    ),
    enable_async=True,
    autoescape=True,
)
TEMPLATE_PATH = Path(__file__).parent / "templates"
BANNER_PATH = Path(__file__).parent / "banners"

SceneType = Mapping[str, str] | Selector


def judge(plugin: str, scene: SceneType | str):
    if not isinstance(scene, str):
        scene = selector2pattern(scene)
    plugin_data = create(PluginData)
    if plugin not in plugin_data.switch:
        plugin_data.add_plugin(plugin)
    if scene not in plugin_data.switch[plugin]:
        plugin_data.add_scene(scene)
    return plugin_data.is_on(plugin, scene)


def random_pic(base_path: Path | str) -> str:
    base_path = Path(base_path)
    path_dir = list(base_path.glob("*"))
    return f"data:image/png;base64,{base64.b64encode(random.sample(path_dir, 1)[0].read_bytes()).decode()}"


@listen(MessageReceived)
@decorate(Function.require(channel.module))
@decorate(FunctionCall.record("help"))
@decorate(Blacklist.enable())
@dispatch(Twilight(meta.gen_match()))
async def helper(ctx: Context, message: Message):
    modules = []
    saya = it(Saya)
    scene = selector2pattern(message.scene)
    for i, c in enumerate(sorted(saya.channels)):
        plugin_meta = PluginMeta.from_module(c)
        modules.append((
            i + 1,
            plugin_meta.display_name or saya.channels[c].meta.get("name") or c.split(".")[-1],
            judge(c, scene),
            plugin_meta.maintaining or False
        ))

    if len(modules) % 3:
        modules.extend([(None, None, None, None) for _ in range(3 - len(modules) % 3)])
    img = await template2img(
        TEMPLATE_PATH / "plugins.html",
        {
            "settings": modules,
            "banner": random_pic(BANNER_PATH),
            "title": "SAGIRI-BOT帮助菜单",
            "subtitle": "CREATED BY SAGIRI-BOT Avilla-V5"
        }
    )
    await ctx.scene.send_message(Picture(RawResource(img)))


@listen(MessageReceived)
@decorate(Function.require(channel.module))
@decorate(FunctionCall.record("help_detail"))
@decorate(Blacklist.enable())
@dispatch(Twilight(meta.gen_match(), RegexMatch("[0-9]+$") @ "index"))
async def detail_helper(ctx: Context, message: Message, index: MessageChain = ResultValue()):
    index = int(str(index))
    saya = it(Saya)
    channels = sorted(saya.channels)
    if index > len(channels):
        return await ctx.scene.send_message(f"一共只有{len(channels)}个插件捏，怎么到你这里变成{index}了，真是的，太粗心了啦！", reply=message)
    elif index == 0:
        return await ctx.scene.send_message("0？我看你像个零！", reply=message)
    else:
        module = channels[index - 1]
        plugin_meta = PluginMeta.from_module(module)
        img = await template2img(
            (TEMPLATE_PATH / "plugin_detail.html").read_text(encoding="utf-8"),
            {
                "display_name": plugin_meta.display_name or saya.channels[module].meta.name,
                "module": module,
                "banner": random_pic(BANNER_PATH),
                "authors": plugin_meta.authors or ["暂无"],
                "description": plugin_meta.description or "暂无",
                "usage": "\n".join(plugin_meta.usage) or "暂无",
                "example": "\n".join(plugin_meta.example) or "暂无",
                "maintaining": plugin_meta.maintaining or False
            }
        )
        await ctx.scene.send_message(Picture(RawResource(img)))
