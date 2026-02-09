import { useMemo, useState } from "react";

export type Topic = {
  id: number;
  name: string;
  is_suggested: boolean;
};

export function TopicModal({
  isOpen,
  topics,
  selectedTopicId,
  yourTopicIds,
  onClose,
  onAddToYourTopics,
  onSelectTopic,
  onResetYourTopics,
}: {
  isOpen: boolean;
  topics: Topic[];
  selectedTopicId: number | null;
  yourTopicIds: number[];
  onClose: () => void;
  onAddToYourTopics: (topicId: number) => void;
  onSelectTopic: (topicId: number) => void;
  onResetYourTopics: () => void; // ✅ NEW
}) {
  const [q, setQ] = useState("");
  const [showAll, setShowAll] = useState(false);

  const byId = useMemo(() => new Map(topics.map((t) => [t.id, t])), [topics]);

  const filteredAll = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!s) return topics;
    return topics.filter((t) => t.name.toLowerCase().includes(s));
  }, [topics, q]);

  const suggested = useMemo(() => {
    const set = new Set(yourTopicIds);
    return filteredAll.filter((t) => t.is_suggested && !set.has(t.id));
  }, [filteredAll, yourTopicIds]);

  const yourTopics = useMemo(() => {
    const items = yourTopicIds
      .map((id) => byId.get(id))
      .filter(Boolean) as Topic[];

    const s = q.trim().toLowerCase();
    if (!s) return items;
    return items.filter((t) => t.name.toLowerCase().includes(s));
  }, [yourTopicIds, byId, q]);

  const allToShow = useMemo(() => {
    const set = new Set(yourTopicIds);
    return filteredAll.filter((t) => !set.has(t.id));
  }, [filteredAll, yourTopicIds]);

  if (!isOpen) return null;

  return (
    <div
      className="modalOverlay"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label="Select topic"
      >
        <div className="modalHeader">
          <div className="modalTitleRow">
            <div className="modalTitle">Select topic</div>
            <button className="modalClose" onClick={onClose} aria-label="Close">
              ✕
            </button>
          </div>

          <input
            className="searchInput"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search topics…"
          />
        </div>

        <div className="modalBody">
          {/* YOUR TOPICS */}
          <div className="sectionTitle" style={{ marginTop: 18 }}>
            Your topics
          </div>

          {/* ✅ Reset button */}
          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              marginTop: -4,
              marginBottom: 10,
            }}
          >
            <button
              className="btn btnGhost"
              style={{ padding: "10px 12px", borderRadius: 14 }}
              onClick={onResetYourTopics}
              title="Clear your topics and restore default"
            >
              Reset your topics
            </button>
          </div>

          <div style={{ display: "grid", gap: 10 }}>
            {yourTopics.length === 0 ? (
              <div style={{ color: "rgba(255,255,255,.65)", fontSize: 14 }}>
                Add topics above to start your list.
              </div>
            ) : (
              yourTopics.map((t) => {
                const active = t.id === selectedTopicId;
                return (
                  <div
                    key={t.id}
                    className="topicRow"
                    onClick={() => {
                      onSelectTopic(t.id);
                      onClose();
                    }}
                  >
                    <div className="topicLeft">
                      <span style={{ fontSize: 18 }}>📌</span>
                      <div style={{ minWidth: 0 }}>
                        <div className="topicName">
                          {t.name}
                          {t.name.toLowerCase() === "mixed" ? (
                            <span
                              style={{
                                opacity: 0.75,
                                marginLeft: 8,
                                fontWeight: 650,
                              }}
                            >
                              (default)
                            </span>
                          ) : null}
                        </div>
                        <div className="topicMeta">Your topic</div>
                      </div>
                    </div>

                    {active ? (
                      <div className="topicActiveDot" title="Selected" />
                    ) : (
                      <span>→</span>
                    )}
                  </div>
                );
              })
            )}
          </div>

          {/* Suggested topics (con + Add) */}
          <div className="sectionTitle" style={{ marginTop: 18 }}>
            Suggested topics
          </div>

          <div style={{ display: "grid", gap: 10 }}>
            {suggested.length === 0 ? (
              <div style={{ color: "rgba(255,255,255,.65)", fontSize: 14 }}>
                No suggestions right now.
              </div>
            ) : (
              suggested.slice(0, 6).map((t) => (
                <div
                  key={t.id}
                  className="topicRow"
                  style={{ cursor: "default" }}
                >
                  <div className="topicLeft">
                    <span style={{ fontSize: 18 }}>⭐</span>
                    <div style={{ minWidth: 0 }}>
                      <div className="topicName">{t.name}</div>
                      <div className="topicMeta">Suggested</div>
                    </div>
                  </div>

                  <button
                    className="btn btnGhost topicAddBtn"
                    onClick={() => onAddToYourTopics(t.id)}
                  >
                    + Add
                  </button>
                </div>
              ))
            )}

            <button
              className="topicLinkBtn"
              onClick={() => setShowAll((v) => !v)}
              aria-label="See all topics"
            >
              {showAll ? "Hide all topics ←" : "See all topics →"}
            </button>

            {showAll && (
              <div style={{ display: "grid", gap: 10 }}>
                {allToShow.length === 0 ? (
                  <div style={{ color: "rgba(255,255,255,.65)", fontSize: 14 }}>
                    No more topics to add.
                  </div>
                ) : (
                  allToShow.map((t) => (
                    <div
                      key={t.id}
                      className="topicRow"
                      style={{ cursor: "default" }}
                    >
                      <div className="topicLeft">
                        <span style={{ fontSize: 18 }}>
                          {t.is_suggested ? "⭐" : "📁"}
                        </span>
                        <div style={{ minWidth: 0 }}>
                          <div className="topicName">{t.name}</div>
                          <div className="topicMeta">
                            {t.is_suggested ? "Suggested" : "Topic"}
                          </div>
                        </div>
                      </div>

                      <button
                        className="btn btnGhost topicAddBtn"
                        onClick={() => onAddToYourTopics(t.id)}
                      >
                        + Add
                      </button>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>

          {/* Create new topic placeholder */}
          <div className="sectionTitle" style={{ marginTop: 18 }}>
            Create new topic
          </div>
          <div style={{ color: "rgba(255,255,255,.65)", fontSize: 14 }}>
            Coming soon.
          </div>
        </div>
      </div>
    </div>
  );
}
