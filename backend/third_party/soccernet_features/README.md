# SoccerNet feature extractor assets

Thư mục này chứa các tài nguyên SoccerNet được cố định phiên bản để trích xuất đặc trưng đầu vào cho hệ thống:

- `VideoFeatureExtractor.py`
- `pca_512_TF2.pkl`
- `average_512_TF2.pkl`

Feature đầu ra tuân theo cấu hình `ResNET_TF2_PCA512`, 2 FPS và 512 chiều.
Các PCA artifacts được sử dụng nguyên bản, không được huấn luyện hoặc fit lại trong project này.
