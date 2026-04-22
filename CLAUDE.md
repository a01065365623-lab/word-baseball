# Word Baseball

야구 메카닉 + 영단어 학습 게임. 실시간 멀티플레이어 대전에서 영단어를 맞추며 타격 결과를 야구 규칙으로 결정한다.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, Flask, Flask-SocketIO, gevent |
| Database | SQLite (`words.db` — 10,000단어, 다국어 컬럼) |
| Frontend | `app/static/index.html` (SPA) |
| Deploy | Railway (`Procfile` + `railway.toml`) |

## Project Structure

```
word-baseball/
├── app.py               ← 메인 Flask 백엔드 (진입점)
├── words.db             ← SQLite DB (vocabulary + users 테이블)
├── requirements.txt
├── Procfile             ← Railway 배포: python app.py
├── railway.toml
├── .gitignore
├── CLAUDE.md
│
├── app/
│   └── static/
│       └── index.html   ← 프론트엔드 SPA
│
└── frontend/            ← Phaser.js 소스 (빌드 → app/static/)
```

## Key Files

### `app.py`
- Flask + Flask-SocketIO (gevent)
- `words.db` 직접 연결 (sqlite3)
- `init_db()`: users 테이블 생성, vocabulary에 ar 컬럼 추가
- `/` → `app/static/index.html` 서빙
- `/get_words?difficulty=1&question_lang=en&answer_lang=ko` → 단어 JSON 반환

### `words.db` — vocabulary 테이블 스키마
| 컬럼 | 설명 |
|------|------|
| `en` | 영어 단어 (질문 기본값) |
| `ko`, `ja`, `zh`, `de`, `fr`, `es`, `hi`, `pt`, `it`, `ru`, `tr`, `vi`, `ar` | 각 언어 번역 |
| `level` | 난이도 1·2·3 |

## API

### `GET /get_words`
```
difficulty   = 1|2|3          (default 1)
question_lang = en|ko|...     (default en)
answer_lang   = ko|en|...     (default ko)
limit        = 1-100          (default 20)
offset       = 0,20,40,...    (default 0)
```
응답: `[{ word, q, a, level }, ...]`

## Development Commands

```bash
# 의존성 설치 후 실행
pip install -r requirements.txt
python app.py

# 포트: 5000 (또는 $PORT 환경변수)
```

## Environment Variables

```
SECRET_KEY=...          # 필수 (production)
FLASK_ENV=development | production
PORT=5000               # Railway에서 자동 주입
```

## Deploy (Railway)

- `Procfile`: `web: python app.py`
- `railway.toml`: NIXPACKS 빌드, ON_FAILURE 재시작
- `words.db`는 git에 포함 (`.gitignore`에서 `!words.db` 허용)

## Game Flow

1. 플레이어가 방 생성/참가
2. 서버가 난이도 · 언어 설정에 따라 `/get_words`로 단어 제공
3. 플레이어가 정답 입력 → 채점 결과에 따라 타격 판정
   - 정답: **홈런** / 근접: **안타** / 오답: **스트라이크/아웃**
4. 9이닝 후 점수 합산 → 승패 결정

## Code Conventions

- Python: PEP 8, 타입 힌트 권장
- 커밋 메시지: `feat:`, `fix:`, `chore:` prefix
