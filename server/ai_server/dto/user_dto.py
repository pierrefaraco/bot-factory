from dataclasses import dataclass, asdict, field
from typing import List


@dataclass
class UserDto:
    id: str
    email: str
    name: str
    roles: str
    parent_id: int
    is_active: bool
    selected_bot_id: int = -1
    assigned_bots: List = field(default_factory=list)

    def to_dict(self):
        return asdict(self)

    def __str__(self):
        return f"UserDto(id={self.id}, email={self.email}, name={self.name}, roles={self.roles}, parent_id={self.parent_id}, is_active={self.is_active}, selected_bot_id={self.selected_bot_id}, assigned_bots={self.assigned_bots})"
