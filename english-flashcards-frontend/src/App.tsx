import { useCallback, useEffect, useState } from "react";
import { apiGet, apiPost } from "./api/client";
import { Frame } from "./components/Frame";
import { Landing } from "./pages/Landing";
import { MainFlashcard } from "./pages/MainFlashcard";

type AuthUser = {
  id: number;
  email: string;
  name?: string | null;
  avatar_url?: string | null;
};

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined;

export default function App() {
  const [checkingSession, setCheckingSession] = useState(true);
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const me = await apiGet<AuthUser>("/auth/me");
        setUser(me);
      } catch {
        setUser(null);
      } finally {
        setCheckingSession(false);
      }
    })();
  }, []);

  const handleGoogleCredential = useCallback(async (credential: string) => {
    try {
      setAuthLoading(true);
      setAuthError(null);
      const loggedUser = await apiPost<AuthUser>("/auth/google", { credential });
      setUser(loggedUser);
    } catch {
      setAuthError("Could not sign in with Google. Please try again.");
    } finally {
      setAuthLoading(false);
    }
  }, []);

  const handleLogout = useCallback(async () => {
    try {
      await apiPost<{ ok: boolean }>("/auth/logout");
    } finally {
      setUser(null);
    }
  }, []);

  return (
    <Frame>
      {checkingSession ? (
        <div className="pill">Checking session...</div>
      ) : user ? (
        <MainFlashcard
          userName={user.name || user.email}
          onLogout={handleLogout}
        />
      ) : (
        <Landing
          googleClientId={GOOGLE_CLIENT_ID}
          authLoading={authLoading}
          authError={authError}
          onGoogleCredential={handleGoogleCredential}
        />
      )}
    </Frame>
  );
}
