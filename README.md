# ENV_07_DA_OOSD

Đồ án môn Phân tích và thiết kế phần mềm hướng đối tượng
Khoa Công nghệ Thông tin, Trường Đại học Tài nguyên và Môi trường TP. Hồ Chí Minh

**Đề tài:** Xây dựng hệ thống quản lý nước tưới và lịch canh tác tiết kiệm (ENV-07)

| | |
|---|---|
| Sinh viên | Mai Tiến Đạt |
| MSSV | 1250080030 |
| Lớp | K12_ĐH_CNPM1 |
| Giảng viên hướng dẫn | Th.S Phạm Trọng Huynh |

Video chạy thử: https://www.youtube.com/watch?v=uzhclfpjxz8&t=58s

## Nội dung repo

| Thư mục | Nội dung |
|---|---|
| [`ENV_07/`](ENV_07) | Mã nguồn (ESP32, backend FastAPI, frontend React, script SQL Server), sơ đồ UML, file draw.io, ảnh chụp, bảng biểu |
| [`Word_PPT/`](Word_PPT) | Báo cáo Word và slide thuyết trình |

Hướng dẫn cài đặt và chạy nằm trong [`ENV_07/README.md`](ENV_07/README.md).

## Tóm tắt hệ thống

ESP32 đo độ ẩm đất, nhiệt độ, độ ẩm không khí rồi gửi lên máy chủ. Máy chủ dựa vào lịch giai đoạn của cây và hạn mức nước để đề xuất lượng nước tưới bằng lít. Kỹ sư có thể ghi đè hoặc từ chối đề xuất nhưng phải ghi lý do. Nông dân muốn bơm ngoài đề xuất thì phải gửi yêu cầu và được duyệt, tối đa 2 lít mỗi lần. Mọi lần bơm đều lưu lại ai ra lệnh, ai duyệt và bơm thật bao nhiêu giây.

Công nghệ: ESP32 (Arduino), Python FastAPI, React + Vite, Microsoft SQL Server, draw.io.
