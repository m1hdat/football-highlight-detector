# Hướng dẫn chạy nhanh

## Cách khuyến nghị

Từ thư mục gốc repository:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

Chỉ cần chạy `setup.ps1` lần đầu hoặc sau khi dependency thay đổi. Những lần sau chỉ chạy `run.ps1`.

## Địa chỉ

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Health: `http://localhost:8000/health`
- Swagger: `http://localhost:8000/docs`

## Chạy thủ công

Backend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
$env:SOCCERNET_EXECUTION_MODE="conda"
$env:SOCCERNET_CONDA_ENV="SoccerNet-FeatureExtraction"
$env:SOCCERNET_GPU="-1"
python -m uvicorn app.main:app --reload
```

Frontend:

```powershell
cd frontend
npm run dev
```

Không cần đặt `SOCCERNET_EXTRACTOR_PYTHON`. Backend mặc định dùng `conda run` để nạp đúng DLL và OpenSSL của Conda environment.
