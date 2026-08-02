import { lazy, Suspense } from "react";
import { Route, Routes, useLocation, useNavigate } from "react-router-dom";

import AuthModal from "./components/AuthModal.jsx";
import Layout from "./components/Layout";
import RequireAuth from "./components/RequireAuth.jsx";
import ScrollToTop from "./components/ScrollToTop.jsx";
import {
  LoadingPage,
  PagePanel,
  PageShell,
} from "./components/ui/PageShell.jsx";
const Legacy = lazy(() => import("./pages/Legacy.jsx"));
const Contact = lazy(() => import("./pages/Contact.jsx"));
const NotFound = lazy(() => import("./pages/NotFound.jsx"));
const AccountSecurity = lazy(() => import("./pages/AccountSecurity.jsx"));
const AccountOnboarding = lazy(() => import("./pages/AccountOnboarding.jsx"));
const SessionExpired = lazy(() => import("./pages/SessionExpired.jsx"));
const ConfirmEmail = lazy(() => import("./pages/ConfirmEmail.jsx"));
const ResetPassword = lazy(() => import("./pages/ResetPassword.jsx"));
const Pay = lazy(() => import("./pages/joutak/Pay.jsx"));
const ItmoCraftRoute = lazy(
  () => import("./pages/itmocraft/ItmoCraftRoute.jsx"),
);
const JouTakRoute = lazy(() => import("./pages/joutak/JouTakRoute.jsx"));
const MinigamesRoute = lazy(
  () => import("./pages/minigames/MinigamesRoute.jsx"),
);

function safeInternalPath(path) {
  if (typeof path !== "string") return "/";
  if (!path.startsWith("/")) return "/";
  if (path.startsWith("//")) return "/";
  return path;
}

function RouteFallback() {
  return <LoadingPage />;
}

function LoginModalRoute() {
  const navigate = useNavigate();
  const location = useLocation();
  const params = new URLSearchParams(location.search);
  const nextFromQuery = params.get("next");
  const nextFromState = location.state?.next;
  const successRedirectTo = safeInternalPath(
    nextFromQuery || nextFromState || "/",
  );
  const hasBackground = Boolean(location.state?.background);

  return (
    <>
      {!hasBackground && (
        <PageShell
          narrow
          eyebrow="Аккаунт"
          title="Вход в ITMOcraft"
          description="Безопасный доступ к профилю, игровым привязкам и настройкам аккаунта."
        >
          <PagePanel>
            Окно входа открыто поверх страницы. После авторизации мы вернём тебя
            к выбранному сценарию.
          </PagePanel>
        </PageShell>
      )}
      <AuthModal
        open
        onClose={() =>
          hasBackground ? navigate(-1) : navigate("/", { replace: true })
        }
        successRedirectTo={successRedirectTo}
      />
    </>
  );
}

function AppRoutes() {
  const location = useLocation();
  const background = location.state && location.state.background;

  return (
    <Suspense fallback={<RouteFallback />}>
      <Routes location={background || location}>
        <Route path="/" element={<ItmoCraftRoute />} />
        <Route path="/joutak" element={<JouTakRoute />} />
        <Route path="/legacy" element={<Legacy />} />
        <Route path="/minigames" element={<MinigamesRoute />} />
        <Route path="/itmocraft" element={<ItmoCraftRoute legacyAlias />} />
        <Route path="/contact" element={<Contact />} />
        <Route
          path="/account/security"
          element={
            <RequireAuth>
              <AccountSecurity />
            </RequireAuth>
          }
        />
        <Route
          path="/account/onboarding"
          element={
            <RequireAuth>
              <AccountOnboarding />
            </RequireAuth>
          }
        />
        <Route
          path="/account/complete-registration"
          element={
            <RequireAuth>
              <AccountOnboarding />
            </RequireAuth>
          }
        />
        <Route
          path="/account/complete-profile"
          element={
            <RequireAuth>
              <AccountOnboarding />
            </RequireAuth>
          }
        />
        <Route path="/joutak/pay" element={<Pay />} />
        <Route path="/session-expired" element={<SessionExpired />} />
        <Route path="/confirm-email" element={<ConfirmEmail />} />
        <Route path="/reset-password" element={<ResetPassword />} />

        <Route path="/login" element={<LoginModalRoute />} />
        <Route path="*" element={<NotFound />} />
      </Routes>

      {background && (
        <Routes>
          <Route path="/login" element={<LoginModalRoute />} />
        </Routes>
      )}
    </Suspense>
  );
}

export default function App() {
  return (
    <>
      <ScrollToTop />
      <Layout>
        <AppRoutes />
      </Layout>
    </>
  );
}
