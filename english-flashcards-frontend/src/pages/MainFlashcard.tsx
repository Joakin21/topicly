import { useEffect, useMemo, useRef, useState } from "react";
import { apiGet } from "../api/client";
import { Flashcard3D } from "../components/Flashcard3D";
import { TopicModal, type Topic } from "../components/TopicModal";

type EntryOut = {
  id: number;
  headword: string;
  meaning_en: string;
  meaning_es: string;
};

type ExampleOut = {
  id: number;
  text_en: string;
  rank: number;
};

type EntryDetail = EntryOut & {
  examples: ExampleOut[];
};

type CardView = {
  id: number;
  headword: string;
  meaningEn: string;
  meaningEs: string;
  exampleFront: string;
  exampleBack: string;
};

/**
 * ✅ Search result enriched with topic info (from backend /entries/search)
 * Your backend should return:
 *  - primary_topic: { id, name } (recommended topic to jump)
 *  - topic_ids: number[] (optional)
 */
type SearchEntry = EntryOut & {
  primary_topic?: { id: number; name: string } | null;
  topic_ids?: number[];
};

const YOUR_TOPICS_KEY = "your_topic_ids_v1";

export function MainFlashcard() {
  const [isFlipped, setIsFlipped] = useState(false);
  const [isTopicModalOpen, setIsTopicModalOpen] = useState(false);

  const [topics, setTopics] = useState<Topic[]>([]);
  const [selectedTopicId, setSelectedTopicId] = useState<number | null>(null);

  // ✅ Your topics (persistido sin login)
  const [yourTopicIds, setYourTopicIds] = useState<number[]>([]);

  const [entries, setEntries] = useState<EntryOut[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);

  const [entryDetail, setEntryDetail] = useState<EntryDetail | null>(null);

  const [loading, setLoading] = useState(true);
  const [errMsg, setErrMsg] = useState<string | null>(null);

  // ✅ Search states
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchEntry[]>([]);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const searchWrapRef = useRef<HTMLDivElement | null>(null);

  // ✅ NEW: request token to ignore stale /entries/{id} responses
  const entryDetailReqRef = useRef(0);

  // ✅ When selecting a global result from another topic, we change topic first,
  // then jump to the entry after entries list loads.
  const [pendingJumpEntryId, setPendingJumpEntryId] = useState<number | null>(
    null
  );

  const selectedTopic = useMemo(
    () => topics.find((t) => t.id === selectedTopicId) ?? null,
    [topics, selectedTopicId]
  );

  function addToYourTopics(topicId: number) {
    setYourTopicIds((prev) => {
      if (prev.includes(topicId)) return prev;
      const next = [...prev, topicId];
      localStorage.setItem(YOUR_TOPICS_KEY, JSON.stringify(next));
      return next;
    });
  }

  // ✅ Reset "Your topics" a estado inicial (Mixed default)
  function resetYourTopics() {
    localStorage.removeItem(YOUR_TOPICS_KEY);

    const mixed = topics.find((x) => x.name.toLowerCase() === "mixed");
    const defaultId = (mixed ?? topics[0])?.id ?? null;

    if (defaultId) {
      const next = [defaultId];
      setYourTopicIds(next);
      localStorage.setItem(YOUR_TOPICS_KEY, JSON.stringify(next));
      setSelectedTopicId(defaultId);
    } else {
      setYourTopicIds([]);
      setSelectedTopicId(null);
    }

    setIsTopicModalOpen(false);
  }

  // Close search dropdown on click outside
  useEffect(() => {
    function onDocMouseDown(e: MouseEvent) {
      if (!searchWrapRef.current) return;
      const el = searchWrapRef.current;
      if (!el.contains(e.target as Node)) setSearchOpen(false);
    }
    document.addEventListener("mousedown", onDocMouseDown);
    return () => document.removeEventListener("mousedown", onDocMouseDown);
  }, []);

  // 1) Load topics once
  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        setErrMsg(null);

        const t = await apiGet<Topic[]>("/topics");
        setTopics(t);

        // default: Mixed if exists, else first
        const mixed = t.find((x) => x.name.toLowerCase() === "mixed");
        const defaultId = (mixed ?? t[0])?.id ?? null;

        // 1) Load saved "Your topics" from localStorage
        const raw = localStorage.getItem(YOUR_TOPICS_KEY);
        let savedIds: number[] = [];
        try {
          savedIds = raw ? (JSON.parse(raw) as number[]) : [];
        } catch {
          savedIds = [];
        }

        // 2) If empty, initialize with Mixed (or first topic)
        if (savedIds.length === 0 && defaultId) {
          savedIds = [defaultId];
          localStorage.setItem(YOUR_TOPICS_KEY, JSON.stringify(savedIds));
        }

        // 3) Filter ids that still exist
        const validSet = new Set(t.map((x) => x.id));
        savedIds = savedIds.filter((id) => validSet.has(id));

        setYourTopicIds(savedIds);

        // 4) Select first of your topics, fallback to default
        setSelectedTopicId(savedIds[0] ?? defaultId ?? null);
      } catch (e: any) {
        setErrMsg(e?.message ?? "Failed to load topics");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // 2) Load entries whenever topic changes
  useEffect(() => {
    if (!selectedTopicId) return;

    (async () => {
      try {
        setLoading(true);
        setErrMsg(null);
        setIsFlipped(false);

        const list = await apiGet<EntryOut[]>(
          `/entries?topic_id=${selectedTopicId}&limit=2000`
        );
        setEntries(list);
        setCurrentIndex(0);
      } catch (e: any) {
        setErrMsg(e?.message ?? "Failed to load entries");
      } finally {
        setLoading(false);
      }
    })();
  }, [selectedTopicId]);

  // ✅ After entries load, if we have a pending jump id (from global search), jump now.
  useEffect(() => {
    if (!pendingJumpEntryId) return;
    if (!entries.length) return;

    const idx = entries.findIndex((e) => e.id === pendingJumpEntryId);
    if (idx >= 0) {
      setIsFlipped(false);
      setCurrentIndex(idx);
      setPendingJumpEntryId(null);
      return;
    }

    // fallback: load detail if entry isn't in the list for some reason
    (async () => {
      const requestId = ++entryDetailReqRef.current;
      try {
        setLoading(true);
        setErrMsg(null);

        const detail = await apiGet<EntryDetail>(
          `/entries/${pendingJumpEntryId}`
        );

        if (requestId !== entryDetailReqRef.current) return;

        setEntryDetail(detail);
        setIsFlipped(false);
      } catch (e: any) {
        if (requestId !== entryDetailReqRef.current) return;
        setErrMsg(e?.message ?? "Failed to open entry");
      } finally {
        if (requestId !== entryDetailReqRef.current) return;
        setLoading(false);
        setPendingJumpEntryId(null);
      }
    })();
  }, [pendingJumpEntryId, entries]);

  // 3) Load entry detail whenever current entry changes
  useEffect(() => {
    const current = entries[currentIndex];
    if (!current) {
      setEntryDetail(null);
      return;
    }

    const requestId = ++entryDetailReqRef.current;
    const currentId = current.id;

    (async () => {
      try {
        setLoading(true);
        setErrMsg(null);

        const detail = await apiGet<EntryDetail>(`/entries/${currentId}`);

        // ✅ Ignore stale responses (user moved to another card)
        if (requestId !== entryDetailReqRef.current) return;

        setEntryDetail(detail);
      } catch (e: any) {
        if (requestId !== entryDetailReqRef.current) return;
        setErrMsg(e?.message ?? "Failed to load entry detail");
      } finally {
        if (requestId !== entryDetailReqRef.current) return;
        setLoading(false);
      }
    })();
  }, [entries, currentIndex]);

  // ✅ Search (debounced) — GLOBAL (all topics)
  useEffect(() => {
    const q = searchQuery.trim();
    if (!q) {
      setSearchResults([]);
      setSearchOpen(false);
      return;
    }

    const handle = window.setTimeout(async () => {
      try {
        setSearchLoading(true);

        // ✅ GLOBAL SEARCH: no topic_id param
        const url = `/entries/search?q=${encodeURIComponent(q)}&limit=20`;
        const res = await apiGet<SearchEntry[]>(url);

        setSearchResults(res);
        setSearchOpen(true);
      } catch {
        setSearchResults([]);
        setSearchOpen(true);
      } finally {
        setSearchLoading(false);
      }
    }, 250);

    return () => window.clearTimeout(handle);
  }, [searchQuery]);

  async function selectSearchResult(item: SearchEntry) {
    setSearchOpen(false);
    setSearchQuery("");

    const targetTopicId = item.primary_topic?.id ?? null;

    // ✅ If result suggests a topic and it's not current, switch topic then jump
    if (targetTopicId && targetTopicId !== selectedTopicId) {
      setPendingJumpEntryId(item.id);
      setIsFlipped(false);

      // ✅ Prevent showing stale card while changing topics
      setEntryDetail(null);
      entryDetailReqRef.current += 1;

      // Optional: ensure this topic appears in "Your topics" as user convenience
      addToYourTopics(targetTopicId);

      setSelectedTopicId(targetTopicId);
      return;
    }

    // If it exists in current entries list, jump to index
    const idx = entries.findIndex((e) => e.id === item.id);
    if (idx >= 0) {
      setIsFlipped(false);
      setCurrentIndex(idx);
      return;
    }

    // fallback: show it even if it's not in current list
    const requestId = ++entryDetailReqRef.current;
    try {
      setLoading(true);
      setErrMsg(null);

      const detail = await apiGet<EntryDetail>(`/entries/${item.id}`);

      if (requestId !== entryDetailReqRef.current) return;

      setEntryDetail(detail);
      setIsFlipped(false);
    } catch (e: any) {
      if (requestId !== entryDetailReqRef.current) return;
      setErrMsg(e?.message ?? "Failed to open entry");
    } finally {
      if (requestId !== entryDetailReqRef.current) return;
      setLoading(false);
    }
  }

  const cardView: CardView | null = useMemo(() => {
    if (!entryDetail) return null;

    const sorted = [...(entryDetail.examples ?? [])].sort(
      (a, b) => a.rank - b.rank
    );
    const ex1 = sorted[0]?.text_en ?? "";
    const ex2 = sorted[1]?.text_en ?? sorted[0]?.text_en ?? "";

    return {
      id: entryDetail.id,
      headword: entryDetail.headword,
      meaningEn: entryDetail.meaning_en,
      meaningEs: entryDetail.meaning_es,
      exampleFront: ex1 ? `"${ex1}"` : "",
      exampleBack: ex2 ? `"${ex2}"` : "",
    };
  }, [entryDetail]);

  const canPrev = currentIndex > 0;
  const canNext = currentIndex < entries.length - 1;

  function goPrev() {
    if (!canPrev) return;
    setIsFlipped(false);
    setCurrentIndex((i) => Math.max(0, i - 1));
  }

  function goNext() {
    if (!canNext) return;
    setIsFlipped(false);
    setCurrentIndex((i) => Math.min(entries.length - 1, i + 1));
  }

  return (
    <div style={{ position: "relative" }}>
      {/* Header */}
      <div style={styles.header}>
        {/* ✅ Search input + dropdown */}
        <div ref={searchWrapRef} style={styles.searchWrap}>
          <div style={styles.searchIcon}>🔎</div>
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onFocus={() => {
              if (searchQuery.trim()) setSearchOpen(true);
            }}
            placeholder="Search a word…"
            style={styles.searchInput}
          />

          {(searchOpen || searchLoading) && (
            <div style={styles.searchDropdown}>
              {searchLoading ? (
                <div style={styles.searchItemMuted}>Searching…</div>
              ) : searchResults.length === 0 ? (
                <div style={styles.searchItemMuted}>No results</div>
              ) : (
                searchResults.map((r) => (
                  <button
                    key={r.id}
                    style={styles.searchItem}
                    onClick={() => selectSearchResult(r)}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        gap: 10,
                      }}
                    >
                      <div style={{ fontWeight: 800 }}>{r.headword}</div>
                      <div
                        style={{
                          display: "flex",
                          gap: 8,
                          alignItems: "center",
                          flexWrap: "wrap",
                          justifyContent: "flex-end",
                        }}
                      >
                        {r.primary_topic?.name && (
                          <div style={styles.searchBadge}>
                            {r.primary_topic.name}
                          </div>
                        )}
                      </div>
                    </div>
                    {/* ✅ Removed Spanish translation here */}
                  </button>
                ))
              )}
            </div>
          )}
        </div>

        <div style={styles.rightHeader}>
          <div className="pill">Hi Carlos 👋</div>

          <div style={styles.topicGroup}>
            <span style={styles.topicBadge} title="Selected topic">
              {selectedTopic?.name ?? "—"}
            </span>

            <button
              className="btn"
              style={styles.selectTopicBtn}
              onClick={() => setIsTopicModalOpen(true)}
            >
              Select topic
            </button>
          </div>
        </div>
      </div>

      <hr className="hr" />

      {/* States */}
      {errMsg && (
        <div style={styles.notice}>
          <div style={{ fontWeight: 700, marginBottom: 6 }}>Error</div>
          <div style={{ opacity: 0.9 }}>{errMsg}</div>
        </div>
      )}

      {!errMsg && loading && (
        <div style={styles.notice}>
          <div style={{ opacity: 0.9 }}>Loading…</div>
        </div>
      )}

      {!errMsg && !loading && !cardView && (
        <div style={styles.notice}>
          <div style={{ opacity: 0.9 }}>No entries for this topic yet.</div>
        </div>
      )}

      {/* Card */}
      {!errMsg && cardView && (
        <>
          <Flashcard3D
            card={{
              id: String(cardView.id),
              headword: cardView.headword,
              meaningEn: cardView.meaningEn,
              meaningEs: cardView.meaningEs,
              exampleFront: cardView.exampleFront,
              exampleBack: cardView.exampleBack,
            }}
            flipped={isFlipped}
            onFlip={() => setIsFlipped((v) => !v)}
            onSpeak={(t) => speak(t)}
          />

          {/* Prev/Next controls */}
          <div style={styles.navBelow}>
            <button
              className="btn"
              onClick={goPrev}
              disabled={!canPrev}
              style={styles.navBtn}
            >
              ← Prev
            </button>

            <div style={{ color: "rgba(255,255,255,.70)", fontSize: 13 }}>
              {entries.length
                ? `${currentIndex + 1} / ${entries.length}`
                : "0 / 0"}
            </div>

            <button
              className="btn"
              onClick={goNext}
              disabled={!canNext}
              style={styles.navBtn}
            >
              Next →
            </button>
          </div>
        </>
      )}

      <hr className="hr" />

      {/* Bottom */}
      <div style={styles.bottom}>
        <button className="btn" style={{ width: "100%", maxWidth: 360 }}>
          ▶ Practice this topic
        </button>
        <div style={{ color: "rgba(255,255,255,.70)", marginTop: 10 }}>
          ⏱ 2 minutes left today
        </div>
      </div>

      {/* ✅ Updated modal props */}
      <TopicModal
        isOpen={isTopicModalOpen}
        topics={topics}
        selectedTopicId={selectedTopicId}
        yourTopicIds={yourTopicIds}
        onClose={() => setIsTopicModalOpen(false)}
        onAddToYourTopics={addToYourTopics}
        onSelectTopic={(id) => setSelectedTopicId(id)}
        onResetYourTopics={resetYourTopics}
      />
    </div>
  );
}

