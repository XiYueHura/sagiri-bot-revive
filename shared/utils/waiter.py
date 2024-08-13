from typing import Type, Mapping

from graia.amnesia.message import Element
from graia.broadcast.interrupt.waiter import Waiter
from avilla.core import MessageChain, Picture, MessageReceived, Message, Selector

from shared.utils.models import selector2pattern

SelectorType = Selector | Mapping[str, str]


class ConfirmWaiter(Waiter.create([MessageReceived])):

    def __init__(self, message: Message | SelectorType, confirm_words: list[str] | None = None):
        self.sender = selector2pattern(message.sender if isinstance(message, Message) else message)
        self.confirm_words = confirm_words or ["是", "y", "yes", "确认"]

    async def detected_event(self, message: Message):
        if self.sender == selector2pattern(message.sender):
            return str(message.content).strip() in self.confirm_words


class MessageWaiter(Waiter.create([MessageReceived])):

    def __init__(self, message: Message | SelectorType):
        self.sender = selector2pattern(message.sender if isinstance(message, Message) else message)

    async def detected_event(self, message: Message) -> MessageChain:
        if self.sender == selector2pattern(message.sender):
            return message.content


class PictureWaiter(Waiter.create([MessageReceived])):

    def __init__(self, message: Message | SelectorType):
        self.sender = selector2pattern(message.sender if isinstance(message, Message) else message)

    async def detected_event(self, message: Message) -> list[Picture]:
        if self.sender == selector2pattern(message.sender):
            return message.content.get(Picture)


class ElementWaiter(Waiter.create([MessageReceived])):

    def __init__(self, message: Message | SelectorType, element_type: Type[Element]):
        self.sender = selector2pattern(message.sender if isinstance(message, Message) else message)
        self.element_type = element_type

    async def detected_event(self, message: Message) -> list[Element]:
        if self.sender == selector2pattern(message.sender):
            return message.content.get(self.element_type)
