from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple
from urllib.parse import urlparse
from urllib.request import urlretrieve

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import IntegrityError

DEFAULT_DATABASE_URL = "postgresql+psycopg://english:english@localhost:5432/english"
DEFAULT_BASE_TOPIC = "Mixed"

CANONICAL_TOPIC_NAME: Dict[str, str] = {
    "mixed": "Mixed",
    "traveling": "Traveling",
    "work": "Work",
    "daily life": "Daily life",
    "food": "Food",
    "shopping": "Shopping",
    "health": "Health",
    "social": "Social",
    "tech": "Tech",
    "slang": "Slang",
}

TOPIC_KEYWORDS: Dict[str, Sequence[str]] = {
    "traveling": (
        "airport",
        "flight",
        "passport",
        "hotel",
        "trip",
        "travel",
        "luggage",
        "book a room",
        "visa",
        "boarding",
        "viaje",
        "aeropuerto",
        "hotel",
        "pasaporte",
        "vuelo",
    ),
    "work": (
        "meeting",
        "deadline",
        "office",
        "salary",
        "manager",
        "interview",
        "coworker",
        "job",
        "work",
        "trabajo",
        "reunion",
        "oficina",
        "empleo",
    ),
    "daily life": (
        "wake up",
        "breakfast",
        "lunch",
        "dinner",
        "today",
        "tomorrow",
        "home",
        "family",
        "house",
        "morning",
        "night",
        "vida diaria",
        "casa",
        "familia",
    ),
    "food": (
        "eat",
        "drink",
        "restaurant",
        "menu",
        "water",
        "coffee",
        "breakfast",
        "lunch",
        "dinner",
        "food",
        "comida",
        "restaurante",
        "desayuno",
        "cena",
    ),
    "shopping": (
        "buy",
        "price",
        "discount",
        "store",
        "mall",
        "receipt",
        "cart",
        "checkout",
        "shop",
        "comprar",
        "precio",
        "tienda",
    ),
    "health": (
        "doctor",
        "pain",
        "medicine",
        "hospital",
        "healthy",
        "exercise",
        "sleep",
        "allergy",
        "sick",
        "salud",
        "medicina",
        "hospital",
        "doctor",
    ),
    "social": (
        "friend",
        "party",
        "invite",
        "call",
        "message",
        "chat",
        "date",
        "social",
        "amigo",
        "fiesta",
        "mensaje",
        "llamar",
    ),
    "tech": (
        "software",
        "hardware",
        "computer",
        "internet",
        "wifi",
        "code",
        "app",
        "bug",
        "phone",
        "email",
        "technology",
        "tecnologia",
        "computadora",
    ),
    "slang": (
        "gonna",
        "wanna",
        "ain't",
        "y'all",
        "kinda",
        "sorta",
        "dude",
        "bro",
        "slang",
        "jerga",
    ),
}

PHRASAL_PARTICLES = {
    "up",
    "down",
    "out",
    "in",
    "on",
    "off",
    "away",
    "back",
    "over",
    "through",
    "around",
    "about",
    "into",
    "for",
    "with",
    "after",
    "to",
    "from",
    "at",
    "by",
}


@dataclass
class ExamplePayload:
    text_en: str
    rank: int = 1


@dataclass
class CardPayload:
    headword: str
    meaning_en: str
    meaning_es: str
    topics: List[str] = field(default_factory=list)
    examples: List[ExamplePayload] = field(default_factory=list)
    source: Optional[str] = None
    frequency: Optional[float] = None


@dataclass
class IngestStats:
    rows_read: int = 0
    rows_valid: int = 0
    rows_skipped_invalid: int = 0
    rows_skipped_low_score: int = 0
    entries_created: int = 0
    entries_updated: int = 0
    examples_created: int = 0
    examples_updated: int = 0
    topics_created: int = 0
    links_created: int = 0


def collapse_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_key(value: str) -> str:
    return collapse_spaces(value).casefold()


def compile_phrase_pattern(phrase: str) -> re.Pattern[str]:
    parts = [re.escape(part) for part in collapse_spaces(phrase).lower().split()]
    pattern = r"\b" + r"\s+".join(parts) + r"\b"
    return re.compile(pattern)


def is_phrasal_verb_headword(headword: str) -> bool:
    tokens = collapse_spaces(headword).lower().split()
    if len(tokens) < 2 or len(tokens) > 4:
        return False
    if not re.fullmatch(r"[a-z][a-z'-]*", tokens[0]):
        return False
    return any(token in PHRASAL_PARTICLES for token in tokens[1:])


