import client from "./client";

export async function uploadVideo(file: File) {
    const formData = new FormData();
    formData.append("file", file);

    const response = await client.post("/upload", formData);
    return response.data;
}
