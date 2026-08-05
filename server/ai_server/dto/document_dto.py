from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict, field


@dataclass
class DocumentDto:
    """Data Transfer Object for vector database documents"""

    id: Optional[str] = None
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    collection_name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert DocumentDto to dictionary representation"""
        return asdict(self)

    def __repr__(self) -> str:
        return f"DocumentDto(id={self.id}, collection_name={self.collection_name})"

    def __str__(self) -> str:
        return f"DocumentDto(id={self.id}, content={self.content[:30]}..., collection_name={self.collection_name})"
