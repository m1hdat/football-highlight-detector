import type { Highlight } from "../types/highlight.ts";
import HighlightCard from "./HighlightCard";

type Props = {
    highlights: Highlight[];
};

export default function HighlightList({ highlights }: Props) {
    if (highlights.length === 0) {
        return (
            <div className="empty-highlight">
                <div className="empty-icon">🎬</div>
                <h3>No Highlights Yet</h3>
                <p>Detected highlights will appear here.</p>
            </div>
        );
    }

    return (
        <div className="highlight-list">
            {highlights.map((highlight) => (
                <HighlightCard
                    key={highlight.clip_id}
                    highlight={highlight}
                />
            ))}
        </div>
    );
}