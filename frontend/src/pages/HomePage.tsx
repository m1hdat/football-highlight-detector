import { Link } from "react-router-dom";
import {
    FaFutbol,
    FaVideo,
    FaBolt,
    FaClock,
    FaBullseye,
    FaRobot,
    FaServer,
    FaPlus,
} from "react-icons/fa";

function HomePage() {
    return (
        <div className="dashboard">
            <section className="hero">
                <div className="hero-left">
                    <div className="welcome">
                        <span>👋🏻 Welcome</span>
                    </div>
                    <h1>Football Highlight Cutter</h1>
                    <h3>AI-powered Event Detection and Clip Generation</h3>
                    <p>
                        Upload a football video, automatically detect important events,
                        and generate ready-to-review highlight clips.
                    </p>

                    <Link to="/detect" className="primary-btn">
                        <FaPlus />
                        Detect New Match
                    </Link>
                </div>

                <div className="hero-right">
                    <FaFutbol />
                </div>
            </section>

            <section className="statistics">
                <div className="stat-card">
                    <FaVideo className="stat-icon" />
                    <h2>6</h2>
                    <span>Event Categories</span>
                </div>

                <div className="stat-card">
                    <FaBolt className="stat-icon" />
                    <h2>AI</h2>
                    <span>Automatic Detection</span>
                </div>

                <div className="stat-card">
                    <FaClock className="stat-icon" />
                    <h2>Job</h2>
                    <span>Progress Tracking</span>
                </div>

                <div className="stat-card">
                    <FaBullseye className="stat-icon" />
                    <h2>ZIP</h2>
                    <span>Download Results</span>
                </div>
            </section>

            <div className="features">
                <h2>System Features</h2>
                <div className="feature-list">
                    <div className="feature-card">
                        <FaBullseye className="feature-icon" />
                        <h4>Event Detection</h4>
                        <p>Locates important football events along the video timeline.</p>
                    </div>

                    <div className="feature-card">
                        <FaVideo className="feature-icon" />
                        <h4>Automatic Clip Cutting</h4>
                        <p>Generates downloadable clips around detected events.</p>
                    </div>

                    <div className="feature-card">
                        <FaRobot className="feature-icon" />
                        <h4>Six Event Categories</h4>
                        <p>Goal, Shot, Corner, DirectFreeKick, Penalty and Card.</p>
                    </div>

                    <div className="feature-card">
                        <FaServer className="feature-icon" />
                        <h4>End-to-End Processing</h4>
                        <p>Handles upload, detection, ranking, clip cutting and downloads.</p>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default HomePage;
