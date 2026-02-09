import React from "react";

type Props = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "ghost";
};

export function Button({ variant = "primary", style, ...props }: Props) {
  const base: React.CSSProperties = {
    fontFamily: "inherit",
    fontSize: 18,
    padding: "10px 16px",
    border: "2px solid #111",
    background: variant === "primary" ? "#fff" : "transparent",
    cursor: "pointer",
  };

  return <button {...props} style={{ ...base, ...style }} />;
}
