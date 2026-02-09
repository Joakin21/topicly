from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select, func, case
from typing import Optional, List

from .db import get_db
from .models import Topic, Entry, Example, TopicEntry
from .schemas import TopicOut, EntryOut, EntryDetailOut, SearchEntryOut

app = FastAPI(title="English Flashcards API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/topics", response_model=List[TopicOut])
def list_topics(db: Session = Depends(get_db)):
    rows = db.execute(select(Topic).order_by(Topic.id)).scalars().all()
    return rows

@app.get("/entries", response_model=List[EntryOut])
def list_entries(
    topic_id: Optional[int] = Query(default=None),
    q: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
):
    stmt = select(Entry)

    if topic_id is not None:
        stmt = (
            stmt.join(TopicEntry, TopicEntry.entry_id == Entry.id)
                .where(TopicEntry.topic_id == topic_id)
        )

    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            (Entry.headword.ilike(like)) | (Entry.meaning_es.ilike(like))
        )

    stmt = stmt.order_by(Entry.id).limit(limit)
    return db.execute(stmt).scalars().all()

# ✅ NEW: Global search across ALL topics (and returns topic info)
@app.get("/entries/search", response_model=List[SearchEntryOut])
def search_entries(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    q_norm = q.strip()
    like = f"%{q_norm}%"

    stmt = (
        select(
            Entry,
            func.array_agg(Topic.id).label("topic_ids"),
            func.array_agg(Topic.name).label("topic_names"),
        )
        .join(TopicEntry, TopicEntry.entry_id == Entry.id)
        .join(Topic, Topic.id == TopicEntry.topic_id)
        .where((Entry.headword.ilike(like)) | (Entry.meaning_es.ilike(like)))
        .group_by(Entry.id)
        .order_by(
            case((func.lower(Entry.headword) == func.lower(q_norm), 0), else_=1),
            func.length(Entry.headword).asc(),
            Entry.headword.asc(),
            Entry.id.asc(),
        )
        .limit(limit)
    )

    rows = db.execute(stmt).all()

    out = []
    for entry, topic_ids, topic_names in rows:
        topic_ids = topic_ids or []
        topic_names = topic_names or []

        # pick primary topic: prefer first non-"mixed", else first
        pairs = list(zip(topic_ids, topic_names))
        primary = None
        for tid, tname in pairs:
            if (tname or "").lower() != "mixed":
                primary = {"id": int(tid), "name": tname}
                break
        if primary is None and pairs:
            tid, tname = pairs[0]
            primary = {"id": int(tid), "name": tname}

        out.append(
            {
                "id": int(entry.id),
                "kind": entry.kind,
                "headword": entry.headword,
                "meaning_es": entry.meaning_es,
                "notes": entry.notes,
                "level": entry.level,
                "primary_topic": primary,
                "topic_ids": [int(x) for x in topic_ids],
            }
        )

    return out

@app.get("/entries/{entry_id}", response_model=EntryDetailOut)
def get_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.execute(select(Entry).where(Entry.id == entry_id)).scalar_one()

    exs = (
        db.execute(
            select(Example)
            .where(Example.entry_id == entry_id)
            .order_by(Example.rank.asc(), Example.id.asc())
        )
        .scalars()
        .all()
    )

    return {
        "id": int(entry.id),
        "kind": entry.kind,
        "headword": entry.headword,
        "meaning_es": entry.meaning_es,
        "notes": entry.notes,
        "level": entry.level,
        "examples": [
            {"id": int(e.id), "text_en": e.text_en, "text_es": e.text_es, "rank": e.rank}
            for e in exs
        ],
    }
