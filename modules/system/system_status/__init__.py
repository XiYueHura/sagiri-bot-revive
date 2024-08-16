import psutil
from datetime import datetime

from creart import it
from graia.saya import Channel
from graiax.shortcut.saya import listen, dispatch, decorate
from avilla.core import Context, MessageReceived, MessageChain
from avilla.twilight.twilight import Twilight, ArgumentMatch, ArgResult

from shared.utils.time import sec_format
from shared.models.status import BotStatus
from shared.models.plugin import PluginMeta
from shared.utils.emitter import EmitterDispatcher
from shared.utils.control import Permission, PermissionLevel, Distribute

channel = Channel.current()
meta = PluginMeta.from_path(__file__)
channel.meta = meta.to_saya_meta()


@listen(MessageReceived)
@decorate(Permission.require(PermissionLevel.USER))
@decorate(Distribute.distribute())
@dispatch(EmitterDispatcher())
@dispatch(Twilight([
    meta.gen_match(),
    ArgumentMatch("-a", "-all", optional=True, action="store_true") @ "all_info",
    ArgumentMatch("-i", "-info", optional=True, action="store_true") @ "info",
    ArgumentMatch("-s", "-storage", optional=True, action="store_true") @ "storage"
]))
async def system_status(ctx: Context, all_info: ArgResult, info: ArgResult, storage: ArgResult):
    mem = psutil.virtual_memory()
    status = it(BotStatus)
    total_memery = round(mem.total / 1024 ** 3, 2)
    launch_time = status.launch_time
    launched_seconds = (datetime.now() - launch_time).seconds
    sent_count = status.sent_count
    received_count = status.received_count
    launch_time_message = MessageChain(
        "SAGIRI-BOT\n"
        f"启动时间：{launch_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"已运行时间：{sec_format((datetime.now() - launch_time).seconds, '{d}天{h}时{m}分{s}秒')}\n"
    )
    count_message = MessageChain(
        f"已接收消息：{received_count} ({round(received_count / launched_seconds, 2)}/s)\n"
        f"已发送消息：{sent_count} ({round(sent_count / launched_seconds, 2)}/s)\n"
    )
    memory_message = MessageChain(
        "内存相关：\n    "
        f"内存总大小：{total_memery}GB\n    "
        f"内存使用量：{round(mem.used / 1024 ** 3, 2)}GB / {total_memery}GB ({round(mem.used / mem.total * 100, 2)}%)\n    "
        f"内存空闲量：{round(mem.free / 1024 ** 3, 2)}GB / {total_memery}GB ({round(mem.free / mem.total * 100, 2)}%)\n"
    )
    cpu_message = MessageChain(
        "CPU相关：\n    "
        f"CPU 物理核心数：{psutil.cpu_count(logical=False)}\n    "
        f"CPU总体占用：{psutil.cpu_percent()}%\n    "
        f"CPU频率：{psutil.cpu_freq().current}MHz\n"
    )
    disk_usage = []
    for disk in psutil.disk_partitions():
        if not disk.fstype:
            continue
        usage = psutil.disk_usage(disk.device)
        disk_usage.append(f"<{disk.device}> {round(usage.used / 1024 ** 3, 2)}GB / {round(usage.total / 1024 ** 3, 2)}GB ({usage.percent}%)")
    disk_message = MessageChain(
        "磁盘相关：\n    "
        "磁盘占用空间：\n        " +
        "\n        ".join(disk_usage)
    )
    if all_info.matched or not info.matched and not storage.matched:
        await ctx.scene.send_message(launch_time_message + count_message + cpu_message + memory_message + disk_message)
    elif info.matched:
        await ctx.scene.send_message(launch_time_message + count_message + cpu_message + memory_message)
    else:
        await ctx.scene.send_message(launch_time_message + disk_message)
