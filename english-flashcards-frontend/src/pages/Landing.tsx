import { useEffect, useRef } from "react";

declare global {
  interface Window {
    google?: {
      accounts?: {
        id?: {
          initialize: (config: {
            client_id: string;
            callback: (response: { credential?: string }) => void;
          }) => void;
          renderButton: (
            parent: HTMLElement,
            options: {
              type?: "standard" | "icon";
              theme?: "outline" | "filled_blue" | "filled_black";
              text?: "signin_with" | "signup_with" | "continue_with" | "signin";
              shape?: "rectangular" | "pill" | "circle" | "square";
              size?: "large" | "medium" | "small";
              width?: number;
            }
          ) => void;
        };
      };
    };
  }
}

type LandingProps = {
  googleClientId?: string;
  authLoading: boolean;
  authError: string | null;
  onGoogleCredential: (credential: string) => void;
};

const GOOGLE_SCRIPT_ID = "google-identity-services";

export function Landing({
  googleClientId,
  authLoading,
  authError,
  onGoogleCredential,
}: LandingProps) {
  const buttonRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!googleClientId || !buttonRef.current) return;

    const renderGoogleButton = () => {
      const googleId = window.google?.accounts?.id;
      if (!googleId || !buttonRef.current) return;

      googleId.initialize({
        client_id: googleClientId,
        callback: (res) => {
          const credential = res.credential?.trim();
          if (credential) onGoogleCredential(credential);
        },
      });

      buttonRef.current.innerHTML = "";
      googleId.renderButton(buttonRef.current, {
        type: "standard",
        theme: "outline",
        text: "continue_with",
        shape: "pill",
        size: "large",
        width: 280,
      });
    };

    if (window.google?.accounts?.id) {
      renderGoogleButton();
      return;
    }

    const existing = document.getElementById(GOOGLE_SCRIPT_ID) as HTMLScriptElement | null;
    if (existing) {
      existing.addEventListener("load", renderGoogleButton, { once: true });
      return;
    }

    const script = document.createElement("script");
    script.id = GOOGLE_SCRIPT_ID;
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.onload = renderGoogleButton;
    document.head.appendChild(script);
  }, [googleClientId, onGoogleCredential]);

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

      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 26 }}>
        <span className="pill">Short sessions</span>
        <span className="pill">Remember better</span>
        <span className="pill">Listen and repeat</span>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 12, width: 300 }}>
        {!googleClientId ? (
          <div className="pill" style={{ borderRadius: 14 }}>
            Missing `VITE_GOOGLE_CLIENT_ID` in frontend `.env`.
          </div>
        ) : (
          <div
            ref={buttonRef}
            style={{
              minHeight: 44,
              display: "flex",
              alignItems: "center",
            }}
          />
        )}

        {authLoading && <div className="link">Signing in...</div>}
        {authError && (
          <div className="link" style={{ color: "var(--danger)" }}>
            {authError}
          </div>
        )}
      </div>
    </div>
  );
}
