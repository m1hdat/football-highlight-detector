# Backend — Football Highlight Detection System

Backend FastAPI tiếp nhận video, quản lý job nền, gọi official SoccerNet TF2 feature extractor, chạy temporal event model và cắt clip bằng FFmpeg.

## Hai môi trường

- `.venv`: FastAPI, PyTorch và code backend.
- Conda environment `SoccerNet-FeatureExtraction`: Python 3.7, TensorFlow 2.3 và official extractor.

Backend mặc định gọi môi trường thứ hai bằng `conda run`, không cần tự tìm đường dẫn `python.exe`.

## Cài đặt khuyến nghị

Từ thư mục gốc repository:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

## Chạy backend riêng

Sau khi setup:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
$env:SOCCERNET_EXECUTION_MODE="conda"
$env:SOCCERNET_CONDA_ENV="SoccerNet-FeatureExtraction"
$env:SOCCERNET_GPU="-1"
python -m uvicorn app.main:app --reload
```

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

Health chỉ trả `ready=true` khi model artifacts, extractor assets và dependency của Conda runtime đều sẵn sàng.

## Kiểm tra

```powershell
pytest
```

```powershell
python -c "from app.pipeline.feature_extractor import preflight_soccernet_extractor; import pprint; pprint.pp(preflight_soccernet_extractor())"
```

Xem README ở thư mục gốc để biết hướng dẫn thủ công và xử lý lỗi.
