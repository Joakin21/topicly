import { useState } from "react";
import { Frame } from "./components/Frame";
import { Landing } from "./pages/Landing";
import { MainFlashcard } from "./pages/MainFlashcard";

type Screen = "landing" | "main";

export default function App() {
  const [screen, setScreen] = useState<Screen>("landing");

  return (
    <Frame>
      {screen === "landing" ? (
        <Landing onStart={() => setScreen("main")} />
      ) : (
        <MainFlashcard />
      )}
    </Frame>
  );
}
