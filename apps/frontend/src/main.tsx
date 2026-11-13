import React from "react";
import { createRoot } from "react-dom/client";
import { AuthRoot } from "./features/accounts/AuthRoot";
import "./styles.css";
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AuthRoot />
  </React.StrictMode>,
);
