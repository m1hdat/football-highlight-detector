import { useState } from "react";
import { uploadVideo } from "../api/upload";
import { getJobStatus, getResults } from "../api/jobs";

import UploadBox from "../components/UploadBox";
import VideoPreview from "../components/VideoPreview";
import ProcessingStatus from "../components/ProcessingStatus";
import HighlightList from "../components/HighlightList";

import type { Highlight } from "../types/highlight";

function DetectPage() {
    const [video, setVideo] = useState<File | null>(null);

    const [processing, setProcessing] = useState(false);

    const [progress, setProgress] = useState(0);

    const [highlights, setHighlights] = useState<Highlight[]>([]);

    const handleVideoSelect = (file: File) => {
        setVideo(file);

        // Reset kết quả cũ khi chọn video mới
        setHighlights([]);
        setProgress(0);
    };

    const handleDetect = async () => {
        if (!video) return;

        setProcessing(true);

        try {
            // Upload video
            const uploadResponse = await uploadVideo(video);
            const jobId = uploadResponse.job_id;

            let finished = false;

            while (!finished) {

                const status = await getJobStatus(jobId);

                setProgress(status.progress);

                if (status.status === "done") {

                    finished = true;

                } else if (status.status === "failed") {

                    throw new Error("Highlight detection failed.");

                } else {

                    await new Promise(resolve =>
                        setTimeout(resolve, 1500)
                    );

                }
            }

            // Lấy kết quả
            const results = await getResults(jobId);

            setHighlights(results);

        } catch (error: any) {

            console.error(error);
            console.log(error.response?.data);
            alert(error.response?.data?.detail ?? "Upload failed");

        } finally {

            setProcessing(false);

        }
    };

    return (
        <div className="detect-page">

            <div className="detect-header">

                <h1>Football Highlight Detector</h1>

                <p>
                    Upload a football match video and let AI detect the highlights.
                </p>

            </div>

            <div className="detect-content">

                {/* LEFT */}

                <div className="left-panel">

                    <UploadBox
                        onSelect={handleVideoSelect}
                        onDetect={handleDetect}
                        disabled={processing || !video}
                    />

                    {processing && (
                        <ProcessingStatus
                            progress={progress}
                        />
                    )}

                </div>

                {/* RIGHT */}

                <div className="right-panel">

                    {/* Video Preview */}

                    <div className="video-preview">

                        {video ? (

                            <VideoPreview
                                file={video}
                            />

                        ) : (

                            <div className="empty-card">

                                <h2>Video Preview</h2>

                                <p>
                                    Select a football match to preview it here.
                                </p>

                            </div>

                        )}

                    </div>

                    {/* Highlight Result */}

                    {processing ? (

                        <></>

                    ) : highlights.length > 0 ? (

                        <HighlightList
                            highlights={highlights}
                        />

                    ) : (

                        <div className="empty-card">

                            <h2>Highlights</h2>

                            <p>
                                Detected highlights will appear here after the AI finishes processing the video.
                            </p>

                        </div>

                    )}

                </div>

            </div>

        </div>
    );
}

export default DetectPage;