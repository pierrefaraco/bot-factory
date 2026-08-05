from dataclasses import dataclass, asdict, field
from typing import Optional
from ai_server.dto.avatar_dto import AvatarDto
from ai_server.dto.bot_parameters_dto import BotParametersDto


@dataclass
class BotDto:
    id: int
    user_account_id: int
    avatar: Optional[AvatarDto] = None
    bot_parameters: Optional[BotParametersDto] = None

    def to_dict(self):
        result = asdict(self)

        # Convertir avatar en dict s'il existe
        if self.avatar:
            result["avatar"] = self.avatar.to_dict()

        # Convertir bot_parameters_dto en dict s'il existe
        if self.bot_parameters:
            result["bot_parameters"] = self.bot_parameters.to_dict()
            result.pop("bot_parameters_dto", None)

        return result

    def __str__(self):
        return f"BotDto(id={self.id}, user_account_id={self.user_account_id}, avatar={self.avatar}, bot_parameters={self.bot_parameters})"
