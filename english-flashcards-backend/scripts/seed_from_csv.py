from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Sequence

import psycopg


@dataclass
class Stats:
    inserted_topics: int = 0
    inserted_entries: int = 0
    updated_entries: int = 0
    inserted_topic_entries: int = 0
    inserted_examples: int = 0
    skipped_rows: int = 0


@dataclass
class EntryCacheItem:
    entry_id: int
    meaning_en: Optional[str]
    meaning_es: Optional[str]


def norm_key(value: str) -> str:
    return value.strip().lower()


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def resolve_column(fieldnames: Sequence[str], candidates: Sequence[str]) -> Optional[str]:
    existing = set(fieldnames)
    for name in candidates:
        if name in existing:
            return name
    return None


def load_topic_cache(cur: psycopg.Cursor) -> Dict[str, int]:
    cur.execute("SELECT id, name FROM topics")
    cache: Dict[str, int] = {}
    for topic_id, name in cur.fetchall():
        cache[norm_key(name)] = int(topic_id)
    return cache


def load_entry_cache(cur: psycopg.Cursor) -> Dict[str, EntryCacheItem]:
    cur.execute("SELECT id, headword, meaning_en, meaning_es FROM entries")
    cache: Dict[str, EntryCacheItem] = {}
    for entry_id, headword, meaning_en, meaning_es in cur.fetchall():
        cache[norm_key(headword)] = EntryCacheItem(
            entry_id=int(entry_id),
            meaning_en=meaning_en,
            meaning_es=meaning_es,
        )
    return cache


def load_example_caches(cur: psycopg.Cursor) -> tuple[Dict[int, set[str]], Dict[int, int]]:
    cur.execute("SELECT entry_id, text_en, rank FROM examples")
    example_cache: Dict[int, set[str]] = {}
    max_rank_by_entry: Dict[int, int] = {}

    for entry_id_raw, text_en, rank_raw in cur.fetchall():
        entry_id = int(entry_id_raw)
        text = clean(text_en)
        if text:
            example_cache.setdefault(entry_id, set()).add(text)

        rank_value = int(rank_raw) if rank_raw is not None else 0
        current_max = max_rank_by_entry.get(entry_id, 0)
        if rank_value > current_max:
            max_rank_by_entry[entry_id] = rank_value

    next_rank_cache = {entry_id: max_rank + 1 for entry_id, max_rank in max_rank_by_entry.items()}
    return example_cache, next_rank_cache


def ensure_topic(
    cur: psycopg.Cursor,
    topic_name: str,
    topic_key: str,
    topic_cache: Dict[str, int],
    stats: Stats,
) -> int:
    cached = topic_cache.get(topic_key)
    if cached is not None:
        return cached

    cur.execute(
        """
        INSERT INTO topics (name, is_suggested)
        VALUES (%s, FALSE)
        ON CONFLICT DO NOTHING
        RETURNING id
        """,
        (topic_name,),
    )
    row = cur.fetchone()
    if row is not None:
        topic_id = int(row[0])
        stats.inserted_topics += 1
    else:
        cur.execute("SELECT id FROM topics WHERE lower(name) = %s", (topic_key,))
        topic_id = int(cur.fetchone()[0])

    topic_cache[topic_key] = topic_id
    return topic_id


def ensure_entry(
    cur: psycopg.Cursor,
    headword: str,
    headword_key: str,
    meaning_en_csv: str,
    meaning_es_csv: str,
    entry_cache: Dict[str, EntryCacheItem],
    stats: Stats,
) -> int:
    cached = entry_cache.get(headword_key)

    if cached is None:
        cur.execute(
            """
            INSERT INTO entries (headword, meaning_en, meaning_es)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING
            RETURNING id
            """,
            (
                headword,
                meaning_en_csv if meaning_en_csv else None,
                meaning_es_csv if meaning_es_csv else None,
            ),
        )
        row = cur.fetchone()
        if row is not None:
            entry_id = int(row[0])
            cached = EntryCacheItem(
                entry_id=entry_id,
                meaning_en=meaning_en_csv if meaning_en_csv else None,
                meaning_es=meaning_es_csv if meaning_es_csv else None,
            )
            entry_cache[headword_key] = cached
            stats.inserted_entries += 1
            return entry_id

        cur.execute(
            "SELECT id, meaning_en, meaning_es FROM entries WHERE lower(headword) = %s",
            (headword_key,),
        )
        existing = cur.fetchone()
        cached = EntryCacheItem(
            entry_id=int(existing[0]),
            meaning_en=existing[1],
            meaning_es=existing[2],
        )
        entry_cache[headword_key] = cached

    updates: list[str] = []
    params: list[object] = []

    if meaning_en_csv and meaning_en_csv != (cached.meaning_en or ""):
        updates.append("meaning_en = %s")
        params.append(meaning_en_csv)
        cached.meaning_en = meaning_en_csv

    if meaning_es_csv and meaning_es_csv != (cached.meaning_es or ""):
        updates.append("meaning_es = %s")
        params.append(meaning_es_csv)
        cached.meaning_es = meaning_es_csv

    if updates:
        updates.append("updated_at = now()")
        params.append(cached.entry_id)
        sql = f"UPDATE entries SET {', '.join(updates)} WHERE id = %s"
        cur.execute(sql, params)
        stats.updated_entries += cur.rowcount

    return cached.entry_id


