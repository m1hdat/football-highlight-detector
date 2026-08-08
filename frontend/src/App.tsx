import { Routes, Route } from "react-router-dom";

import Sidebar from "./components/Sidebar.tsx";
import HomePage from "./pages/HomePage.tsx";
import DetectPage from "./pages/DetectPage.tsx";
import AboutPage from "./pages/AboutPage.tsx";

function App() {
    return (
        <div className="app">
            <Sidebar />

            <main className="content">
                <Routes>
                    <Route path="/" element={<HomePage />} />
                    <Route path="/detect" element={<DetectPage />} />
                    <Route path="/about" element={<AboutPage />} />
                </Routes>
            </main>
        </div>
    );
}

export default App;
