<div align="center">

# ENV-07 · Quản lý nước tưới và lịch canh tác tiết kiệm

**Hệ thống IoT tưới cây theo giai đoạn sinh trưởng, tính lượng nước bằng lít và lưu vết mọi lần bơm**

[▶ Video chạy thử](https://www.youtube.com/watch?v=uzhclfpjxz8&t=58s) ·
[Mã nguồn](ENV_07) ·
[Sơ đồ và tài liệu](ENV_07/docs) ·
[Báo cáo và slide](Word_PPT) ·
[Hướng dẫn cài đặt](ENV_07/README.md)

</div>

---

## Thông tin đồ án

| | |
|---|---|
| **Môn học** | Phân tích và thiết kế phần mềm hướng đối tượng (OOSD) |
| **Lớp** | OOSD_CNPM1 · K12_ĐH_CNPM1 |
| **Đơn vị** | Khoa Công nghệ Thông tin, Trường Đại học Tài nguyên và Môi trường TP. Hồ Chí Minh |
| **Sinh viên** | Mai Tiến Đạt · MSSV 1250080030 |
| **Giảng viên hướng dẫn** | Th.S Phạm Trọng Huynh |
| **Repository** | https://github.com/MaiDatTien/ENV_07_DA_OOSD |

## Bài toán

Ở hộ gia đình, cây thường được tưới theo thói quen: sáng một lần, chiều một lần, tưới đến khi thấy đất ướt. Lượng nước không theo nhu cầu của cây ở từng giai đoạn, và không ai biết mỗi ngày đã dùng bao nhiêu nước.

ENV-07 gồm một thiết bị ESP32 đặt tại chậu cây và một ứng dụng web:

- **Đo thật:** độ ẩm đất, nhiệt độ và độ ẩm không khí được gửi lên mỗi 10 giây.
- **Đề xuất bằng lít:** lượng nước được tính từ giai đoạn sinh trưởng, hạn mức ngày và thời tiết tại chỗ, kèm phạm vi áp dụng rõ ràng.
- **Có người chịu trách nhiệm:** ghi đè đề xuất phải có lý do, bơm ngoài đề xuất phải được duyệt, mọi lần bơm đều lưu người ra lệnh và số giây bơm thật.

<p align="center">
  <img src="ENV_07/docs/anh_chup/theodoi.png" width="88%" alt="Trang Theo dõi">
</p>

## Cấu trúc repository

```
ENV_07_DA_OOSD/
├── ENV_07/                 Project
│   ├── arduino/            Chương trình ESP32
│   ├── backend/            Máy chủ FastAPI, kiểm thử, tệp cấu hình mẫu
│   ├── database/           Script tạo CSDL SQL Server
│   ├── frontend/           Giao diện React + Vite
│   ├── docs/               Sơ đồ UML, ERD, draw.io, ảnh chụp, bảng biểu
│   └── README.md           Tài liệu kỹ thuật và hướng dẫn cài đặt
└── Word_PPT/               Báo cáo cuối kỳ (.docx) và slide (.pptx)
```

## Đối chiếu yêu cầu nộp bài

| Yêu cầu | Vị trí trong repository |
|---|---|
| Toàn bộ mã nguồn | [`ENV_07/arduino`](ENV_07/arduino), [`ENV_07/backend`](ENV_07/backend), [`ENV_07/frontend`](ENV_07/frontend), [`ENV_07/database`](ENV_07/database) |
| Tệp cấu hình | [`backend/.env.example`](ENV_07/backend/.env.example), [`backend/requirements.txt`](ENV_07/backend/requirements.txt), [`frontend/package.json`](ENV_07/frontend/package.json), [`frontend/vite.config.js`](ENV_07/frontend/vite.config.js) |
| Sơ đồ (UML, ERD, kiến trúc) | [`ENV_07/docs/hinh_ve`](ENV_07/docs/hinh_ve) (PNG) và [`ENV_07/docs/so_do_drawio`](ENV_07/docs/so_do_drawio) (tệp gốc) |
| Hình ảnh minh họa | [`ENV_07/docs/anh_chup`](ENV_07/docs/anh_chup) |
| Bảng biểu | [`ENV_07/docs/bang_bieu.md`](ENV_07/docs/bang_bieu.md), đánh số giống báo cáo Word |
| Đối chiếu hình với báo cáo | [`ENV_07/docs/danh_muc_hinh.md`](ENV_07/docs/danh_muc_hinh.md) |
| README giới thiệu và hướng dẫn chạy | [`ENV_07/README.md`](ENV_07/README.md) |
| Không lộ thông tin bí mật | Mật khẩu CSDL đọc từ `backend/.env` (đã loại khỏi Git); WiFi trong `arduino.ino` để chuỗi mẫu |

## Bắt đầu nhanh

```bash
git clone https://github.com/MaiDatTien/ENV_07_DA_OOSD.git
cd ENV_07_DA_OOSD/ENV_07
```

Tiếp tục theo [ENV_07/README.md](ENV_07/README.md#cài-đặt): tạo CSDL, chạy backend, chạy frontend, nạp chương trình ESP32.

## Tác giả

**Mai Tiến Đạt** · [@MaiDatTien](https://github.com/MaiDatTien)
