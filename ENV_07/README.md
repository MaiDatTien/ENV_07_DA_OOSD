# ENV-07 - Quản lý nước tưới và lịch canh tác tiết kiệm

## Giới thiệu

Project gồm 4 phần:

- **arduino**: chương trình cho ESP32, đọc cảm biến DHT11 và cảm biến độ ẩm đất, gửi số đo lên máy chủ, nhận lệnh bật tắt bơm.
- **backend**: máy chủ viết bằng Python FastAPI, xử lý nghiệp vụ, phân quyền và cung cấp API.
- **frontend**: giao diện web viết bằng ReactJS (Vite).
- **database**: script tạo cơ sở dữ liệu SQL Server `ENV07_DB`.

Hệ thống có 4 vai trò: Quản trị, Kỹ sư canh tác, Nông dân vận hành, Người xem.

Chức năng chính:

- Theo dõi độ ẩm đất, nhiệt độ, độ ẩm không khí theo thời gian thực
- Quản lý loại cây, lịch giai đoạn và mùa vụ
- Tạo đề xuất tưới từ số đo, áp dụng để bơm, ghi đè hoặc từ chối (phải có lý do)
- Gửi yêu cầu bơm tay (tối đa 2 lít, phải được duyệt)
- Tưới tự động khi đất khô
- Xem nhật ký bơm, quản lý tài khoản

## Cấu trúc thư mục

```
ENV_07/
├── arduino/arduino.ino
├── backend/
│   ├── app/              mã nguồn backend
│   ├── tests/            kiểm thử
│   ├── .env.example      file cấu hình mẫu
│   └── requirements.txt
├── database/ENV07_DB/ENV07_DB.sql
├── frontend/             mã nguồn giao diện
└── docs/
    ├── hinh_ve/          hình các sơ đồ (use case, lớp, tuần tự, hoạt động, ERD...)
    ├── so_do_drawio/     file draw.io của các sơ đồ
    ├── anh_chup/         ảnh chụp giao diện và phần cứng
    ├── bang_bieu.md      các bảng trong báo cáo
    └── danh_muc_hinh.md  danh sách hình theo số hình trong báo cáo
```

## Phần cứng

| Linh kiện | Nối vào ESP32 |
|---|---|
| DHT11 | chân DATA nối D4 |
| Cảm biến độ ẩm đất LM393 | chân AO nối D34 |
| Relay 5V | chân IN nối D26, VCC nối VIN |
| Máy bơm 12V | nối qua COM và NO của relay, dùng nguồn 12V riêng |

Máy bơm chạy 60 giây được khoảng 2 lít nước.

## Cài đặt và chạy

Cần cài: SQL Server, ODBC Driver 17 for SQL Server, Python 3.11 trở lên, Node.js 18 trở lên, Arduino IDE.

**1. Tạo cơ sở dữ liệu**

Mở SQL Server Management Studio, chạy file `database/ENV07_DB/ENV07_DB.sql`.

**2. Chạy backend**

```
cd backend
copy .env.example .env
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Sau đó mở file `backend/.env` và điền tài khoản, mật khẩu SQL Server của máy mình.

**3. Chạy frontend**

```
cd frontend
npm install
npm run dev
```

Mở trình duyệt vào http://localhost:5173. Lần đầu vào sẽ tạo tài khoản quản trị.

**4. Nạp chương trình ESP32**

- Mở `arduino/arduino.ino` bằng Arduino IDE
- Cài thư viện DHT sensor library và ArduinoJson
- Sửa tên WiFi, mật khẩu WiFi và địa chỉ IP của máy chạy backend
- Chọn board ESP32 Dev Module rồi bấm Upload

## Kiểm thử

```
cd backend
pytest
```

## Lưu ý

- File `backend/.env` chứa mật khẩu nên không đưa lên GitHub (đã có trong `.gitignore`).
- Thông tin WiFi trong `arduino.ino` chỉ để chuỗi mẫu, khi chạy thì tự sửa lại.
