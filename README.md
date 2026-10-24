# Hệ thống Chấm Điểm Rèn Luyện Sinh Viên (Phiên bản Vỏ V1)

> **Cảnh báo dữ liệu minh họa:** Toàn bộ dữ liệu lớp học, tài khoản, tiêu chí và điểm số trong dự án này là **dữ liệu minh họa — không dùng để ra quyết định thật**. Hệ thống hoạt động theo cơ chế kiểm tra thủ công (AI chưa kích hoạt).

Dự án này là nền tảng (Foundation) được xây dựng theo tài liệu đặc tả `DAC_TA_CODE_WEB_VO_V1.md` và kế hoạch phân chia song song `PHAN_CHIA_CODE_SONG_SONG_V1.md`.

---

## 1. Cấu trúc thư mục

```text
├── contracts/               # Hợp đồng API và dữ liệu đã khóa
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
│   ├── alembic/             # Cấu hình và migration đầu tiên 001_initial_schema
│   ├── scripts/seed.py      # Seed script idempotent
│   ├── tests/               # Unit/integration test
│   └── requirements.txt
├── web/                     # Frontend React + TypeScript + Vite
│   ├── src/
│   │   ├── api/types.ts     # TypeScript interfaces từ OpenAPI
│   │   ├── api/client.ts    # Fetch client (CSRF, cookies, errors)
│   │   ├── tokens/          # Design tokens & color mapping
│   │   ├── components/      # AppLayout, StatusBadge, Deadline, ConfirmDialog
│   │   ├── pages/           # Placeholder pages cho 4 vai trò
│   │   └── App.tsx          # Route registry
│   └── package.json
├── handoff/                 # Tài liệu bàn giao và contract issues giữa các gói
├── storage/                 # Thư mục lưu trữ tệp minh chứng local
├── compose.yaml             # Docker Compose chạy PostgreSQL
├── .env.example             # Biến môi trường mẫu
└── README.md
```

---

## 2. Hướng dẫn cài đặt & Khởi động Local

### Bước 1: Khởi động cơ sở dữ liệu PostgreSQL
Khởi động container PostgreSQL qua Docker:
```bash
docker compose up -d db
```

### Bước 2: Cài đặt và chạy Backend (FastAPI)
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

Chạy migration và seed dữ liệu mẫu:
```bash
# Chạy migration
alembic -c api/alembic.ini upgrade head

# Chạy seed dữ liệu (Idempotent - an toàn khi chạy lại nhiều lần)
python -m api.scripts.seed
```

Khởi động Backend server:
```bash
uvicorn api.app.main:app --host 0.0.0.0 --port 8000 --reload
```
Kiểm tra sức khỏe Backend: `GET http://localhost:8000/health` hoặc `GET http://localhost:8000/api/v1/health`

### Bước 3: Cài đặt và chạy Frontend (React / Vite)
```bash
cd web
npm install
npm run dev
```
Truy cập giao diện Web: `http://localhost:5173`

---

## 3. Tài khoản Thử nghiệm (Demo Accounts)

Mật khẩu mặc định cho toàn bộ tài khoản demo (cấu hình qua biến môi trường `DEMO_PASSWORD`): **`Demo@123456`**

| Vai trò | Tên đăng nhập | Họ và tên | Chức năng chính |
|---|---|---|---|
| **STUDENT** | `sv001` | Nguyễn Văn An | Tự chấm, tải minh chứng, nộp hồ sơ, khiếu nại |
| **STUDENT** | `sv002` | Trần Thị Bình | Sinh viên cùng lớp LOP-DEMO |
| **STUDENT** | `sv003` | Lê Văn Cường | Sinh viên cùng lớp LOP-DEMO |
| **BCS** | `bcs001` | Phạm Thị Dung | Hàng chờ 3 vùng, duyệt điểm, biên bản họp, công bố điểm |
| **GVCN** | `gvcn001` | ThS. Hoàng Văn Em | Xem và xuất bảng điểm chính thức CSV |
| **ADMIN** | `admin001` | Quản trị viên Hệ thống | Cấu hình đợt đánh giá, hạn nộp, tiêu chí |

---

## 4. Lệnh Deadline Tick

Lệnh xử lý hạn tự động có thể chạy thủ công hoặc lập lịch định kỳ:
```bash
# Sử dụng thời gian hiện tại
python -m api.app.jobs.tick

# Giả lập thời gian cụ thể (ISO8601 UTC)
python -m api.app.jobs.tick --now 2026-10-25T01:00:00Z
```

---

## 5. Quy tắc dành cho Giai đoạn 1 (Gói A, B, C, D)

1. Mọi gói bắt đầu từ commit nền: `foundation-v1`.
2. **Không sửa đổi** các file hợp đồng đã khóa: `contracts/*`, `web/src/api/types.ts`, `web/src/api/client.ts`.
3. Nếu phát hiện thiếu sót hoặc sai lệch, ghi nhận vào `handoff/<goi>-contract-issues.md` để giải quyết tại Giai đoạn 2.
4. Tuân thủ phạm vi phân quyền và vùng thư mục đã quy định tại `PHAN_CHIA_CODE_SONG_SONG_V1.md`.
