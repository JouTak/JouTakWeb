import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { ThemeProvider } from '@gravity-ui/uikit';

import Layout from "./components/Layout";
import Home from "./pages/Home";
import PrivacyPolicy from "./pages/PrivacyPolicy";
import NotFound from "./pages/NotFound.jsx";
// import Terms from './pages/Terms';
// import Contact from './pages/Contact';

import '@gravity-ui/uikit/styles/fonts.css';
import '@gravity-ui/uikit/styles/styles.css';

function App() {
    return (
        <ThemeProvider>
            <Router>
                <Layout>
                    <Routes>
                        <Route path="/" element={<Home />} />
                        <Route path="/privacy-policy" element={<PrivacyPolicy />} />
                        <Route path="*" element={<NotFound />} />
                    </Routes>
                </Layout>
            </Router>
        </ThemeProvider>
    );
}

export default App;
