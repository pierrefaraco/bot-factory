from dataclasses import dataclass, asdict


@dataclass
class IFrameDto:
    id: int = -1
    bot_id: int = -1
    key: str = ""
    allowed_origins: str = ""

    def to_dict(self):
        return asdict(self)

    def __str__(self):
        return f"ChapterDto(id={self.id}, bot_id={self.bot_id}, key={self.key}, allowed_origins={self.allowed_origins}"
