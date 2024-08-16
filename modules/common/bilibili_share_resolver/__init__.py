"""
识别群内的B站链接、分享、av号、BV号并获取其对应的视频的信息

以下几种消息均可触发

 - 新版B站app分享的两种小程序
 - 旧版B站app分享的xml消息
 - B站概念版分享的json消息
 - 文字消息里含有B站视频地址，如 https://www.bilibili.com/video/{av/bv号} （m.bilibili.com 也可以
 - 文字消息里含有B站视频地址，如 https://b23.tv/3V31Ap
 - 文字消息里含有B站视频地址，如 https://b23.tv/3V31Ap
 - BV1xx411c7mD
 - av2
"""

import re
import time
from io import BytesIO
from pathlib import Path
from loguru import logger
from typing import Literal
from PIL.Image import Image
from base64 import b64encode
from qrcode.main import QRCode
from dataclasses import dataclass

from launart import Launart
from graia.saya import Channel
from avilla.core.resource import RawResource
from avilla.core.elements import Picture, Text
from avilla.core import Context, MessageReceived
from graiax.text2img.playwright import PageOption
from graiax.shortcut.saya import listen, decorate, dispatch

from shared.utils.text2img import template2img
from shared.utils.emitter import EmitterDispatcher
from shared.services.aiohttp import AiohttpClientInterface
from shared.utils.control import SceneSwitch, FunctionCall, Function, Distribute

channel = Channel.current()

channel.meta['name'] = 'B站视频信息获取'
channel.meta['author'] = ['Red_lnn']
channel.meta['description'] = (
    '识别群内的B站链接、分享、av号、BV号并获取其对应的视频的信息\n'
    '以下几种消息均可触发：\n'
    ' - 新版B站app分享的两种小程序\n'
    ' - 旧版B站app分享的xml消息\n'
    ' - B站概念版分享的json消息\n'
    ' - 文字消息里含有B站视频地址，如 https://www.bilibili.com/video/{av/bv号} （m.bilibili.com 也可以）\n'
    ' - 文字消息里含有B站视频地址，如 https://b23.tv/3V31Ap\n'
    ' - 文字消息里含有BV号，如 BV1xx411c7mD\n'
    ' - 文字消息里含有av号，如 av2'
)

avid_re = '(av|AV)(\\d{1,12})'
bvid_re = '[Bb][Vv]1([0-9a-zA-Z]{2})4[1y]1[0-9a-zA-Z]7([0-9a-zA-Z]{2})'


@dataclass
class VideoInfo:
    cover_url: str  # 封面地址
    bvid: str  # BV号
    avid: int  # av号
    title: str  # 视频标题
    sub_count: int  # 视频分P数
    pub_timestamp: int  # 视频发布时间（时间戳）
    upload_timestamp: int  # 视频上传时间（时间戳，不一定准确）
    desc: str  # 视频简介
    duration: int  # 视频长度（单位：秒）
    up_mid: int  # up主mid
    up_name: str  # up主名称
    up_face: str  # up主头像地址
    views: int  # 播放量
    danmu: int  # 弹幕数
    likes: int  # 点赞数
    coins: int  # 投币数
    replys: int  # 评论数
    favorites: int  # 收藏量


@listen(MessageReceived)
@decorate(Distribute.distribute())
@decorate(SceneSwitch.check())
@decorate(Function.require(channel.module))
@decorate(FunctionCall.record("bilibili_share_resolver"))
@dispatch(EmitterDispatcher())
async def main(ctx: Context, event: MessageReceived):
    message = str(event.message.content)
    p = re.compile(f'({avid_re})|({bvid_re})')
    if 'b23.tv/' in message:
        message = await b23_url_extract(message)
        if not message:
            return
    video_id = p.search(message)
    if not video_id or video_id is None:
        return
    video_id = video_id.group()
    video_info = await get_video_info(video_id)
    if video_info['code'] == -404:
        return await ctx.scene.send_message('视频不存在')
    elif video_info['code'] != 0:
        error_text = f'解析B站视频 {video_id} 时出错👇\n错误代码：{video_info["code"]}\n错误信息：{video_info["message"]}'  # noqa
        logger.error(error_text)
        return await ctx.scene.send_message(error_text)
    else:
        video_info = await info_json_dump(video_info['data'])
        img: bytes = await gen_img(video_info)
        await ctx.scene.send_message(
            [
                Picture(resource=RawResource(img)),
                Text(
                    f'{video_info.title}\n'
                    '—————————————\n'
                    f'UP主：{video_info.up_name}\n'
                    f'{math(video_info.views)}播放 {math(video_info.likes)}赞\n'
                    f'链接：https://b23.tv/{video_info.bvid}',
                ),
            ]
        )


