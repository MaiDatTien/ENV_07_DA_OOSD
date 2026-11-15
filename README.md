# ENV_07_DA_OOSD

Đồ án môn Phân tích và thiết kế phần mềm hướng đối tượng, lớp OOSD_CNPM1.

**Đề tài:** Xây dựng hệ thống quản lý nước tưới và lịch canh tác tiết kiệm (ENV-07)

- Sinh viên: Mai Tiến Đạt - 1250080030 - K12_ĐH_CNPM1
- Giảng viên hướng dẫn: Th.S Phạm Trọng Huynh
- Video chạy thử: https://www.youtube.com/watch?v=uzhclfpjxz8&t=58s

## Nội dung repo

| Thư mục | Nội dung |
|---|---|
| `ENV_07/` | Mã nguồn project và tài liệu (sơ đồ, hình ảnh, bảng biểu) |
| `Word_PPT/` | File báo cáo Word và slide thuyết trình |

Hướng dẫn cài đặt và chạy chương trình xem trong [ENV_07/README.md](ENV_07/README.md).

## Giới thiệu ngắn

Hệ thống dùng ESP32 đo độ ẩm đất, nhiệt độ, độ ẩm không khí và điều khiển máy bơm qua relay. Máy chủ dựa vào giai đoạn sinh trưởng của cây và hạn mức nước mỗi ngày để đề xuất lượng nước tưới (tính bằng lít). Người dùng xem số đo, áp dụng hoặc ghi đè đề xuất trên giao diện web. Mọi lần bơm đều được lưu lại.

Công nghệ sử dụng: ESP32 (Arduino), Python FastAPI, ReactJS, SQL Server.