def parse_float(raw: Any) -> Optional[float]:
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def parse_topics(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        values = [str(x) for x in raw]
    else:
        values = re.split(r"[|,;]", str(raw))
    out: List[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = collapse_spaces(value)
        if not cleaned:
            continue
        key = cleaned.casefold()
        canonical = CANONICAL_TOPIC_NAME.get(key, cleaned)
        if canonical.casefold() in seen:
            continue
        seen.add(canonical.casefold())
        out.append(canonical)
    return out


def parse_examples(row: Dict[str, Any], max_examples: int) -> List[ExamplePayload]:
    raw_examples = row.get("examples")
    parsed: List[ExamplePayload] = []

    if isinstance(raw_examples, list):
        for idx, item in enumerate(raw_examples, start=1):
            if not isinstance(item, dict):
                continue
            text_en = collapse_spaces(str(item.get("text_en") or item.get("en") or ""))
            if not text_en:
                continue
            rank_value = item.get("rank") or idx
            try:
                rank = max(1, int(rank_value))
            except (TypeError, ValueError):
                rank = idx
            parsed.append(ExamplePayload(text_en=text_en, rank=rank))

    if not parsed:
        for idx in range(1, max_examples + 1):
            en = collapse_spaces(str(row.get(f"example_en_{idx}") or ""))
            if not en:
                continue
            parsed.append(ExamplePayload(text_en=en, rank=idx))

    if not parsed:
        en = collapse_spaces(str(row.get("example_en") or ""))
        if en:
            parsed.append(ExamplePayload(text_en=en, rank=1))

    deduped: List[ExamplePayload] = []
    seen_en: set[str] = set()
    for example in sorted(parsed, key=lambda ex: (ex.rank, ex.text_en.casefold())):
        key = normalize_key(example.text_en)
        if key in seen_en:
            continue
        seen_en.add(key)
        deduped.append(example)
        if len(deduped) >= max_examples:
            break
    return deduped


def normalize_row(row: Dict[str, Any], source_name: str, max_examples: int) -> Optional[CardPayload]:
    headword = collapse_spaces(
        str(row.get("headword") or row.get("term") or row.get("word") or row.get("phrase") or "")
    )
    meaning_en = collapse_spaces(
        str(row.get("meaning_en") or row.get("definition_en") or row.get("gloss_en") or "")
    )
    meaning_es = collapse_spaces(
        str(row.get("meaning_es") or row.get("translation_es") or row.get("gloss_es") or "")
    )
    if not headword or not meaning_en or not meaning_es:
        return None

    frequency = parse_float(row.get("frequency"))
    topics = parse_topics(row.get("topics") or row.get("topic"))
    examples = parse_examples(row=row, max_examples=max_examples)

    return CardPayload(
        headword=headword,
        meaning_en=meaning_en,
        meaning_es=meaning_es,
        topics=topics,
        examples=examples,
        source=source_name,
        frequency=frequency,
    )


def sanitize_card(card: CardPayload, max_examples: int) -> Optional[CardPayload]:
    card.headword = collapse_spaces(card.headword)
    card.meaning_en = collapse_spaces(card.meaning_en)
    card.meaning_es = collapse_spaces(card.meaning_es)

    blocked = {normalize_key(card.headword), normalize_key(card.meaning_en)}
    is_multiword = " " in card.headword
    phrase_pattern = compile_phrase_pattern(card.headword) if is_multiword else None

    cleaned_examples: List[ExamplePayload] = []
    seen_examples: set[str] = set()
    for idx, example in enumerate(sorted(card.examples, key=lambda ex: (ex.rank, ex.text_en.casefold())), start=1):
        text_en = collapse_spaces(example.text_en)
        if not text_en:
            continue
        key = normalize_key(text_en)
        if key in seen_examples or key in blocked:
            continue
        if phrase_pattern is not None and not phrase_pattern.search(text_en.lower()):
            continue
        seen_examples.add(key)
        cleaned_examples.append(ExamplePayload(text_en=text_en, rank=idx))
        if len(cleaned_examples) >= max_examples:
            break
    card.examples = cleaned_examples

    if is_multiword:
        if not is_phrasal_verb_headword(card.headword):
            return None
        if normalize_key(card.headword) == normalize_key(card.meaning_en):
            return None
        if normalize_key(card.headword) == normalize_key(card.meaning_es):
            return None
        if not card.examples:
            return None
    return card


def quality_score(card: CardPayload) -> int:
    score = 0
    if card.headword and card.meaning_en and card.meaning_es:
        score += 45

    word_count = len(card.headword.split())
    if word_count == 1:
        score += 20
    else:
        if is_phrasal_verb_headword(card.headword):
            score += 20
        elif 2 <= word_count <= 7:
            score += 20
        elif word_count <= 12:
            score += 10
        else:
            score -= 10

    if card.examples:
        score += min(20, len(card.examples) * 10)
    else:
        score -= 5

    if card.frequency is not None:
        if 0.0 <= card.frequency <= 1.0:
            score += int(card.frequency * 10)
        elif card.frequency > 1:
            score += max(0, 10 - int(min(card.frequency, 10000) / 1000))

    if len(card.headword) > 90:
        score -= 15
    if len(card.meaning_en) > 250 or len(card.meaning_es) > 250:
        score -= 10
    return max(0, min(100, score))


def infer_topics(card: CardPayload) -> List[str]:
    if card.topics:
        return card.topics

    def keyword_hits(text: str, keywords: Sequence[str]) -> int:
        lowered = text.lower()
        tokens = set(re.findall(r"[a-z]+(?:'[a-z]+)?", lowered))
        hits = 0
        for raw in keywords:
            kw = collapse_spaces(raw).lower()
            if not kw:
                continue
            if " " in kw:
                if compile_phrase_pattern(kw).search(lowered):
                    hits += 2
            else:
                if kw in tokens:
                    hits += 1
        return hits

    scores: List[Tuple[int, str]] = []
    for topic_key, keywords in TOPIC_KEYWORDS.items():
        score = 0
        score += keyword_hits(card.headword, keywords) * 4
        score += keyword_hits(card.meaning_en, keywords) * 2
        score += keyword_hits(card.meaning_es, keywords) * 2
        for ex in card.examples:
            score += keyword_hits(ex.text_en, keywords)
        if score > 0:
            scores.append((score, topic_key))

    if not scores:
        return []

    scores.sort(reverse=True)
    top_score, top_topic = scores[0]
    second_score = scores[1][0] if len(scores) > 1 else 0
    if top_score < 3 or top_score < second_score + 2:
        return []
    return [CANONICAL_TOPIC_NAME.get(top_topic, top_topic.title())]


def iter_jsonl(path: Path) -> Iterator[Dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            yield json.loads(stripped)


def iter_csv(path: Path) -> Iterator[Dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            yield row


def collect_input_files(raw_inputs: Sequence[str], logger: logging.Logger) -> List[Path]:
    files: List[Path] = []
    for item in raw_inputs:
        p = Path(item)
        if p.is_file():
            files.append(p)
            continue
        if p.is_dir():
            files.extend(sorted(p.glob("*.jsonl")))
            files.extend(sorted(p.glob("*.csv")))
            continue
        logger.warning("Input path not found: %s", item)
    return files


def download_sources(urls: Sequence[str], output_dir: Path, logger: logging.Logger) -> List[Path]:
    if not urls:
        return []
    output_dir.mkdir(parents=True, exist_ok=True)
    downloaded: List[Path] = []
    for url in urls:
        parsed = urlparse(url)
        filename = Path(parsed.path).name or "downloaded_data"
        destination = output_dir / filename
        logger.info("Downloading %s -> %s", url, destination)
        urlretrieve(url, destination)
        downloaded.append(destination)
    return downloaded


def canonical_topic_name(raw_name: str) -> str:
    cleaned = collapse_spaces(raw_name)
    if not cleaned:
        return cleaned
    return CANONICAL_TOPIC_NAME.get(cleaned.casefold(), cleaned)


def load_topic_cache(conn: Connection) -> Dict[str, int]:
    rows = conn.execute(text("SELECT id, name FROM topics")).mappings().all()
    return {str(row["name"]).casefold(): int(row["id"]) for row in rows}


def ensure_topic(conn: Connection, topic_cache: Dict[str, int], topic_name: str, stats: IngestStats) -> int:
    canonical = canonical_topic_name(topic_name)
    key = canonical.casefold()
    if key in topic_cache:
        return topic_cache[key]

    is_suggested = canonical.casefold() != DEFAULT_BASE_TOPIC.casefold()
    created = True
    try:
        topic_id = conn.execute(
            text(
                """
                INSERT INTO topics (name, is_suggested)
                VALUES (:name, :is_suggested)
                RETURNING id
                """
            ),
            {"name": canonical, "is_suggested": is_suggested},
        ).scalar_one()
    except IntegrityError:
        created = False
        topic_id = conn.execute(
            text("SELECT id FROM topics WHERE lower(name) = lower(:name)"),
            {"name": canonical},
        ).scalar_one()

    topic_cache[key] = int(topic_id)
    if created:
        stats.topics_created += 1
    return int(topic_id)


def load_entry_cache(conn: Connection) -> Dict[str, Dict[str, Any]]:
    rows = conn.execute(
        text(
            """
            SELECT id, headword, meaning_en, meaning_es
            FROM entries
            """
        )
    ).mappings()
    cache: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        key = normalize_key(str(row["headword"]))
        cache[key] = dict(row)
    return cache


def upsert_entry(conn: Connection, cache: Dict[str, Dict[str, Any]], card: CardPayload, stats: IngestStats) -> int:
    key = normalize_key(card.headword)
    existing = cache.get(key)
    if existing is None:
        entry_id = conn.execute(
            text(
                """
                INSERT INTO entries (headword, meaning_en, meaning_es)
                VALUES (:headword, :meaning_en, :meaning_es)
                RETURNING id
                """
            ),
            {
                "headword": card.headword,
                "meaning_en": card.meaning_en,
                "meaning_es": card.meaning_es,
            },
        ).scalar_one()
        cache[key] = {
            "id": int(entry_id),
            "headword": card.headword,
            "meaning_en": card.meaning_en,
            "meaning_es": card.meaning_es,
        }
        stats.entries_created += 1
        return int(entry_id)

    changed = (
        existing.get("meaning_en") != card.meaning_en
        or existing.get("meaning_es") != card.meaning_es
    )
    if changed:
        conn.execute(
            text(
                """
                UPDATE entries
                SET meaning_en = :meaning_en,
                    meaning_es = :meaning_es,
                    updated_at = now()
                WHERE id = :entry_id
                """
            ),
            {
                "entry_id": existing["id"],
                "meaning_en": card.meaning_en,
                "meaning_es": card.meaning_es,
            },
        )
        existing["meaning_en"] = card.meaning_en
        existing["meaning_es"] = card.meaning_es
        stats.entries_updated += 1
    return int(existing["id"])


def sync_examples(conn: Connection, entry_id: int, card: CardPayload, stats: IngestStats) -> None:
    if not card.examples:
        return

    rows = conn.execute(
        text(
            """
            SELECT id, text_en, rank
            FROM examples
            WHERE entry_id = :entry_id
            """
        ),
        {"entry_id": entry_id},
    ).mappings()
    existing_by_en: Dict[str, Dict[str, Any]] = {
        normalize_key(str(row["text_en"])): dict(row) for row in rows
    }

    for example in card.examples:
        ex_key = normalize_key(example.text_en)
        existing = existing_by_en.get(ex_key)
        if existing is None:
            conn.execute(
                text(
                    """
                    INSERT INTO examples (entry_id, text_en, rank)
                    VALUES (:entry_id, :text_en, :rank)
                    """
                ),
                {
                    "entry_id": entry_id,
                    "text_en": example.text_en,
                    "rank": example.rank,
                },
            )
            stats.examples_created += 1
            continue

        changed = int(existing.get("rank") or 1) != example.rank
        if changed:
            conn.execute(
                text(
                    """
                    UPDATE examples
                    SET rank = :rank
                    WHERE id = :id
                    """
                ),
                {
                    "id": existing["id"],
                    "rank": example.rank,
                },
            )
            stats.examples_updated += 1


def attach_topics(conn: Connection, entry_id: int, topic_ids: Sequence[int], stats: IngestStats) -> None:
    for topic_id in topic_ids:
        result = conn.execute(
            text(
                """
                INSERT INTO topic_entries (topic_id, entry_id)
                VALUES (:topic_id, :entry_id)
                ON CONFLICT DO NOTHING
                """
            ),
            {"topic_id": topic_id, "entry_id": entry_id},
        )
        if result.rowcount and result.rowcount > 0:
            stats.links_created += 1


def iter_cards(input_files: Sequence[Path], logger: logging.Logger, max_examples: int) -> Iterator[Optional[CardPayload]]:
    for file_path in input_files:
        suffix = file_path.suffix.lower()
        source_name = file_path.name
        try:
            if suffix == ".jsonl":
                row_iter = iter_jsonl(file_path)
            elif suffix == ".csv":
                row_iter = iter_csv(file_path)
            else:
                logger.warning("Skipping unsupported file: %s", file_path)
                continue
            for row in row_iter:
                yield normalize_row(row=row, source_name=source_name, max_examples=max_examples)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to parse %s: %s", file_path, exc)


def build_engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True)


def run_ingest(args: argparse.Namespace, logger: logging.Logger) -> int:
    stats = IngestStats()
    output_dir = Path(args.download_dir)
    downloaded = download_sources(args.download, output_dir=output_dir, logger=logger)

    all_inputs = list(args.input or []) + [str(path) for path in downloaded]
    input_files = collect_input_files(all_inputs, logger=logger)
    if not input_files:
        logger.error("No input files found. Use --input <file|folder> or --download <url>.")
        return 2

    logger.info("Input files: %s", ", ".join(str(p) for p in input_files))
    engine = build_engine(args.database_url)

    with engine.connect() as conn:
        tx = conn.begin()
        try:
            topic_cache = load_topic_cache(conn)
            entry_cache = load_entry_cache(conn)
            mixed_topic_id = ensure_topic(conn, topic_cache, DEFAULT_BASE_TOPIC, stats)

            accepted_rows = 0
            for maybe_card in iter_cards(input_files, logger=logger, max_examples=args.max_examples):
                stats.rows_read += 1
                if args.limit and accepted_rows >= args.limit:
                    break
                if maybe_card is None:
                    stats.rows_skipped_invalid += 1
                    continue

                card = sanitize_card(card=maybe_card, max_examples=args.max_examples)
                if card is None:
                    stats.rows_skipped_invalid += 1
                    continue

                score = quality_score(card)
                if score < args.min_score:
                    stats.rows_skipped_low_score += 1
                    continue

                inferred_topics = infer_topics(card) if not card.topics else []
                topic_names = list(dict.fromkeys([*card.topics, *inferred_topics]))
                topic_ids = [mixed_topic_id]
                for topic_name in topic_names:
                    if not topic_name:
                        continue
                    topic_id = ensure_topic(conn, topic_cache, topic_name, stats)
                    if topic_id not in topic_ids:
                        topic_ids.append(topic_id)

                entry_id = upsert_entry(conn, entry_cache, card, stats)
                sync_examples(conn, entry_id, card, stats)
                attach_topics(conn, entry_id, topic_ids, stats)

                stats.rows_valid += 1
                accepted_rows += 1

            if args.dry_run:
                tx.rollback()
                logger.info("Dry-run enabled. Transaction rolled back.")
            else:
                tx.commit()
        except Exception:  # noqa: BLE001
            tx.rollback()
            raise

    logger.info(
        "rows_read=%s rows_valid=%s skipped_low_score=%s skipped_invalid=%s",
        stats.rows_read,
        stats.rows_valid,
        stats.rows_skipped_low_score,
        stats.rows_skipped_invalid,
    )
    logger.info(
        "entries(created=%s updated=%s) examples(created=%s updated=%s) topics(created=%s) links(created=%s)",
        stats.entries_created,
        stats.entries_updated,
        stats.examples_created,
        stats.examples_updated,
        stats.topics_created,
        stats.links_created,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Weekly data ingest for flashcards. Supports JSONL/CSV input, "
            "quality filtering, topic inference, and idempotent upserts."
        )
    )
    parser.add_argument(
        "--input",
        action="append",
        default=[],
        help="Input file or folder (.jsonl or .csv). Can be used multiple times.",
    )
    parser.add_argument(
        "--download",
        action="append",
        default=[],
        help="Optional URL to download before ingest. Can be used multiple times.",
    )
    parser.add_argument(
        "--download-dir",
        default="data/inbox",
        help="Directory where downloaded files are stored. Default: data/inbox",
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
        help="SQLAlchemy database URL. Defaults to DATABASE_URL env var or local Postgres.",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=45,
        help="Minimum quality score to ingest (0-100). Default: 45",
    )
    parser.add_argument(
        "--max-examples",
        type=int,
        default=2,
        help="Maximum number of examples kept per card. Default: 2",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional max number of accepted rows per run. 0 means no limit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and execute ingest logic, but rollback transaction at the end.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Log level. Default: INFO",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    logger = logging.getLogger("data_ingest")

    if args.max_examples < 1:
        logger.error("--max-examples must be >= 1")
        return 2
    if args.min_score < 0 or args.min_score > 100:
        logger.error("--min-score must be between 0 and 100")
        return 2

    return run_ingest(args=args, logger=logger)


if __name__ == "__main__":
    sys.exit(main())
