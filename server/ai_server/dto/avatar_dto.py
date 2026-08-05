from dataclasses import dataclass, asdict


@dataclass
class AvatarDto:
    id: int = -1
    bot_id: int = -1
    body: int = 0
    body_color: int = 0
    hat: int = 0
    hat_color: int = 0
    eyes: int = 0
    eyes_color: int = 0
    mouth: int = 0
    mouth_color: int = 0

    def to_dict(self):
        return asdict(self)

    def __str__(self):
        return f"AvatarDto(id={self.id}, bot_id={self.bot_id}, body={self.body}, body_color={self.body_color}, hat={self.hat}, hat_color={self.hat_color}, eyes={self.eyes}, eyes_color={self.eyes_color}, mouth={self.mouth}, mouth_color={self.mouth_color})"
