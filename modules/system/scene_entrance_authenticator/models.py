import re
import random
from pathlib import Path
from typing import Mapping
from dataclasses import dataclass, field

import kayaku
from kayaku import config
from avilla.core import Selector

from .utils import gen_verification
from shared.utils.models import selector2pattern

SceneType = Selector | Mapping[str, str]
DEFAULT_SWITCH = False


@dataclass
class Authenticator:
    name: str = ""
    image_path: str = ""
    required: list[str] = field(default_factory=list)
    optional: list[str] = field(default_factory=list)

    def __post_init__(self):
        super().__init__()
        if not self.required or self.optional:
            self.pattern = None
            return
        pattern = "".join(sorted(list(set(self.required + self.optional))))
        if not pattern:
            return
        for i in self.optional:
            pattern.replace(i, f"{i}?")
        self.pattern = re.compile(f"^{pattern.lower()}$")

    def verify(self, answer: str) -> bool:
        answer = "".join(sorted(answer)).lower()
        return bool(self.pattern.match(answer)) if self.pattern else True

    def gen_verify_image(self) -> bytes:
        raw = Path(self.image_path).read_bytes()
        return gen_verification(self.name, raw)


@config("modules.authenticator")
class AuthenticatorConfig:
    authenticators: list[Authenticator] = field(default_factory=list)

    def add_authenticator(self, authenticator: Authenticator):
        self.authenticators.append(authenticator)
        kayaku.save(self.__class__)

    def get_authenticator(self) -> Authenticator | None:
        if not self.authenticators:
            return None
        return random.choice(self.authenticators)


@config("modules.control.authenticator_switch")
class AuthenticatorSwitch:
    switch: dict[str, bool] = field(default_factory=dict)

    def add_scene(self, scene: SceneType | str):
        if not isinstance(scene, str):
            scene = selector2pattern(scene)
        if scene not in self.switch:
            self.switch[scene] = DEFAULT_SWITCH
        kayaku.save(self.__class__)
    
    def is_on(self, scene: SceneType) -> bool:
        if not isinstance(scene, str):
            scene = selector2pattern(scene)
        self.add_scene(scene)
        return self.switch[scene]

    def _change_switch(self, scene: SceneType | str, value: bool):
        if not isinstance(scene, str):
            scene = selector2pattern(scene)
        self.add_scene(scene)
        self.switch[scene] = value
        kayaku.save(self.__class__)
    
    def switch_on(self, scene: SceneType | str):
        self._change_switch(scene, True)
    
    def switch_off(self, scene: SceneType | str):
        self._change_switch(scene, False)