def attach_topic_entry(cur: psycopg.Cursor, topic_id: int, entry_id: int, stats: Stats) -> None:
    cur.execute(
        """
        INSERT INTO topic_entries (topic_id, entry_id)
        VALUES (%s, %s)
        ON CONFLICT (topic_id, entry_id) DO NOTHING
        """,
        (topic_id, entry_id),
    )
    if cur.rowcount > 0:
        stats.inserted_topic_entries += 1


def insert_example(
    cur: psycopg.Cursor,
    entry_id: int,
    example_text: str,
    example_cache: Dict[int, set[str]],
    next_rank_cache: Dict[int, int],
    stats: Stats,
) -> None:
    existing_for_entry = example_cache.setdefault(entry_id, set())
    if example_text in existing_for_entry:
        return

    next_rank = next_rank_cache.get(entry_id, 1)
    cur.execute(
        """
        INSERT INTO examples (entry_id, text_en, rank)
        VALUES (%s, %s, %s)
        """,
        (entry_id, example_text, next_rank),
    )

    existing_for_entry.add(example_text)
    next_rank_cache[entry_id] = next_rank + 1
    stats.inserted_examples += 1


def run(csv_path: Path, database_url: str, logger: logging.Logger) -> Stats:
    stats = Stats()

    with psycopg.connect(database_url) as conn:
        try:
            with conn.cursor() as cur:
                topic_cache = load_topic_cache(cur)
                entry_cache = load_entry_cache(cur)
                example_cache, next_rank_cache = load_example_caches(cur)

                with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                    reader = csv.DictReader(handle)
                    fieldnames = reader.fieldnames or []

                    topic_col = resolve_column(fieldnames, ("Topic",))
                    entry_col = resolve_column(fieldnames, ("Entrie", "Entry"))
                    meaning_en_col = resolve_column(fieldnames, ("Meaning_En",))
                    meaning_es_col = resolve_column(fieldnames, ("Meaning_Es",))
                    example_col = resolve_column(fieldnames, ("Example Sentence", "Example_Sentence"))

                    missing_cols = [
                        name
                        for name, col in (
                            ("Topic", topic_col),
                            ("Entrie", entry_col),
                            ("Meaning_En", meaning_en_col),
                            ("Meaning_Es", meaning_es_col),
                            ("Example Sentence", example_col),
                        )
                        if col is None
                    ]
                    if missing_cols:
                        raise ValueError(f"Missing required CSV columns: {', '.join(missing_cols)}")

                    for line_no, row in enumerate(reader, start=2):
                        topic_name = clean(row.get(topic_col))
                        headword = clean(row.get(entry_col))
                        meaning_en = clean(row.get(meaning_en_col))
                        meaning_es = clean(row.get(meaning_es_col))
                        example_text = clean(row.get(example_col))

                        if not topic_name or not headword or not example_text:
                            stats.skipped_rows += 1
                            logger.warning(
                                "Skipping row %s (missing Topic, Entrie/Entry or Example Sentence)",
                                line_no,
                            )
                            continue

                        topic_key = norm_key(topic_name)
                        headword_key = norm_key(headword)

                        topic_id = ensure_topic(
                            cur=cur,
                            topic_name=topic_name,
                            topic_key=topic_key,
                            topic_cache=topic_cache,
                            stats=stats,
                        )
                        entry_id = ensure_entry(
                            cur=cur,
                            headword=headword,
                            headword_key=headword_key,
                            meaning_en_csv=meaning_en,
                            meaning_es_csv=meaning_es,
                            entry_cache=entry_cache,
                            stats=stats,
                        )
                        attach_topic_entry(cur=cur, topic_id=topic_id, entry_id=entry_id, stats=stats)
                        insert_example(
                            cur=cur,
                            entry_id=entry_id,
                            example_text=example_text,
                            example_cache=example_cache,
                            next_rank_cache=next_rank_cache,
                            stats=stats,
                        )

            conn.commit()
            return stats
        except Exception:
            conn.rollback()
            raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Seed Postgres topics/entries/topic_entries/examples from a CSV file."
    )
    parser.add_argument(
        "csv_path",
        help="Path to CSV file. Example: ./english_topics_vocabulary_best_meanings.csv",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Logging level. Default: INFO",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s | %(message)s")
    logger = logging.getLogger("seed_from_csv")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL env var is required.")
        return 2

    csv_path = Path(args.csv_path)
    if not csv_path.exists() or not csv_path.is_file():
        logger.error("CSV file not found: %s", csv_path)
        return 2

    try:
        stats = run(csv_path=csv_path, database_url=database_url, logger=logger)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Seeding failed: %s", exc)
        return 1

    logger.info("inserted_topics=%s", stats.inserted_topics)
    logger.info("inserted_entries=%s", stats.inserted_entries)
    logger.info("updated_entries=%s", stats.updated_entries)
    logger.info("inserted_topic_entries=%s", stats.inserted_topic_entries)
    logger.info("inserted_examples=%s", stats.inserted_examples)
    logger.info("skipped_rows=%s", stats.skipped_rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