function speak(text: string) {
  const synth = window.speechSynthesis;
  if (!synth) return;
  synth.cancel();
  const utter = new SpeechSynthesisUtterance(text);
  utter.lang = "en-US";
  synth.speak(utter);
}

const styles: Record<string, React.CSSProperties> = {
  header: {
    display: "flex",
    justifyContent: "space-between",
    gap: 12,
    alignItems: "center",
    flexWrap: "wrap",
  },
  rightHeader: {
    display: "flex",
    gap: 10,
    alignItems: "center",
    flexWrap: "wrap",
    justifyContent: "flex-end",
  },
  topicGroup: {
    display: "flex",
    alignItems: "center",
    gap: 10,
  },
  topicBadge: {
    display: "inline-flex",
    alignItems: "center",
    padding: "8px 12px",
    borderRadius: 999,
    border: "1px solid rgba(255,255,255,.18)",
    background: "rgba(255,255,255,.08)",
    color: "rgba(255,255,255,.92)",
    fontWeight: 700,
    letterSpacing: 0.2,
  },
  selectTopicBtn: {
    padding: "10px 16px",
    borderRadius: 12,
    fontWeight: 700,
    letterSpacing: 0.3,
    color: "#fff",
    border: "1px solid rgba(124,92,255,.7)",
    background:
      "linear-gradient(135deg, rgba(124,92,255,.65), rgba(34,197,94,.35))",
    boxShadow:
      "0 12px 28px rgba(124,92,255,.35), 0 0 0 1px rgba(124,92,255,.2)",
    textShadow: "0 1px 8px rgba(0,0,0,.35)",
  },
  bottom: {
    display: "grid",
    placeItems: "center",
    paddingBottom: 6,
  },
  notice: {
    border: "1px solid rgba(255,255,255,.14)",
    background: "rgba(255,255,255,.06)",
    borderRadius: 16,
    padding: 14,
    margin: "10px 0 14px",
    backdropFilter: "blur(10px)",
  },
  navBelow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 12,
    marginTop: 10,
  },
  navBtn: {
    borderRadius: 14,
    padding: "10px 12px",
    opacity: 1,
  },

  // ✅ Search styles (improved visibility + layering)
  searchWrap: {
    position: "relative",
    zIndex: 2000,
    isolation: "isolate",
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "10px 12px",
    borderRadius: 999,
    border: "1px solid rgba(255,255,255,.16)",
    background: "rgba(255,255,255,.08)",
    backdropFilter: "blur(10px)",
    minWidth: 260,
    maxWidth: 360,
    width: "min(360px, 60vw)",
  },
  searchIcon: {
    opacity: 0.85,
  },
  searchInput: {
    width: "100%",
    border: "none",
    outline: "none",
    background: "transparent",
    color: "rgba(255,255,255,.92)",
    fontSize: 14,
  },
  searchDropdown: {
    position: "absolute",
    top: "calc(100% + 10px)",
    left: -6,
    right: -6,
    borderRadius: 16,
    border: "1px solid rgba(255,255,255,.18)",
    background: "rgba(12, 14, 22, .96)",
    backdropFilter: "blur(14px)",
    boxShadow: "0 24px 60px rgba(0,0,0,.60)",
    padding: 10,
    zIndex: 3000,
    maxHeight: 340,
    overflow: "auto",
  },
  searchItem: {
    width: "100%",
    textAlign: "left",
    border: "1px solid rgba(255,255,255,.14)",
    background: "rgba(255,255,255,.08)",
    color: "rgba(255,255,255,.94)",
    borderRadius: 14,
    padding: "12px 12px",
    cursor: "pointer",
    marginBottom: 8,
  },
  searchItemMuted: {
    color: "rgba(255,255,255,.70)",
    padding: "10px 10px",
    fontSize: 14,
  },
  searchBadge: {
    fontSize: 12,
    padding: "4px 8px",
    borderRadius: 999,
    border: "1px solid rgba(255,255,255,.14)",
    background: "rgba(255,255,255,.08)",
    color: "rgba(255,255,255,.78)",
    alignSelf: "center",
  },
};
