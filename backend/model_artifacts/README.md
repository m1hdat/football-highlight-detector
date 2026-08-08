# Model artifacts

Thư mục này chứa checkpoint và cấu hình threshold của mô hình nhận diện sự kiện hiện tại.

```text
model_artifacts/
└── spotter_v2/
    ├── best_model.pt
    └── best_thresholds.json
```

## Input contract

- Feature type: `ResNET_TF2_PCA512`
- Feature rate: 2 FPS
- Feature dimension: 512
- Model weights: `checkpoint["ema"]`

## Fine-grained classes

- `Goal`
- `ShotOnTarget`
- `ShotOffTarget`
- `Corner`
- `DirectFreeKick`
- `Penalty`
- `Card`

## Visible labels

- `Goal`
- `Shot`
- `Corner`
- `DirectFreeKick`
- `Penalty`
- `Card`