async def b23_url_extract(b23_url: str) -> Literal[False] | str:
    url = re.search(r'b23.tv[/\\]+([0-9a-zA-Z]+)', b23_url)
    if url is None:
        return False

    launart = Launart.current()
    session = launart.get_interface(AiohttpClientInterface).service.session

    async with session.get(f'https://{url.group()}', allow_redirects=True) as resp:
        target = str(resp.url)
    return target if 'www.bilibili.com/video/' in target else False


async def get_video_info(video_id: str) -> dict:
    launart = Launart.current()
    session = launart.get_interface(AiohttpClientInterface).service.session

    if video_id[:2].lower() == 'av':
        async with session.get(f'http://api.bilibili.com/x/web-interface/view?aid={video_id[2:]}') as resp:
            return await resp.json()
    elif video_id[:2].lower() == 'bv':
        async with session.get(f'http://api.bilibili.com/x/web-interface/view?bvid={video_id}') as resp:
            return await resp.json()
    return {}


async def info_json_dump(obj: dict) -> VideoInfo:
    return VideoInfo(
        cover_url=obj['pic'],
        bvid=obj['bvid'],
        avid=obj['aid'],
        title=obj['title'],
        sub_count=obj['videos'],
        pub_timestamp=obj['pubdate'],
        upload_timestamp=obj['ctime'],
        desc=obj['desc'].strip(),
        duration=obj['duration'],
        up_mid=obj['owner']['mid'],
        up_name=obj['owner']['name'],
        up_face=obj['owner']['face'],
        views=obj['stat']['view'],
        danmu=obj['stat']['danmaku'],
        likes=obj['stat']['like'],
        coins=obj['stat']['coin'],
        replys=obj['stat']['reply'],
        favorites=obj['stat']['favorite'],
    )


def math(num: int):
    if num < 10000:
        return str(num)
    elif num < 100000000:
        return ('%.2f' % (num / 10000)) + '万'
    else:
        return ('%.2f' % (num / 100000000)) + '亿'


template = (Path(__file__).parent / "template.html").read_text(encoding='utf-8')


async def gen_img(data: VideoInfo) -> bytes:
    video_length_m, video_length_s = divmod(data.duration, 60)  # 将总的秒数转换为时分秒格式
    video_length_h, video_length_m = divmod(video_length_m, 60)
    if video_length_h == 0:
        video_length = f'{video_length_m}:{video_length_s}'
    else:
        video_length = f'{video_length_h}:{video_length_m}:{video_length_s}'

    desc = data.desc.strip().replace('\n', '<br/>')

    launart = Launart.current()
    session = launart.get_interface(AiohttpClientInterface).service.session

    async with session.get(f'https://api.bilibili.com/x/relation/stat?vmid={data.up_mid}') as resp:
        result = await resp.json()
        fans_num: int = result['data']['follower']

    qr = QRCode(version=2, box_size=4)
    qr.add_data(f'https://b23.tv/{data.bvid}')
    qr.make()
    qrcode: Image | None = qr.make_image()._img
    if qrcode is None:
        qrcode_src = ''
    else:
        output_buffer = BytesIO()
        qrcode.save(output_buffer, format='png')
        base64_str = b64encode(output_buffer.getvalue()).decode('utf-8')
        qrcode_src = f'data:image/png;base64,{base64_str}'

    return await template2img(
        template,
        {
            'cover_src': data.cover_url,
            'duration': video_length,
            'title': data.title,
            'play_num': math(data.views),
            'danmaku_num': math(data.danmu),
            'reply_num': math(data.replys),
            'like_num': math(data.likes),
            'coin_num': math(data.coins),
            'favorite_num': math(data.favorites),
            'desc': desc,
            'publish_time': time.strftime('%Y/%m/%d %p %I:%M:%S', time.localtime(data.upload_timestamp)),
            'profile_src': data.up_face,
            'name': data.up_name,
            'fans_num': math(fans_num),
            'qrcode_src': qrcode_src,
        },
        extra_page_option=PageOption(viewport={'width': 960, 'height': 10}),
    )
