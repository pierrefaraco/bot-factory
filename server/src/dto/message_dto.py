from dataclasses import dataclass, asdict


@dataclass
class MessageDto:
    id: str
    session_id: int
    role: str
    content: str
    order: int
    time: str

    def to_dict(self):
        return asdict(self)

    def __str__(self):
        return f"MessageDto(id={self.id}, session_id={self.session_id}, role={self.role}, content={self.content[:50]}..., order={self.order}, time={self.time})"
