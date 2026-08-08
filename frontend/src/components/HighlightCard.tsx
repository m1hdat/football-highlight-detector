import type { IconType } from "react-icons";
import {
    FaBullseye,
    FaExchangeAlt,
    FaFlag,
    FaFutbol,
    FaRegSquare,
    FaVideo,
} from "react-icons/fa";

import { getClipUrl } from "../api/jobs";
import type { Highlight } from "../types/highlight.ts";

type Props = {
    highlight: Highlight;
};

function formatTime(seconds: number): string {
    const totalSeconds = Math.max(0, Math.round(seconds));
    const minutes = Math.floor(totalSeconds / 60);
    const remainingSeconds = totalSeconds % 60;

    return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
}

function formatLabel(label: string): string {
    const normalized = label.trim().toLowerCase();

    if (normalized === "directfreekick" || normalized === "direct free kick") {
        return "Direct Free Kick";
    }

    return label
        .replace(/([a-z])([A-Z])/g, "$1 $2")
        .replace(/\b\w/g, (character) => character.toUpperCase());
}

function getIcon(label: string): IconType {
    switch (label.trim().toLowerCase()) {
        case "goal":
        case "shot":
            return FaFutbol;
        case "corner":
            return FaFlag;
        case "directfreekick":
        case "direct free kick":
        case "penalty":
            return FaBullseye;
        case "card":
            return FaRegSquare;
        case "substitution":
            return FaExchangeAlt;
        default:
            return FaVideo;
    }
}

export default function HighlightCard({ highlight }: Props) {
    const confidence = Math.max(
        0,
        Math.min(100, Math.round(highlight.highlight_confidence * 100)),
    );
    const EventIcon = getIcon(highlight.label);

    const handleDownload = () => {
        const anchor = document.createElement("a");
        anchor.href = getClipUrl(highlight.clip_url, true);
        anchor.download = `${highlight.clip_id}.mp4`;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
    };

    return (
        <article className="highlight-card">
            <div className="highlight-content">
                <div className="highlight-title">
                    <span className="highlight-icon" aria-hidden="true">
                        <EventIcon />
                    </span>
                    <div>
                        <span className="highlight-kicker">Detected event</span>
                        <h3>{formatLabel(highlight.label)}</h3>
                    </div>
                </div>

                <p className="highlight-time">
                    {formatTime(highlight.start)}
                    <span aria-hidden="true">→</span>
                    {formatTime(highlight.end)}
                </p>

                <div className="confidence">
                    <div className="confidence-header">
                        <span>Confidence</span>
                        <strong>{confidence}%</strong>
                    </div>

                    <div
                        className="confidence-bar"
                        role="progressbar"
                        aria-label="Highlight confidence"
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-valuenow={confidence}
                    >
                        <div
                            className="confidence-fill"
                            style={{ width: `${confidence}%` }}
                        />
                    </div>
                </div>

                <button
                    className="download-btn"
                    type="button"
                    onClick={handleDownload}
                >
                    Download Clip
                </button>
            </div>
        </article>
    );
}
