import {
  BrowserRouter as Router,
  Route,
  Routes,
  Navigate,
} from "react-router-dom";
import { ThemeProvider } from "@gravity-ui/uikit";

import Layout from "./components/Layout";
import JouTak from "./pages/JouTak";
import NotFound from "./pages/NotFound.jsx";
import Bedrock from "./pages/Bedrock.jsx";
import MiniGames from "./pages/Minigames.jsx";
import ItmoCraft from "./pages/ItmoCraft.jsx";
import Contact from "./pages/Contact.jsx";

import "@gravity-ui/uikit/styles/fonts.css";
import "@gravity-ui/uikit/styles/styles.css";
import ProfilePrototype from "./pages/ProfilePrototype.jsx";

function App() {
  return (
    <ThemeProvider>
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Navigate to="/joutak" replace />} />
            <Route path="/joutak" element={<JouTak />} />
            <Route path="/bedrock" element={<Bedrock />} />
            <Route path="/itmocraft" element={<ItmoCraft />} />
            <Route path="/minigames" element={<MiniGames />} />
            <Route path="/contact" element={<Contact />} />
            <Route path="/profile-prototype" element={<ProfilePrototype />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Layout>
      </Router>
    </ThemeProvider>
  );
}

export default App;
