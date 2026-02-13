import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
  useNavigate,
  useLocation,
} from "react-router-dom";

import Forbidden from "./pages/Forbidden.jsx";
import Restricted from "./pages/Restricted.jsx";
import Layout from "./components/Layout";
import JouTak from "./pages/JouTak";
import Legacy from "./pages/Legacy.jsx";
import MiniGames from "./pages/Minigames.jsx";
import ItmoCraft from "./pages/ItmoCraft.jsx";
import Contact from "./pages/Contact.jsx";
import NotFound from "./pages/NotFound.jsx";
import AuthModal from "./components/AuthModal.jsx";
import AccountSecurity from "./pages/AccountSecurity.jsx";
import Pay from "./pages/joutak/Pay.jsx";
import ScrollToTop from "./components/ScrollToTop.jsx";

function LoginModalRoute() {
  const navigate = useNavigate();
  return <AuthModal open onClose={() => navigate(-1)} />;
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
        <Route path="/account/security" element={<AccountSecurity />} />
        <Route path="/joutak/pay" element={<Pay />} />

        <Route path="/login" element={<LoginModalRoute />} />
        <Route path="/403" element={<Forbidden />} />
        <Route path="/restricted" element={<Restricted />} />
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
