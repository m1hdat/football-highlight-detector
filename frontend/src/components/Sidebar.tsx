import { FaHome, FaFutbol, FaUsers } from "react-icons/fa";
import { NavLink } from "react-router-dom";

function Sidebar() {
    return (
        <aside className="sidebar">
            <div className="logo">
                <FaFutbol size={30} />
                <div>
                    <h2>Football AI</h2>
                    <small>Highlight Cutter</small>
                </div>
            </div>

            <nav>
                <NavLink to="/">
                    <FaHome />
                    Dashboard
                </NavLink>

                <NavLink to="/detect">
                    <FaFutbol />
                    Detect
                </NavLink>

                <NavLink to="/about">
                    <FaUsers />
                    About
                </NavLink>
            </nav>
        </aside>
    );
}

export default Sidebar;
