import client from "./client";

export async function getJobStatus(jobId: string) {
    const response = await client.get(
        `/jobs/${jobId}/status`
    );

    return response.data;
}

export async function getResults(jobId: string) {
    const response = await client.get(
        `/jobs/${jobId}/results`
    );

    return response.data;
}

export function getClipUrl(clipUrl: string, download = false) {
    const baseUrl = client.defaults.baseURL ?? window.location.origin;
    const url = new URL(clipUrl, baseUrl);

    if (download) {
        url.searchParams.set("download", "true");
    }

    return url.toString();
}

export function getDownloadAllUrl(jobId: string) {
    return `${client.defaults.baseURL}/jobs/${jobId}/download-all`;
}