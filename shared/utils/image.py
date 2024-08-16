import ssl
import hashlib
from typing import Literal

import aiohttp
from avilla.core.elements import Picture


def get_image_type(data: bytes) -> Literal["JPEG", "PNG", "GIF", "BMP", "Unknown"]:
    if data.startswith(b"\xFF\xD8"):
        return "JPEG"
    elif data.startswith(b"\x89\x50\x4E\x47"):
        return "PNG"
    elif data.startswith(b"\x47\x49\x46\x38"):
        return "GIF"
    elif data.startswith(b"\x42\x4D"):
        return "BMP"
    else:
        return "Unknown"


def get_md5(raw: bytes) -> str:
    md5_hash = hashlib.md5()
    md5_hash.update(raw)
    return md5_hash.hexdigest().upper()


async def download_picture(picture: Picture) -> bytes:
    img_url = picture.resource.url
    async with aiohttp.ClientSession() as session:
        ssl_context = None
        if "multimedia.nt.qq.com.cn" in img_url:
            ssl_context = ssl.create_default_context()
            ssl_context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_TLSv1_3
            ssl_context.set_ciphers("HIGH:!aNULL:!MD5")
        async with session.get(img_url, ssl=ssl_context) as resp:
            return await resp.read()
