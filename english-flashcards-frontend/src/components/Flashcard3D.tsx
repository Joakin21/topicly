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
              🔊 Listen
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
          <div style={styles.center}>
            <div style={styles.headword}>{card.headword}</div>

            <button
              className="btn"
              style={styles.listen}
              onClick={() => onSpeak(card.headword)}
            >
              🔊 Listen
            </button>

            <div style={styles.imagePlaceholder}>[ image ]</div>

            <div style={styles.meaning}>{card.meaningEs}</div>

            <div style={styles.example}>{card.exampleBack}</div>

            <button
              className="btn"
              style={styles.listen}
              onClick={() => onSpeak(stripQuotes(card.exampleBack))}
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
    height: "min(64vh, 620px)",
    minHeight: 520,
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
    gap: "clamp(8px, 1.8vh, 12px)",
    padding: "clamp(8px, 1.8vh, 12px) clamp(10px, 2.2vw, 12px)",
    minHeight: 0,
    overflow: "auto",
    overscrollBehavior: "contain",
  },

  headword: {
    fontSize: "clamp(30px, 5.8vw, 44px)",
    fontWeight: 800,
    letterSpacing: -0.6,
    marginTop: 4,
  },
  example: {
    fontSize: "clamp(16px, 3.7vw, 22px)",
    color: "rgba(255,255,255,.88)",
    maxWidth: 520,
    lineHeight: 1.45,
    padding: "2px 0",
  },
  meaning: {
    fontSize: "clamp(16px, 3.8vw, 22px)",
    color: "rgba(255,255,255,.92)",
    fontWeight: 700,
  },

  listen: {
    borderRadius: 999,
    padding: "10px 14px",
  },

  imagePlaceholder: {
    width: "clamp(86px, 22vw, 110px)",
    height: "clamp(86px, 22vw, 110px)",
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
