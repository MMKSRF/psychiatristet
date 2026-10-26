import { createContext, useContext, useMemo, useState } from "react";

const ThemeContext = createContext(null);

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => localStorage.getItem("carebridge-theme") || "light");
  const value = useMemo(
    () => ({
      theme,
      toggleTheme: () =>
        setTheme((current) => {
          const next = current === "light" ? "dark" : "light";
          localStorage.setItem("carebridge-theme", next);
          return next;
        }),
    }),
    [theme],
  );
  return (
    <ThemeContext.Provider value={value}>
      <div className={theme === "dark" ? "dark min-h-screen" : "min-h-screen"}>{children}</div>
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const theme = useContext(ThemeContext);
  if (!theme) throw new Error("useTheme must be used inside ThemeProvider");
  return theme;
}
