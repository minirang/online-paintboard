# online-paintboard

Web Workers 병렬 처리 기반의 프론트엔드와 FastAPI 웹소켓, Supabase 데이터베이스를 연동한 **실시간 공동 그림판 서비스**입니다.

---

## 배포 정보

* **클라이언트 (프론트엔드)**: `https://online-paintboard.onrender.com`
* **백엔드**: `https://online-paintboard-backend.onrender.com`

---

## 핵심 기능 (Features)

* **병렬 렌더링 최적화**: 메인 스레드의 UI 렌더링 부하를 최소화하기 위해 Canvas 픽셀 연산과 웹소켓 패킷 처리를 백그라운드 스레드(`Web Worker` & `OffscreenCanvas`)로 완전히 분리했습니다.
* **주사율 맞춤형 렌더링 (`requestAnimationFrame`)**: 마우스/터치 이벤트를 매 순간 직접 그리지 않고 디스플레이 재생 주기에 맞춰 최신 좌표만 동기화하여 렌더링 및 통신 효율을 높였습니다.
* **실시간 양방향 브로드캐스팅**: `FastAPI WebSocket`을 매개로 접속자 간의 드로잉 데이터를 실시간으로 동기화합니다.
* **클라우드 데이터 보존 및 복원**: `Supabase(PostgreSQL)` 다이렉트 커넥션을 통해 그림 데이터를 저장하며, 새로고침 및 최초 입장 시 기존 데이터를 역대 순서대로 복원합니다.
* **서버 사이드 보안 검증**: 프론트엔드 코드 변조를 통한 트롤링을 방지하기 위해 백엔드 패킷 수신 단계에서 최대 붓 크기(20 이하)를 강제 검증합니다.
* **원격 도화지 초기화 (Admin API)**: `.env` 환경 변수와 연동되는 관리자 전용 POST 엔드포인트(`POST /api/clear`)를 통해 캔버스 데이터를 안전하게 일괄 삭제할 수 있습니다.
* **모바일 렌더링 보정**: 모바일 브라우저 환경에서 시작점과 끝점이 일치할 때 드로잉이 생략되는 버그를 해결하기 위해 점 찍기 시 미세 가짜 길이(`+0.1px`)를 추가했습니다.

---

## 시스템 구조

```text
[ Client (PC / Mobile) ]
   │
   ├───► Main 스레드 (main.ts) : UI 조작, 모드 전환(이동/그리기), 드래그 스크롤, 이벤트 캡처
   │       │
   │       ▼ (postMessage)
   │
   └───► Worker 스레드 (paint.worker.ts) : OffscreenCanvas 연산, 웹소켓 송수신 전담
           ▲
           │ (WebSocket / JSON 패킷)
           ▼
[ Server (FastAPI / Render 배포) ]
   │
   ├───► WebSocket Endpoint : 유저 관리, 패킷 유효성 검증(size <= 20), 데이터 브로드캐스트
   │
   ▼ (Direct Connection Pooler / psycopg2)
   
[ Database (Supabase / PostgreSQL) ] : draw_history 테이블에 좌표 데이터 영구 보존
```

---

## 폴더 구조

```text
online-paintboard/
├── .vscode/
│   └── setting.json
├── backend/
│   └── server/
│       ├── sql/
│       │   └── init.sql
│       ├── venv/
│       ├── .env
│       ├── main.py
│       └── requirements.txt
├── client/
│   ├── node_modules/
│   ├── public/
│   │   └── images/
│   │       └── logo.svg
│   ├── src/
│   │   ├── main.ts
│   │   ├── paint.worker.ts
│   │   ├── style.scss
│   │   └── vite-env.d.ts
│   ├── index.html
│   ├── package-lock.json
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── .editorconfig
├── .gitattributes
├── .gitignore
├── LICENSE
└── README.md
```

---

## 🛠️ 기술 스택

### Frontend
- TypeScript / Vite
- Web Workers API / OffscreenCanvas API
- WebSockets API

### Backend
- Python / FastAPI
- Uvicorn / psycopg2-binary
- python-dotenv / Pydantic

### Infrastructure
- Supabase (PostgreSQL)
- Render (Cloud Hosting)
