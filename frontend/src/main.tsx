import { lazy, StrictMode, Suspense } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./index.css";
import "./i18n";
import App from "./App.tsx";
import { AuthProvider } from "./contexts/AuthContext";

const FIDICHistoryPage = lazy(() =>
  import("./pages/FIDICHistoryPage").then((m) => ({ default: m.FIDICHistoryPage })),
);
const AuthModal = lazy(() => import("./components/AuthModal").then((m) => ({ default: m.AuthModal })));

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <Suspense fallback={null}>
          <Routes>
            <Route path="/" element={<App />} />
            <Route path="/fidic-history" element={<FIDICHistoryPage />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
      <Suspense fallback={null}>
        <AuthModal />
      </Suspense>
    </AuthProvider>
  </StrictMode>,
);
