from dataclasses import dataclass, asdict


@dataclass
class BotAssignmentDto:
    id: int
    bot_id: int
    user_id: int
    assigned_by: int
    assigned_at: str
    is_active: bool

    def to_dict(self):
        return asdict(self)

    def __str__(self):
        return f"BotAssignmentDto(id={self.id}, bot_id={self.bot_id}, user_id={self.user_id}, assigned_by={self.assigned_by}, assigned_at={self.assigned_at}, is_active={self.is_active})"
