from pydantic import BaseModel
from typing import List, Optional

class TopicOut(BaseModel):
    id: int
    name: str
    is_suggested: bool

class TopicMini(BaseModel):
    id: int
    name: str

class ExampleOut(BaseModel):
    id: int
    text_en: str
    text_es: Optional[str] = None
    rank: int

class EntryOut(BaseModel):
    id: int
    kind: str
    headword: str
    meaning_en: str
    meaning_es: str
    notes: Optional[str] = None
    level: Optional[str] = None

class EntryDetailOut(EntryOut):
    examples: List[ExampleOut]

# ✅ NEW: search response includes topic info
class SearchEntryOut(EntryOut):
    primary_topic: Optional[TopicMini] = None
    topic_ids: List[int] = []
