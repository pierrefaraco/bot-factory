from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class BotParametersDto:
    id: int
    bot_id: int
    bot_name: str
    bot_type: Optional[str] = None
    main_personality_trait_1: Optional[str] = None
    main_personality_trait_2: Optional[str] = None
    main_personality_trait_3: Optional[str] = None
    used_sources: Optional[str] = None
    context_type: Optional[str] = None
    answer_style: Optional[str] = None
    answer_length: Optional[str] = None
    interlocutor_type: Optional[str] = None
    goal: Optional[str] = None
    behaviour_when_ignore: Optional[str] = None
    behaviour_with_language: Optional[str] = None
    localisation: Optional[str] = None
    interlocutor_identity: Optional[str] = None
    answer_format: Optional[str] = None
    voice_output: bool = False
    persona_description: Optional[str] = None

    def __init___(self):
        pass

    def to_dict(self) -> dict:
        return asdict(self)

    def __str__(self):
        return f"BotParametersDto(id={self.id}, bot_id={self.bot_id}, bot_name={self.bot_name}, bot_type={self.bot_type})"
