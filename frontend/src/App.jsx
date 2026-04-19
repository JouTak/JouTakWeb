import { Suspense, lazy } from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
  useNavigate,
  useLocation,
} from "react-router-dom";

import Layout from "./components/Layout";
import AuthModal from "./components/AuthModal.jsx";
import RequireAuth from "./components/RequireAuth.jsx";
import ScrollToTop from "./components/ScrollToTop.jsx";

const JouTak = lazy(() => import("./pages/JouTak.jsx"));
const Legacy = lazy(() => import("./pages/Legacy.jsx"));
const MiniGames = lazy(() => import("./pages/Minigames.jsx"));
const ItmoCraft = lazy(() => import("./pages/ItmoCraft.jsx"));
const Contact = lazy(() => import("./pages/Contact.jsx"));
const NotFound = lazy(() => import("./pages/NotFound.jsx"));
const Unauthorized = lazy(() => import("./pages/Unauthorized.jsx"));
const AccountSecurity = lazy(() => import("./pages/AccountSecurity.jsx"));
const AccountOnboarding = lazy(() => import("./pages/AccountOnboarding.jsx"));
const SessionExpired = lazy(() => import("./pages/SessionExpired.jsx"));
const ConfirmEmail = lazy(() => import("./pages/ConfirmEmail.jsx"));
const ResetPassword = lazy(() => import("./pages/ResetPassword.jsx"));
const Pay = lazy(() => import("./pages/joutak/Pay.jsx"));

function safeInternalPath(path) {
  if (typeof path !== "string") return "/joutak";
  if (!path.startsWith("/")) return "/joutak";
  if (path.startsWith("//")) return "/joutak";
  return path;
}

function RouteFallback() {
  return <div className="py-5 text-center text-secondary">Загрузка...</div>;
}

function LoginModalRoute() {
  const navigate = useNavigate();
  const location = useLocation();
  const params = new URLSearchParams(location.search);
  const nextFromQuery = params.get("next");
  const nextFromState = location.state?.next;
  const successRedirectTo = safeInternalPath(
    nextFromQuery || nextFromState || "/joutak",
  );

  return (
    <AuthModal
      open
      onClose={() => navigate(-1)}
      successRedirectTo={successRedirectTo}
    />
  );
}

function AppRoutes() {
  const location = useLocation();
  const background = location.state && location.state.background;

  return (
    <Suspense fallback={<RouteFallback />}>
      <Routes location={background || location}>
        <Route path="/" element={<Navigate to="/joutak" replace />} />
        <Route path="/joutak" element={<JouTak />} />
        <Route path="/legacy" element={<Legacy />} />
        <Route path="/itmocraft" element={<ItmoCraft />} />
        <Route path="/minigames" element={<MiniGames />} />
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

        <Route path="/401" element={<Unauthorized />} />
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
    <Router>
      <ScrollToTop />
      <Layout>
        <AppRoutes />
      </Layout>
    </Router>
  );
}
