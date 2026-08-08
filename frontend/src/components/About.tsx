import {
    FaBrain,
    FaCode,
    FaEnvelope,
    FaFacebook,
    FaGithub,
    FaPhone,
    FaServer,
} from "react-icons/fa";
import { MdSportsSoccer } from "react-icons/md";

import BKhangAvatar from "../assets/BKhang.jpg";
import MDatAvatar from "../assets/MDat.jpg";
import NHuyAvatar from "../assets/NHuy.jpg";
import PKhangAvatar from "../assets/PKhang.jpg";
import "../styles/About.css";

const members = [
    {
        name: "Huỳnh Bảo Khang",
        role: "Frontend Developer",
        email: "24120507@student.hcmus.edu.vn",
        phone: "0822402282",
        github: "https://github.com/khanghb2006",
        facebook: "https://www.facebook.com/khanghb2006",
        image: BKhangAvatar,
        icon: <FaCode />,
    },
    {
        name: "Nguyễn Phước Khang",
        role: "Backend Developer",
        email: "24120189@student.hcmus.edu.vn",
        phone: "0783462622",
        github: "https://github.com/Kh4nq",
        facebook: "https://www.facebook.com/share/1DK3SbwikN/?mibextid=wwXIfr",
        image: PKhangAvatar,
        icon: <FaServer />,
    },
    {
        name: "Hồ Ngọc Huy",
        role: "AI Engineer",
        email: "0917196047hongochuy.work@gmail.com",
        phone: "0917196047",
        github: "https://github.com/realRukashi",
        facebook: "https://www.facebook.com/rukashii27",
        image: NHuyAvatar,
        icon: <FaBrain />,
    },
    {
        name: "Phạm Minh Đạt",
        role: "AI Engineer",
        email: "phamminhdat2705@gmail.com",
        phone: "0858480666",
        github: "https://github.com/m1hdat",
        facebook: "https://www.facebook.com/fitus.mdat5",
        image: MDatAvatar,
        icon: <FaBrain />,
    },
];

function About() {
    return (
        <div className="about-page">
            <section className="about-hero">
                <div className="about-hero-left">
                    <span className="about-badge">AI PROJECT</span>
                    <h1>Football Highlight Detection</h1>
                    <p>
                        Football Highlight Detection là hệ thống sử dụng trí tuệ
                        nhân tạo nhằm tự động phát hiện các khoảnh khắc nổi bật
                        trong trận đấu bóng đá như bàn thắng, cú sút, thẻ phạt,
                        thay người và nhiều sự kiện hấp dẫn khác.
                    </p>

                    <div className="about-hero-btn">
                        <a href="#team" className="about-primary-action">
                            Explore Project
                        </a>
                        <a href="#features" className="about-secondary-action">
                            Learn More
                        </a>
                    </div>
                </div>

                <div className="about-hero-right" aria-hidden="true">
                    <MdSportsSoccer className="about-football-icon" />
                </div>
            </section>

            <section id="features" className="about-features">
                <article className="about-feature">
                    <h3>⚡ Flash Detection</h3>
                    <p>AI tự động phát hiện highlight trong vài phút.</p>
                </article>

                <article className="about-feature">
                    <h3>🎯 Accurate</h3>
                    <p>Deep Learning giúp phát hiện highlight chính xác hơn.</p>
                </article>

                <article className="about-feature">
                    <h3>💾 Download</h3>
                    <p>Tải về các highlight đã được phát hiện.</p>
                </article>
            </section>

            <section id="team" className="about-team">
                <h2>Meet Our Team</h2>

                <div className="about-team-grid">
                    {members.map((member) => (
                        <article className="about-member-card" key={member.email}>
                            <img src={member.image} alt={member.name} />

                            <div className="about-role-icon" aria-hidden="true">
                                {member.icon}
                            </div>

                            <h3>{member.name}</h3>
                            <span className="about-role">{member.role}</span>

                            <div className="about-contact">
                                <p>
                                    <FaPhone aria-hidden="true" />
                                    <a href={`tel:${member.phone}`}>{member.phone}</a>
                                </p>
                                <p className="about-email-row">
                                    <FaEnvelope aria-hidden="true" />
                                    <a
                                        href={`mailto:${member.email}`}
                                        title={member.email}
                                    >
                                        {member.email}
                                    </a>
                                </p>
                            </div>

                            <div className="about-social">
                                <a
                                    href={member.github}
                                    target="_blank"
                                    rel="noreferrer"
                                    aria-label={`${member.name} on GitHub`}
                                >
                                    <FaGithub />
                                </a>
                                <a
                                    href={member.facebook}
                                    target="_blank"
                                    rel="noreferrer"
                                    aria-label={`${member.name} on Facebook`}
                                >
                                    <FaFacebook />
                                </a>
                            </div>
                        </article>
                    ))}
                </div>
            </section>
        </div>
    );
}

export default About;
