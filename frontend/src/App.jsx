import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
  useNavigate,
  useLocation,
} from "react-router-dom";

import Layout from "./components/Layout";
import JouTak from "./pages/JouTak";
import Legacy from "./pages/Legacy.jsx";
import MiniGames from "./pages/Minigames.jsx";
import ItmoCraft from "./pages/ItmoCraft.jsx";
import Contact from "./pages/Contact.jsx";
import NotFound from "./pages/NotFound.jsx";
import AuthModal from "./components/AuthModal.jsx";
import AccountSecurity from "./pages/AccountSecurity.jsx";
import AccountOnboarding from "./pages/AccountOnboarding.jsx";
import SessionExpired from "./pages/SessionExpired.jsx";
import RequireAuth from "./components/RequireAuth.jsx";
import Pay from "./pages/joutak/Pay.jsx";
import ScrollToTop from "./components/ScrollToTop.jsx";

function safeInternalPath(path) {
  if (typeof path !== "string") return "/joutak";
  if (!path.startsWith("/")) return "/joutak";
  if (path.startsWith("//")) return "/joutak";
  return path;
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
    <>
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

        <Route path="/login" element={<LoginModalRoute />} />
        <Route path="*" element={<NotFound />} />
      </Routes>

      {background && (
        <Routes>
          <Route path="/login" element={<LoginModalRoute />} />
        </Routes>
      )}
    </>
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
