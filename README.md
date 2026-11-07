# Hệ thống chấm điểm rèn luyện sinh viên

Ứng dụng hỗ trợ sinh viên tự chấm và nộp minh chứng, BCS xử lý hồ sơ và công bố điểm, GVCN nhận bảng điểm chính thức. Bản chạy local dùng React/Vite, FastAPI và PostgreSQL. Tài khoản, tiêu chí và hồ sơ mẫu chỉ dùng để minh họa.

## 1. Chuẩn bị

Cài Git, Python 3.11, Node.js 24 kèm npm và Docker có Compose v2 trở lên. Mở Docker trước khi chạy lệnh. Các cổng mặc định là `5432` (PostgreSQL), `8000` (API) và `5173` (web).

```sh
git clone --branch master https://github.com/Hermnnz/AI-DiemRenLuyen.git
cd AI-DiemRenLuyen
```

## 2. Khởi động PostgreSQL và API

Chạy ở thư mục gốc của bản clone. Các lệnh dưới đây tạo cấu hình cho lần cài đầu tiên. Nếu đã có `.env`, giữ lại cấu hình của bạn.

### Windows PowerShell — Terminal 1

```powershell
Copy-Item .env.example .env
docker compose up -d --wait db
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r api/requirements.txt
.\.venv\Scripts\python.exe -m alembic -c api/alembic.ini upgrade head
$env:DEMO_PASSWORD = "Demo@123456"
.\.venv\Scripts\python.exe -m api.scripts.seed
.\.venv\Scripts\python.exe -m uvicorn api.app.main:app --host 127.0.0.1 --port 8000
```

### macOS/Linux — Terminal 1

```bash
cp .env.example .env
docker compose up -d --wait db
python3 -m venv .venv
.venv/bin/python -m pip install -r api/requirements.txt
.venv/bin/python -m alembic -c api/alembic.ini upgrade head
DEMO_PASSWORD='Demo@123456' .venv/bin/python -m api.scripts.seed
.venv/bin/python -m uvicorn api.app.main:app --host 127.0.0.1 --port 8000
```

Giữ Terminal 1 mở. Kiểm tra [API health](http://localhost:8000/api/v1/health). Nếu migration hoặc seed báo lỗi, kiểm tra `docker compose ps` và `docker compose logs db` trước khi chạy tiếp.

Nếu máy đã có PostgreSQL ở cổng `5432`, đổi `POSTGRES_PORT` và cổng trong `DATABASE_URL` của `.env` sang cùng một cổng trống, ví dụ `55436`. Khi chạy song song nhiều bản clone, dùng một tên dự án Compose riêng, ví dụ `docker compose -p drl-local-check up -d --wait db`. Giải phóng cổng `8000` và `5173` trước khi khởi động API và web.

## 3. Khởi động web

Mở **Terminal 2** ở thư mục gốc của bản clone và giữ cả hai terminal chạy.

```sh
npm ci --prefix web
npm run dev --prefix web -- --strictPort
```

Nếu PowerShell chặn `npm.ps1`, dùng `npm.cmd` thay cho `npm` trong hai lệnh. Truy cập [trang đăng nhập](http://localhost:5173/login). Vite chuyển tiếp `/api` tới API local ở cổng `8000`.

## 4. Đăng nhập và thử quy trình

| Vai trò | Tài khoản mẫu |
| --- | --- |
| Quản trị viên | `admin001` |
| Ban cán sự | `bcs001` |
| Sinh viên | `sv001`, `sv002`, `sv003`, `sv004` |
| Giáo viên chủ nhiệm | `gvcn001` |

Trên cơ sở dữ liệu mới, các tài khoản dùng mật khẩu đã đặt ở bước seed. Với lệnh trên, mật khẩu là `Demo@123456`. Seed có thể chạy lại và giữ mật khẩu của các tài khoản đã tồn tại.

1. Đăng nhập bằng `admin001`. Đợt mẫu được tạo ở trạng thái nháp. Vào quản lý đợt, sửa hạn nộp sang tương lai nếu ngày mẫu đã qua, rồi mở đợt.
2. Đăng xuất và đăng nhập bằng `sv001`. Mở màn hình tự chấm để kiểm tra đã thấy đợt mở và danh sách tiêu chí.
3. Dùng `bcs001` để xem hàng chờ duyệt. Dùng `gvcn001` để xem bảng điểm sau khi lớp chốt điểm và bàn giao.

### AI và cấu hình trình diễn

- Mã nguồn có hai bước AI để đọc minh chứng và đối chiếu với tiêu chí. BCS vẫn chịu trách nhiệm duyệt điểm và xử lý hồ sơ ngoại lệ.
- Cấu hình local mặc định lưu tệp trong `storage/` và tắt hai bước Gemini (`AI_READ_ENABLED=false`, `AI_TRANSPARENCY_ENABLED=false`). Với cấu hình này có thể chạy quy trình duyệt thủ công bằng tài khoản mẫu.
- Khi bật cả hai bước AI, cấp `GEMINI_API_KEY` và bật `AI_AUTO_ACCEPT_ENABLED`, ngưỡng mặc định là `AI_AUTO_ACCEPT_THRESHOLD=0.70`. Bản trình diễn kiểm tra cả điểm đối chiếu và điểm tự rà soát từ 70%, cùng các điều kiện về minh chứng. Xem [các biến cấu hình](.env.example).
- Lượt Playwright tổng hợp ngày 04/11/2026 dùng PostgreSQL riêng và AI mô phỏng. Một lượt thử Gemini thật riêng đã kiểm tra đường đọc, đối chiếu và BCS bác kết luận trên một minh chứng. Kết quả này mô tả tích hợp đã thử nghiệm.

## 5. Kiểm thử và dừng hệ thống

Chạy từ thư mục gốc. Dùng `.venv/bin/python` thay cho đường dẫn Python bên dưới nếu dùng macOS/Linux.

```powershell
.\.venv\Scripts\python.exe -m pytest api/tests
npm run test --prefix web
npm run build --prefix web
```

Để dừng web và API, nhấn Ctrl+C ở từng terminal, rồi chạy `docker compose down` để dừng PostgreSQL. Nếu đã dùng `-p`, dùng lại cùng tên dự án.

Thư mục `docs/`, `tests/` tại gốc dự án và các tài liệu đặc tả, phân chia công việc, BPMN được giữ riêng ở local và được loại trừ bằng `.gitignore`.

| Thư mục | Nội dung |
| --- | --- |
| `api/` | FastAPI, migration Alembic và script seed |
| `web/` | Giao diện React và cấu hình Vite |
| `contracts/` | Hợp đồng API, trạng thái và dữ liệu mẫu |

