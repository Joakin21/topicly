import { useEffect, useState } from "react";
import type { Flashcard } from "../data/flashcards";

export function Flashcard3D({
  card,
  flipped,
  onFlip,
  onSpeak,
}: {
  card: Flashcard;
  flipped: boolean;
  onFlip: () => void;
  onSpeak: (text: string) => void;
}) {
  const [showSpanish, setShowSpanish] = useState(false);

  useEffect(() => {
    setShowSpanish(false);
  }, [card.id, flipped]);

  const hasSpanish = Boolean(card.meaningEs?.trim());

  return (
    <div style={styles.stage}>
      <div
        style={{
          ...styles.card,
          transform: flipped ? "rotateY(180deg)" : "rotateY(0deg)",
        }}
      >
        {/* FRONT */}
        <div style={{ ...styles.face, ...styles.front }}>
          <div style={styles.center}>
            <div style={styles.headword}>{card.headword}</div>

            <button
              className="btn"
              style={styles.listen}
              onClick={() => onSpeak(card.headword)}
            >
              Listen
            </button>

            <div style={styles.example}>{card.exampleFront}</div>

            <button
              className="btn"
              style={styles.listen}
              onClick={() => onSpeak(stripQuotes(card.exampleFront))}
            >
              🔊 Listen example
            </button>

            <div style={styles.smallLink}>See other example</div>
          </div>

          {/* ⬇️ SOLO FLIP (sin prev / next) */}
          <div style={styles.faceBottom}>
            <button
              className="btn btnGhost"
              style={styles.flipBtn}
              onClick={onFlip}
            >
              Flip ↺
            </button>
          </div>
        </div>

        {/* BACK */}
        <div style={{ ...styles.face, ...styles.back }}>
          <div style={styles.centerBack}>
            <div style={styles.headwordBack}>{card.headword}</div>

            <button
              className="btn"
              style={styles.listenSmall}
              onClick={() => onSpeak(card.headword)}
            >
              Listen
            </button>

            <div style={styles.imagePlaceholder}>[ image ]</div>

            <div style={styles.infoCard}>
              <div style={styles.infoSection}>
                <div style={styles.infoLabel}>Meaning</div>
                <div style={styles.meaningEn}>{card.meaningEn}</div>
              </div>

              {hasSpanish && (
                <div style={styles.infoSection}>
                  <button
                    className="btn btnGhost"
                    style={styles.revealBtn}
                    onClick={() => setShowSpanish((v) => !v)}
                  >
                    {showSpanish
                      ? "Ocultar significado en espanol"
                      : "Ver significado en espanol"}
                  </button>

                  {showSpanish && (
                    <div style={styles.meaningEs}>{card.meaningEs}</div>
                  )}
                </div>
              )}

              <div style={styles.divider} />

              <div style={styles.infoSection}>
                <div style={styles.infoLabel}>Example</div>
                <div style={styles.exampleText}>{card.exampleBack}</div>
                <button
                  className="btn"
                  style={styles.listenSmall}
                  onClick={() => onSpeak(stripQuotes(card.exampleBack))}
                >
                  Listen example
                </button>
              </div>
            </div>

          </div>

          {/* ⬇️ SOLO FLIP (sin prev / next) */}
          <div style={styles.faceBottom}>
            <button
              className="btn btnGhost"
              style={styles.flipBtn}
              onClick={onFlip}
            >
              Flip ↺
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function stripQuotes(s: string) {
  return s.replace(/^"+|"+$/g, "");
}

const styles: Record<string, React.CSSProperties> = {
  stage: {
    perspective: 1200,
    width: "100%",
    display: "grid",
    placeItems: "center",
    padding: "10px 0 8px",
  },

  card: {
    width: "min(660px, 100%)",
    height: "min(58vh, 540px)",
    minHeight: 460,
    position: "relative",
    transformStyle: "preserve-3d",
    transition: "transform 650ms cubic-bezier(.2,.8,.2,1)",
  },

  face: {
    position: "absolute",
    inset: 0,
    borderRadius: 22,
    border: "1px solid rgba(255,255,255,.14)",
    background:
      "linear-gradient(180deg, rgba(255,255,255,.10), rgba(255,255,255,.06))",
    boxShadow: "0 12px 28px rgba(0,0,0,.28)",
    backdropFilter: "blur(12px)",
    padding: "clamp(14px, 2.8vw, 18px)",
    display: "grid",
    gridTemplateRows: "minmax(0, 1fr) auto",
    backfaceVisibility: "hidden",
    overflow: "hidden",
  },
  front: { transform: "rotateY(0deg)" },
  back: { transform: "rotateY(180deg)" },

  center: {
    textAlign: "center",
    display: "grid",
    placeItems: "center",
    gap: "clamp(6px, 1.2vh, 10px)",
    padding: "clamp(6px, 1.2vh, 10px) clamp(8px, 2vw, 10px)",
    minHeight: 0,
    overflow: "auto",
    overscrollBehavior: "contain",
  },
  centerBack: {
    textAlign: "center",
    display: "grid",
    placeItems: "center",
    gap: "clamp(4px, 0.9vh, 8px)",
    padding: "clamp(4px, 0.9vh, 8px) clamp(8px, 2vw, 10px)",
    minHeight: 0,
    overflow: "auto",
    overscrollBehavior: "contain",
  },

  headword: {
    fontSize: "clamp(24px, 4.8vw, 38px)",
    fontWeight: 800,
    letterSpacing: -0.6,
    marginTop: 4,
  },
  headwordBack: {
    fontSize: "clamp(22px, 4.4vw, 34px)",
    fontWeight: 800,
    letterSpacing: -0.6,
    marginTop: 2,
  },
  example: {
    fontSize: "clamp(14px, 3vw, 19px)",
    color: "rgba(255,255,255,.88)",
    maxWidth: 520,
    lineHeight: 1.4,
    padding: "2px 0",
  },
  infoCard: {
    width: "min(540px, 96%)",
    borderRadius: 18,
    border: "1px solid rgba(255,255,255,.16)",
    background:
      "linear-gradient(180deg, rgba(255,255,255,.08), rgba(255,255,255,.04))",
    boxShadow: "inset 0 1px 0 rgba(255,255,255,.06)",
    padding: "clamp(8px, 1.6vw, 12px)",
    display: "grid",
    gap: 8,
  },
  infoSection: {
    display: "grid",
    placeItems: "center",
    gap: 4,
  },
  infoLabel: {
    fontSize: 10,
    textTransform: "uppercase",
    letterSpacing: ".18em",
    color: "rgba(255,255,255,.55)",
  },
  meaningEn: {
    fontSize: "clamp(14px, 2.9vw, 18px)",
    color: "rgba(255,255,255,.95)",
    fontWeight: 700,
    lineHeight: 1.35,
  },
  revealBtn: {
    padding: "7px 10px",
    borderRadius: 999,
    border: "1px solid rgba(255,255,255,.18)",
    background: "rgba(255,255,255,.06)",
    fontSize: 12,
  },
  meaningEs: {
    fontSize: "clamp(13px, 2.7vw, 17px)",
    color: "rgba(255,255,255,.82)",
    fontWeight: 600,
    lineHeight: 1.35,
  },
  exampleText: {
    fontSize: "clamp(14px, 3vw, 18px)",
    color: "rgba(255,255,255,.90)",
    maxWidth: 520,
    lineHeight: 1.35,
  },
  divider: {
    height: 1,
    width: "100%",
    background:
      "linear-gradient(90deg, rgba(255,255,255,0), rgba(255,255,255,.18), rgba(255,255,255,0))",
  },

  listen: {
    borderRadius: 999,
    padding: "9px 12px",
    fontSize: 13,
  },
  listenSmall: {
    borderRadius: 999,
    padding: "7px 10px",
    fontSize: 12,
  },

  imagePlaceholder: {
    width: "clamp(70px, 18vw, 90px)",
    height: "clamp(70px, 18vw, 90px)",
    borderRadius: 18,
    border: "1px dashed rgba(255,255,255,.20)",
    display: "grid",
    placeItems: "center",
    color: "rgba(255,255,255,.55)",
    background: "rgba(0,0,0,.15)",
  },

  smallLink: {
    fontSize: 12,
    color: "rgba(255,255,255,.62)",
    textTransform: "uppercase",
    letterSpacing: ".12em",
    marginTop: 2,
    opacity: 0.9,
  },

  faceBottom: {
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    paddingTop: 10,
    paddingBottom: 6,
    color: "rgba(255,255,255,.72)",
  },

  flipBtn: {
    padding: "10px 12px",
    borderRadius: 12,
  },

};




