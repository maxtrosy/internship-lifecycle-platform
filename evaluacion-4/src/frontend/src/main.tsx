import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";
import "./theme.css";
import { ThemeProvider } from "./theme";
import { ConfirmProvider } from "./components/overlays";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider><ConfirmProvider><App /></ConfirmProvider></ThemeProvider>
  </StrictMode>,
);
