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
    rank: int

class EntryOut(BaseModel):
    id: int
    headword: str
    meaning_en: str
    meaning_es: str

class EntryDetailOut(EntryOut):
    examples: List[ExampleOut]

# ✅ NEW: search response includes topic info
class SearchEntryOut(EntryOut):
    primary_topic: Optional[TopicMini] = None
    topic_ids: List[int] = []


class GoogleLoginIn(BaseModel):
    credential: str


class AuthUserOut(BaseModel):
    id: int
    email: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
