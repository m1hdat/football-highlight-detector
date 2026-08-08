export interface UploadJob {
    job_id: string;
    filename: string;
    status: "uploaded";
}

export interface JobStatus {
    job_id: string;
    status:
        | "uploaded"
        | "extracting_feature"
        | "detecting_highlight"
        | "classifying"
        | "cutting_video"
        | "done"
        | "failed";
    progress: number;
    message: string;
}
