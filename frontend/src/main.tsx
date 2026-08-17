import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./index.css";
import App from "./App.tsx";
import { FIDICHistoryPage } from "./pages/FIDICHistoryPage";
import { AuthProvider } from "./contexts/AuthContext";
import { AuthModal } from "./components/AuthModal";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<App />} />
          <Route path="/fidic-history" element={<FIDICHistoryPage />} />
        </Routes>
      </BrowserRouter>
      <AuthModal />
    </AuthProvider>
  </StrictMode>,
);
