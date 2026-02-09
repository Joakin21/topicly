export function Landing({ onStart }: { onStart: () => void }) {
  return (
    <div style={{ position: "relative" }}>
      <div className="kicker">English that actually matters</div>
      <div className="h1">
        Learn useful English.
        <br />
        Fast.
      </div>

      <div className="sub" style={{ maxWidth: 520, marginBottom: 22 }}>
        Real vocabulary. Real phrases. Practice with flashcards that feel like a
        modern product.
      </div>

      <div
        style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 26 }}
      >
        <span className="pill">⚡ Short sessions</span>
        <span className="pill">🧠 Remember better</span>
        <span className="pill">🔊 Listen & repeat</span>
      </div>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 12,
          width: 280,
        }}
      >
        <button className="btn btnPrimary" onClick={onStart}>
          Start learning →
        </button>
        <a className="link" href="#">
          Log in
        </a>
      </div>
    </div>
  );
}
