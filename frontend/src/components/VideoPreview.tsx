import { useEffect, useState } from "react";

import "../styles/VideoPreview.css";

type Props = {
    file?: File | null;
    videoUrl?: string;
    fileName?: string;
    duration?: string;
};

export default function VideoPreview({
    file,
    videoUrl,
    fileName,
    duration = "--:--",
}: Props) {

    const [url, setUrl] = useState<string>("");

    useEffect(() => {

        if (videoUrl) {

            setUrl(videoUrl);
            return;

        }

        if (file) {

            const objectUrl = URL.createObjectURL(file);

            setUrl(objectUrl);

            return () => {

                URL.revokeObjectURL(objectUrl);

            };

        }

        setUrl("");

    }, [file, videoUrl]);

    return (

        <div className="video-preview">

            <div className="video-container">

                {url ? (

                    <video
                        controls
                        src={url}
                    />

                ) : (

                    <div className="video-placeholder">

                        <div className="play-icon">
                            ▶
                        </div>

                        <h3>No Video Selected</h3>

                        <p>
                            Upload a football match to preview it here.
                        </p>

                    </div>

                )}

            </div>

            <div className="video-info">

                <div>

                    <h3>
                        {file?.name ??
                            fileName ??
                            "football_match.mp4"}
                    </h3>

                    <p>{duration}</p>

                </div>

                <span className="video-status">
                    Ready
                </span>

            </div>

        </div>

    );

}