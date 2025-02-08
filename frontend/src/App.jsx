import React from 'react';
import {BrowserRouter as Router, Routes, Route} from 'react-router-dom';
import Layout from './components/Layout';
import Home from './pages/Home';
import PrivacyPolicy from './pages/PrivacyPolicy';
// import Terms from './pages/Terms';
// import Contact from './pages/Contact';

import NotFound from "./pages/NotFound.jsx";

function App() {
    return (
        <Router>
            <Layout>
                <Routes>
                    <Route path="/" element={<Home/>}/>

                    <Route path="/privacy-policy" element={<PrivacyPolicy/>}/>
                    {/*<Route path="/terms" element={<Terms/>}/>*/}
                    {/*<Route path="/contact" element={<Contact/>}/>*/}

                    <Route path="*" element={<NotFound/>}/>
                </Routes>
            </Layout>
        </Router>
    );
}

export default App;
