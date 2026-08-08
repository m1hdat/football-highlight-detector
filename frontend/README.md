# Frontend — Football Highlight Detection System

Frontend React/TypeScript cung cấp giao diện upload video, theo dõi tiến trình, xem danh sách highlight và tải kết quả từ backend.

## Yêu cầu

- Node.js 20.19+ hoặc 22.12+
- npm
- Backend chạy tại `http://localhost:8000`

## Cách khuyến nghị

Từ thư mục gốc repository:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

## Chạy riêng frontend

```powershell
cd frontend
npm ci
npm run dev
```

Mở `http://localhost:5173`.

## Luồng giao diện

```text
Chọn video
→ POST /upload
→ polling GET /jobs/{job_id}/status
→ GET /jobs/{job_id}/results
→ xem hoặc tải clip
```

## Nhãn hiển thị

- Goal
- Shot
- Corner
- DirectFreeKick
- Penalty
- Card

## Các lệnh hữu ích

```powershell
npm run dev
npm run build
npm run lint
npm run preview
```
