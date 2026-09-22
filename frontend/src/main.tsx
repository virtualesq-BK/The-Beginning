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
const StandardContractComparePage = lazy(() =>
  import("./pages/StandardContractComparePage").then((m) => ({ default: m.StandardContractComparePage })),
);
const StandardContractHistoryPage = lazy(() =>
  import("./pages/StandardContractHistoryPage").then((m) => ({ default: m.StandardContractHistoryPage })),
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
            <Route path="/standard-contract-compare" element={<StandardContractComparePage />} />
            <Route path="/standard-contract-history" element={<StandardContractHistoryPage />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
      <Suspense fallback={null}>
        <AuthModal />
      </Suspense>
    </AuthProvider>
  </StrictMode>,
);
