# Hệ thống Chấm Điểm Rèn Luyện Sinh Viên (Phiên bản V1 Tích hợp Hoàn chỉnh)

> **Cảnh báo dữ liệu minh họa:** Toàn bộ dữ liệu lớp học, tài khoản, tiêu chí và điểm số trong dự án này là **dữ liệu minh họa — không dùng để ra quyết định thật**. Hệ thống hoạt động theo cơ chế kiểm tra thủ công (AI chưa kích hoạt).

Dự án này là hệ thống Web Chấm Điểm Rèn Luyện Sinh Viên V1 hoàn chỉnh đã tích hợp Frontend React với Backend FastAPI và cơ sở dữ liệu PostgreSQL thật, được phát triển theo tài liệu đặc tả `DAC_TA_CODE_WEB_VO_V1.md` và hướng dẫn tích hợp `output/PROMPT_SUA_TICH_HOP_GIAI_DOAN_2_5.md`.

---

## 1. Cấu trúc thư mục

```text
├── contracts/               # Hợp đồng API và dữ liệu
│   ├── openapi.yaml         # Hợp đồng OpenAPI 3.0.3 đầy đủ mọi endpoint
│   ├── states.md            # Máy trạng thái Campaign & Case
│   └── seed-fixtures.json   # Dữ liệu seed và fixtures mẫu UI
├── api/                     # Backend FastAPI
│   ├── app/
│   │   ├── main.py          # Entrypoint FastAPI, CORS, error handling
│   │   ├── config.py        # Cấu hình môi trường
│   │   ├── database.py      # SQLAlchemy engine & session
│   │   ├── models/          # ORM models (15 bảng Mục 5)
│   │   ├── routes/          # Routers (health, auth, student, bcs, admin, gvcn, files, notifications)
│   │   ├── review/          # ReviewProvider & ManualReviewProvider
│   │   └── jobs/tick.py     # Lệnh xử lý hạn deadline tick
│   ├── alembic/             # Cấu hình và migration database
│   ├── scripts/             # Seed database, demo e2e, verify live flow
│   ├── tests/               # Backend tests (auth, rbac, workflow, health)
│   └── requirements.txt
├── web/                     # Frontend React + TypeScript + Vite
│   ├── src/
│   │   ├── api/types.ts     # TypeScript interfaces từ OpenAPI
│   │   ├── api/client.ts    # Fetch client (CSRF token in-memory, HttpOnly cookies, auto-logout 401)
│   │   ├── context/         # AuthContext quản lý session thực & restore phiên qua /auth/me
│   │   ├── components/      # ProtectedRoute, AppLayout, StatusBadge, Deadline, ConfirmDialog
│   │   ├── pages/           # Màn hình thật cho 4 vai trò (Student, BCS, GVCN, Admin)
│   │   └── App.tsx          # Route registry & RBAC ProtectedRoute
│   └── package.json
├── tests/                   # Kiểm thử hợp đồng & 16 kịch bản chấp nhận Section 9
│   ├── contract/            # Kiểm thử hợp đồng (OpenAPI, Fixtures, States)
│   ├── e2e/                 # 16 kịch bản chấp nhận (Acceptance Tests Mục 9)
│   └── run_tests.py         # Test runner tổng hợp
├── storage/                 # Thư mục lưu trữ tệp minh chứng local
├── compose.yaml             # Docker Compose chạy PostgreSQL
├── .env.example             # Biến môi trường mẫu
└── README.md
```

---

## 2. Hướng dẫn Cài đặt & Khởi động Hệ thống

### Chế độ hoạt động (Live Mode vs Demo Mock Mode)
- **Live Mode (Mặc định):** Frontend gọi trực tiếp Backend FastAPI và cơ sở dữ liệu PostgreSQL qua HttpOnly cookie session và CSRF token. Nếu backend mất kết nối hoặc API trả về lỗi, hệ thống hiển thị thông báo lỗi rõ ràng và nút "Thử lại", **tuyệt đối không âm thầm fallback sang mock**. Dropdown chuyển vai trò bị ẩn hoàn toàn để đảm bảo tính phân quyền thực tế.
- **Demo Mode (Tùy chọn):** Khi cần trình diễn ngoại tuyến không cần backend, khởi động frontend với biến môi trường `VITE_DEMO_MODE=true`. Lúc này giao diện sẽ kích hoạt thanh chuyển kịch bản giả lập và gắn nhãn `[DEMO MOCK]`.

---

### Bước 1: Khởi động cơ sở dữ liệu PostgreSQL
Khởi động container PostgreSQL qua Docker:
```bash
docker compose up -d db
```

### Bước 2: Cài đặt và Khởi động Backend (FastAPI)
Tạo môi trường ảo Python và cài đặt thư viện:
```bash
python -m venv .venv
# Trên Windows:
.venv\Scripts\activate
# Trên Linux/macOS:
source .venv/bin/activate

pip install -r api/requirements.txt
```

