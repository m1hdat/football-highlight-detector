/**
 * Represents a highlight of the clip
 * example:
 * {
 *   "clip_id": "1234567890",
 *  "start": 10,
 *  "end": 20,
 * "peak_second": 15,
 * "label": "Exciting Moment",
 * "highlight_confidence": 0.95, 
 * "label_confidence": 0.9,
 * "clip_url": "https://example.com/clip.mp4"
 * }
 */

export interface Highlight {
    clip_id : string;
    start : number;
    end : number;
    peak_second : number;
    label : string;
    highlight_confidence : number;
    label_confidence : number;
    clip_url : string;
    // Visible label is Goal/Shot/Corner/DirectFreeKick/Penalty/Card.
    // Optional diagnostics retain the fine-grained event class.
    fine_label?: string;
    fine_events?: string[];
    event_score?: number;
    selection_score?: number;
}