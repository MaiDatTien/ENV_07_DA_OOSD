# ENV-07: Quản lý nước tưới và lịch canh tác tiết kiệm

Đồ án môn Phân tích và thiết kế phần mềm hướng đối tượng, Khoa Công nghệ Thông tin, Trường Đại học Tài nguyên và Môi trường TP. Hồ Chí Minh.

Video thực hiện: https://www.youtube.com/watch?v=uzhclfpjxz8&t=58s

Hệ thống gồm thiết bị ESP32 đo độ ẩm đất, nhiệt độ, độ ẩm không khí và điều khiển máy bơm 12V qua relay; máy chủ Python FastAPI; cơ sở dữ liệu SQL Server; giao diện web React. Hệ thống đề xuất lượng nước tưới bằng lít theo giai đoạn sinh trưởng của cây, cho phép ghi đè có lý do, bơm ngoài đề xuất có duyệt và lưu vết mọi lần bơm.

## Cấu trúc thư mục

| Thư mục | Nội dung |
|---|---|
| `arduino/arduino.ino` | Chương trình ESP32 (DHT11 chân D4, cảm biến đất AO chân D34, relay chân D26) |
| `backend/` | Máy chủ FastAPI: `routes`, `services`, `domain`, `repositories`, kiểm thử `tests/` |
| `database/ENV07_DB/ENV07_DB.sql` | Script tạo CSDL ENV07_DB (13 bảng, 3 view, 1 thủ tục), không có dữ liệu mẫu |
| `frontend/` | Giao diện React + Vite |
| `TaiLieu/SoDo/` | Hình các sơ đồ UML, ERD, kiến trúc trong báo cáo |
| `TaiLieu/DrawIO/` | File draw.io của các sơ đồ, cùng tên với file hình |
| `TaiLieu/AnhChup/` | Ảnh chụp giao diện web, phần cứng, Serial Monitor |
| `TaiLieu/BangBieu.md` | Các bảng trong báo cáo |
| `TaiLieu/DanhMucHinh.md` | Danh mục hình theo số hình trong báo cáo |

## Cài đặt và chạy

### 1. Cơ sở dữ liệu
Mở SQL Server Management Studio, chạy `database/ENV07_DB/ENV07_DB.sql`.

### 2. Backend
```
cd backend
copy .env.example .env
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Sửa `backend/.env` cho đúng tài khoản và mật khẩu SQL Server của máy. Tệp `.env` đã nằm trong `.gitignore`, không đưa lên GitHub. Tài liệu API: http://localhost:8000/docs

### 3. Frontend
```
cd frontend
npm install
npm run dev
```
Mở http://localhost:5173. Lần đầu, trang đăng nhập cho tạo tài khoản quản trị.

### 4. ESP32
Mở `arduino/arduino.ino` bằng Arduino IDE, cài thư viện DHT sensor library và ArduinoJson. Thay `ten_wifi_2.4g`, `pass_wifi_2.4G` bằng WiFi 2,4 GHz của bạn và `ipv4_config` bằng địa chỉ IPv4 của máy chạy backend (lệnh `ipconfig`). Chọn board ESP32 Dev Module rồi Upload. Không commit thông tin WiFi thật lên GitHub.

## Vai trò

| Vai trò | Quyền chính |
|---|---|
| Quản trị hệ thống (ADMIN) | Toàn bộ quyền, quản lý tài khoản, đổi ảnh nền |
| Kỹ sư canh tác (MANAGER) | Loại cây, lịch giai đoạn, mùa vụ, ghi đè và duyệt bơm |
| Nông dân vận hành (FARMER) | Tạo, áp dụng đề xuất, gửi yêu cầu bơm, dừng bơm |
| Người xem (VIEWER) | Chỉ xem số đo, đề xuất, nhật ký |