Sao chép cấu hình môi trường:
```bash
cp .env.example .env
```

Thiết lập mật khẩu demo qua biến môi trường (khuyến nghị đổi mật khẩu an toàn khi triển khai):
```bash
# Trên Windows PowerShell:
$env:DEMO_PASSWORD="YourPasswordHere"
# Trên Linux/macOS:
export DEMO_PASSWORD="YourPasswordHere"
```

Chạy migration và seed dữ liệu mẫu:
```bash
# Chạy migration database
alembic -c api/alembic.ini upgrade head

# Chạy seed dữ liệu (Idempotent - an toàn khi chạy lại nhiều lần)
python -m api.scripts.seed
```

Khởi động Backend server:
```bash
uvicorn api.app.main:app --host 0.0.0.0 --port 8000 --reload
```
Kiểm tra sức khỏe Backend: `GET http://localhost:8000/api/v1/health`

### Bước 3: Cài đặt và Khởi động Frontend (React / Vite)
```bash
cd web
npm install

# Khởi động ở chế độ Live kết nối Backend thực (Mặc định):
npm run dev

# (Tùy chọn) Khởi động ở chế độ Demo Mock độc lập:
# $env:VITE_DEMO_MODE="true"; npm run dev
```
Truy cập giao diện Web: `http://localhost:5173`

---

## 3. Danh sách Tài khoản Khởi tạo

Mật khẩu khởi tạo cho toàn bộ tài khoản được thiết lập thông qua biến môi trường `DEMO_PASSWORD` khi chạy lệnh seed (mặc định trong tệp môi trường mẫu: `Demo@123456`). Khi đăng nhập trên giao diện web, người dùng phải nhập đúng mật khẩu này.

| Vai trò | Tên đăng nhập | Họ và tên | Chức năng chính |
|---|---|---|---|
| **STUDENT** | `sv001` | Nguyễn Văn An | Tự chấm, tải minh chứng file thực, nộp hồ sơ, khiếu nại |
| **STUDENT** | `sv002` | Trần Thị Bình | Sinh viên cùng lớp LOP-DEMO |
| **STUDENT** | `sv003` | Lê Văn Cường | Sinh viên cùng lớp LOP-DEMO |
| **BCS** | `bcs001` | Phạm Thị Dung (Lớp trưởng) | Hàng chờ 3 vùng, duyệt điểm, biên bản họp, công bố điểm |
| **GVCN** | `gvcn001` | ThS. Hoàng Văn Em (GVCN) | Xem và xuất bảng điểm chính thức CSV |
| **ADMIN** | `admin001` | Quản trị viên Hệ thống | Cấu hình đợt đánh giá, hạn nộp, tiêu chí |

---

## 4. Lệnh Deadline Tick

Lệnh xử lý hạn tự động có thể chạy thủ công hoặc lập lịch định kỳ qua cron:
```bash
# Sử dụng thời gian hiện tại
python -m api.app.jobs.tick

# Giả lập thời gian cụ thể (ISO8601 UTC)
python -m api.app.jobs.tick --now 2026-10-25T01:00:00Z
```

---

## 5. Hướng dẫn Chạy Kiểm thử & Xác minh

### 1. Kiểm thử Toàn bộ Hợp đồng & 16 Kịch bản Chấp nhận (Section 9):
```bash
# Chạy tất cả kiểm thử hợp đồng và e2e
python tests/run_tests.py --mode all

# Hoặc chạy kiểm thử hợp đồng riêng
python -m pytest tests/contract

# Chạy 16 kịch bản chấp nhận riêng
$env:RUN_ACCEPTANCE_TESTS="1"; python -m pytest tests/e2e
```

### 2. Kiểm thử Đơn vị Backend:
```bash
python -m pytest api/tests
```

### 3. Kiểm thử Frontend (Unit, Mock Logic & Live Integration/Route Guard):
```bash
npm run test --prefix web
```

### 4. Build Kiểm tra Kiểu TypeScript & Bundle Frontend:
```bash
npm run build --prefix web
```

### 5. Chạy Script Kiểm chứng Tích hợp Luồng Thực (Live Flow Verification):
```bash
python api/scripts/verify_live_flow.py
```
Script này tự động kiểm tra toàn bộ chu trình 10 bước qua API và cơ sở dữ liệu thực: Đăng nhập sai pass bị 401 -> Đăng nhập đúng giữ cookie/CSRF -> sv001 vào /bcs bị 403 -> sv001 tự chấm/upload/nộp -> BCS duyệt điểm -> BCS ghi họp/công bố -> sv001 khiếu nại -> BCS giải quyết/chốt -> GVCN tải CSV -> Đăng xuất chặn route.
