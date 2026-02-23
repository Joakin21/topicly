from __future__ import annotations

import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import urlopen

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import case, delete, func, select, text, update
from sqlalchemy.orm import Session

from .db import engine, get_db
from .models import Entry, Example, Topic, TopicEntry, User, UserSession
from .schemas import (
    AuthUserOut,
    EntryDetailOut,
    EntryOut,
    GoogleLoginIn,
    SearchEntryOut,
    TopicOut,
)

SESSION_COOKIE_NAME = "ef_session"
SESSION_TTL_DAYS = int(os.getenv("SESSION_TTL_DAYS", "30"))
AUTH_COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "false").strip().lower() == "true"
GOOGLE_CLIENT_IDS = [
    item.strip() for item in os.getenv("GOOGLE_CLIENT_ID", "").split(",") if item.strip()
]


def _allowed_origins() -> List[str]:
    raw = os.getenv("FRONTEND_ORIGINS", "http://localhost:5173")
    origins = [item.strip() for item in raw.split(",") if item.strip()]
    return origins or ["http://localhost:5173"]


app = FastAPI(title="English Flashcards API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _ensure_auth_tables() -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id BIGSERIAL PRIMARY KEY,
                    google_sub TEXT NOT NULL UNIQUE,
                    email TEXT NOT NULL UNIQUE,
                    name TEXT NULL,
                    avatar_url TEXT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    last_login_at TIMESTAMPTZ NULL
                )
                """
            )
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_google_sub ON users (google_sub)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)"))

        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    token_hash TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    expires_at TIMESTAMPTZ NOT NULL,
                    revoked_at TIMESTAMPTZ NULL
                )
                """
            )
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions (user_id)")
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS idx_user_sessions_token_hash ON user_sessions (token_hash)")
        )


@app.on_event("startup")
def on_startup() -> None:
    _ensure_auth_tables()


def _is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def _hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite="lax",
        max_age=SESSION_TTL_DAYS * 24 * 60 * 60,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


def _verify_google_credential(credential: str) -> dict[str, Any]:
    if not GOOGLE_CLIENT_IDS:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Missing GOOGLE_CLIENT_ID on backend",
        )

    url = f"https://oauth2.googleapis.com/tokeninfo?id_token={quote_plus(credential)}"

    try:
        with urlopen(url, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google credential",
        ) from exc
    except URLError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google auth service unavailable",
        ) from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unexpected response from Google auth service",
        ) from exc

    aud = str(payload.get("aud") or "")
    iss = str(payload.get("iss") or "")
    sub = str(payload.get("sub") or "")
    email = str(payload.get("email") or "").strip().lower()
    email_verified = payload.get("email_verified")

    if aud not in GOOGLE_CLIENT_IDS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid audience")
    if iss not in {"accounts.google.com", "https://accounts.google.com"}:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid issuer")
    if not sub or not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Google claims")
    if not _is_truthy(email_verified):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email not verified")

    return payload


def _current_user_from_request(request: Request, db: Session) -> Optional[User]:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None

    token_hash = _hash_session_token(token)
    now_utc = datetime.now(timezone.utc)
    stmt = (
        select(User)
        .join(UserSession, UserSession.user_id == User.id)
        .where(UserSession.token_hash == token_hash)
        .where(UserSession.revoked_at.is_(None))
        .where(UserSession.expires_at > now_utc)
    )
    return db.execute(stmt).scalars().first()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/google", response_model=AuthUserOut)
def auth_google(payload: GoogleLoginIn, response: Response, db: Session = Depends(get_db)) -> User:
    credential = payload.credential.strip()
    if not credential:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing credential")

    claims = _verify_google_credential(credential)
    sub = str(claims["sub"])
    email = str(claims["email"]).strip().lower()
    name = str(claims.get("name") or "").strip() or None
    avatar_url = str(claims.get("picture") or "").strip() or None
    now_utc = datetime.now(timezone.utc)

    user = (
        db.execute(select(User).where((User.google_sub == sub) | (User.email == email)))
        .scalars()
        .first()
    )

    if user is None:
        user = User(
            google_sub=sub,
            email=email,
            name=name,
            avatar_url=avatar_url,
            last_login_at=now_utc,
        )
        db.add(user)
        db.flush()
    else:
        user.google_sub = sub
        user.email = email
        user.name = name
        user.avatar_url = avatar_url
        user.last_login_at = now_utc
        db.add(user)
        db.flush()

    db.execute(
        delete(UserSession).where(
            (UserSession.user_id == user.id)
            & ((UserSession.expires_at <= now_utc) | (UserSession.revoked_at.is_not(None)))
        )
    )

    raw_token = secrets.token_urlsafe(48)
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=_hash_session_token(raw_token),
            expires_at=now_utc + timedelta(days=SESSION_TTL_DAYS),
        )
    )
    db.commit()

    _set_session_cookie(response, raw_token)
    return user


@app.get("/auth/me", response_model=AuthUserOut)
def auth_me(request: Request, db: Session = Depends(get_db)) -> User:
    user = _current_user_from_request(request, db)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


@app.post("/auth/logout")
def auth_logout(request: Request, response: Response, db: Session = Depends(get_db)) -> dict[str, bool]:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        db.execute(
            update(UserSession)
            .where(UserSession.token_hash == _hash_session_token(token))
            .where(UserSession.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )
        db.commit()

    _clear_session_cookie(response)
    return {"ok": True}


@app.get("/topics", response_model=List[TopicOut])
def list_topics(db: Session = Depends(get_db)) -> List[Topic]:
    rows = db.execute(select(Topic).order_by(Topic.id)).scalars().all()
    return rows


@app.get("/entries", response_model=List[EntryOut])
def list_entries(
    topic_id: Optional[int] = Query(default=None),
    q: Optional[str] = Query(default=None),
    limit: int = Query(default=200, le=2000),
    db: Session = Depends(get_db),
) -> List[Entry]:
    stmt = select(Entry)

    if topic_id is not None:
        stmt = stmt.join(TopicEntry, TopicEntry.entry_id == Entry.id).where(TopicEntry.topic_id == topic_id)

    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            (Entry.headword.ilike(like))
            | (Entry.meaning_en.ilike(like))
            | (Entry.meaning_es.ilike(like))
        )

    stmt = stmt.order_by(Entry.id).limit(limit)
    return db.execute(stmt).scalars().all()


@app.get("/entries/search", response_model=List[SearchEntryOut])
def search_entries(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
) -> List[dict[str, Any]]:
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
        .where(
            (Entry.headword.ilike(like))
            | (Entry.meaning_en.ilike(like))
            | (Entry.meaning_es.ilike(like))
        )
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
                "headword": entry.headword,
                "meaning_en": entry.meaning_en,
                "meaning_es": entry.meaning_es,
                "primary_topic": primary,
                "topic_ids": [int(x) for x in topic_ids],
            }
        )
    return out


@app.get("/entries/{entry_id}", response_model=EntryDetailOut)
def get_entry(entry_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
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
        "headword": entry.headword,
        "meaning_en": entry.meaning_en,
        "meaning_es": entry.meaning_es,
        "examples": [{"id": int(e.id), "text_en": e.text_en, "rank": e.rank} for e in exs],
    }
