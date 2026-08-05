from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class KnowledgeDto:
    id: str
    name: str
    date: str
    content: str
    knowledge_dad_id: str
    indice: int
    children_ref_id: str
    pdf_file: Optional[str] = None

    def to_dict(self):
        return asdict(self)

    def __str__(self):
        return f"ChapterDto(id={self.id}, name={self.name}, date={self.date}, content={self.content[:30]}..., knowledge_dad_id={self.knowledge_dad_id}, indice={self.indice}, children_ref_id={self.children_ref_id}, pdf_file={self.pdf_file})"
