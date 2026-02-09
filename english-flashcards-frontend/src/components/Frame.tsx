import React from "react";

export function Frame({ children }: { children: React.ReactNode }) {
  return (
    <div style={styles.wrap}>
      <div style={styles.shell}>
        <div style={styles.glow} />
        <div style={styles.content}>{children}</div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrap: {
    minHeight: "100vh",
    display: "grid",
    placeItems: "center",
    padding: "clamp(10px, 3vw, 22px)", // ✅ responsive padding
  },
  shell: {
    width: "min(820px, 100%)",
    minHeight: "min(860px, 94vh)", // ✅ un poco más compacto en móvil
    borderRadius: 28,
    border: "1px solid rgba(255,255,255,.14)",
    background: "rgba(255,255,255,.06)",
    boxShadow: "0 20px 60px rgba(0,0,0,.45)",
    backdropFilter: "blur(14px)",
    position: "relative",
    overflow: "hidden",
  },
  glow: {
    position: "absolute",
    inset: -80,
    background:
      "radial-gradient(500px 340px at 20% 20%, rgba(124,92,255,.22), transparent 60%)," +
      "radial-gradient(420px 300px at 80% 15%, rgba(34,197,94,.16), transparent 55%)",
    filter: "blur(18px)",
    pointerEvents: "none",
  },
  content: {
    position: "relative",
    padding: "clamp(14px, 3.2vw, 22px)", // ✅ responsive padding interno
  },
};
