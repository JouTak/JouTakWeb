import {
    BrowserRouter as Router, Route, Routes, Navigate,
} from "react-router-dom";
import {ThemeProvider} from "@gravity-ui/uikit";

import Layout from "./components/Layout";
import Login from "./components/Auth/Login";
import Logout from "./components/Auth/Logout";
import JouTak from "./pages/JouTak";
import NotFound from "./pages/NotFound.jsx";
import Bedrock from "./pages/Bedrock.jsx";
import MiniGames from "./pages/Minigames.jsx";
import ItmoCraft from "./pages/ItmoCraft.jsx";
import Contact from "./pages/Contact.jsx";

import "@gravity-ui/uikit/styles/fonts.css";
import "@gravity-ui/uikit/styles/styles.css";
import {ToastContainer} from "react-toastify";
import PrivateRoute from "./context/PrivateRoute.jsx";

function App() {
    return (<ThemeProvider>
        <Router>
            <Layout>
                <ToastContainer position="bottom-right" autoClose={3000}/>
                <Routes>
                    <Route
                        path="*"
                        element={<PrivateRoute>
                            <UserPanel/>
                        </PrivateRoute>}
                    />
                    <Route path="/login" element={<Login/>}/>
                    <Route path="/logout" element={<Logout/>}/>
                    <Route path="/"
                           element={<Navigate to="/joutak" replace/>}/>
                    <Route path="/joutak" element={<JouTak/>}/>
                    <Route path="/bedrock" element={<Bedrock/>}/>
                    <Route path="/itmocraft" element={<ItmoCraft/>}/>
                    <Route path="/minigames" element={<MiniGames/>}/>
                    <Route path="/contact" element={<Contact/>}/>
                    <Route path="*" element={<NotFound/>}/>
                </Routes>
            </Layout>
        </Router>
    </ThemeProvider>);
}

function UserPanel() {
    return (<Routes>
        <Route path="/account" element={<NotFound/>}/>
        <Route path="*" element={<NotFound/>}/>
    </Routes>);
}

export default App;
