# PRD: 위치 기반 맛집 추천 AI 에이전트 (텔레그램 챗봇)

**문서 버전:** v1.2  
**작성일:** 2026-06-16  
**상태:** 초안  
**채널:** Telegram Bot  
**실행 환경:** 로컬 (Polling 방식)

---

## 1. 개요

### 1.1 제품 목적

텔레그램 챗봇으로 자연어 대화를 통해 맛집을 추천받는 개인용 AI 에이전트.  
**위치 공유** 또는 **텍스트 지역 입력** 두 가지 방식 모두 지원하며, Google · Kakao · 네이버 데이터를 통합해 Gemini API로 개인화 추천을 제공한다.

### 1.2 사용 시나리오

**시나리오 A — 위치 공유 방식**
```
나: 📍 [현재 위치 전송]
나: 혼밥하기 좋은 조용한 일식집 추천해줘

봇: 📍 현재 위치 기준 추천 결과예요!

    🥇 멘야 사쿠라 (350m)
    ⭐ 4.6 · 🟢 영업중 · 1인석 多
    "조용하고 아늑한 분위기의 라멘 전문점. 혼밥 손님이 많아 편안해요."
    🗺 카카오맵 | 구글맵
    ...
```

**시나리오 B — 텍스트 지역 입력 방식**
```
나: 강남역 근처 파스타 맛집 알려줘
나: 홍대 데이트하기 좋은 분위기 좋은 이탈리안

봇: 📍 강남역 기준 추천 결과예요!
    ...
```

---

## 2. 검색 입력 방식

### 2.1 두 가지 입력 모드 비교

| 구분 | 위치 공유 방식 | 텍스트 입력 방식 |
|---|---|---|
| 입력 | 텔레그램 위치 메시지 + 검색어 | 자연어 텍스트만 |
| 정확도 | GPS 좌표 → 정밀 반경 검색 | 지역명 → Kakao Geocoding 변환 |
| 편의성 | 위치 전송 동작 필요 | 텍스트만으로 완결 |
| 예시 | `📍위치` + "근처 고기집" | "강남역 근처 고기집" |

### 2.2 Gemini 입력 파싱 전략

두 방식 모두 Gemini가 동일하게 처리. 텍스트에서 지역명이 감지되면 `location_text` 슬롯을 채우고, 위치 메시지가 있으면 `coordinates` 우선 사용.

```
입력: "홍대 데이트하기 좋은 분위기 이탈리안"
→ location_text: "홍대"
→ cuisine_type: ["이탈리안"]
→ atmosphere: ["데이트", "분위기 좋은"]

입력: 📍(위도 37.55, 경도 126.92) + "파스타"
→ coordinates: (37.55, 126.92)  ← 우선 사용
→ cuisine_type: ["파스타", "이탈리안"]
```

### 2.3 위치 결정 우선순위

```
1순위: 텔레그램 위치 메시지 (GPS 좌표)
2순위: 텍스트에서 추출한 지역명 → Kakao Geocoding API로 좌표 변환
3순위: 이전 대화에서 사용한 위치 (세션 내 캐시)
4순위: 위치 정보 없음 → 위치 요청 안내
```

### 2.4 대화 흐름 상태도

```
[START]
    │
    ▼
메시지 수신
    │
    ├─ 위치 메시지 포함? ──YES──→ coordinates 저장
    │                               │
    │                               ▼
    └─ 텍스트에 지역명? ──YES──→ Geocoding → coordinates
                │
                NO
                │
                ▼
        세션 캐시에 이전 위치?
                │
          YES ──┘── NO
          │          │
          ▼          ▼
        재사용    위치 요청 메시지
                  + 버튼 제공

    coordinates 확정
          │
          ▼
    Gemini 의도 분석
          │
          ▼
    API 병렬 호출
          │
          ▼
    추천 결과 전송
```

---

## 3. 시스템 아키텍처 (로컬 실행)

```
┌──────────────────────────────────────────────────────┐
│                   Telegram App (사용자)               │
└───────────────────────┬──────────────────────────────┘
                        │ Long Polling (HTTPS 불필요)
                        ▼
┌──────────────────────────────────────────────────────┐
│           로컬 Python 프로세스 (터미널 실행)           │
│                                                      │
│  python main.py                                      │
│                                                      │
│  ┌─────────────────────────────────────────────┐    │
│  │           MessageRouter                      │    │
│  │  Location 메시지 ──┐                         │    │
│  │  텍스트 메시지 ────┼→ IntentParser           │    │
│  │  커맨드 ──────────┘   (Gemini Function Call) │    │
│  └──────────────────────────┬──────────────────┘    │
│                             │                        │
│              ┌──────────────┼──────────────┐         │
│              ▼              ▼              ▼         │
│         Google           Kakao           Naver       │
│         Places           Local          Search       │
│         Client           Client         Client       │
│              │              │              │         │
│              └──────────────┴──────────────┘         │
│                             │                        │
│                    ResultAggregator                  │
│                   (중복 제거 + 정규화)                │
│                             │                        │
│                    RankingEngine                     │
│                    (Gemini 랭킹 + 추천이유)           │
│                             │                        │
│                    MessageFormatter                  │
│                    (텔레그램 메시지 조립)             │
│  ┌──────────────────────────────────────────────┐   │
│  │  SessionStore (dict)                         │   │
│  │  { chat_id: { last_coords, last_intent } }   │   │
│  └──────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
```

### 3.1 로컬 실행의 특징

| 항목 | 내용 |
|---|---|
| 실행 방식 | **Long Polling** (Webhook 불필요, HTTPS 서버 불필요) |
| 시작 명령 | `python main.py` |
| 종료 | `Ctrl+C` |
| 네트워크 | 인터넷 연결만 있으면 동작 |
| 상태 저장 | 프로세스 메모리 (재시작 시 세션 초기화) |

---

## 4. 프로젝트 구조

```
agent_good_place/
├── main.py                  # 진입점, 봇 실행
├── .env                     # API 키 모음
├── requirements.txt
│
├── bot/
│   ├── handlers.py          # 텔레그램 핸들러 (텍스트, 위치, 커맨드)
│   ├── formatter.py         # 추천 결과 → 텔레그램 메시지 변환
│   └── session.py           # 세션 상태 관리 (chat_id별 위치 캐시)
│
├── agent/
│   ├── intent_parser.py     # Gemini Function Calling → intent_slots
│   ├── ranker.py            # Gemini 랭킹 + 추천이유 생성
│   └── orchestrator.py      # 전체 흐름 조율
│
└── search/
    ├── google_places.py     # Google Places API 클라이언트
    ├── kakao_local.py       # Kakao 로컬 API 클라이언트 (검색 + Geocoding)
    ├── naver_local.py       # 네이버 지역 검색 API 클라이언트
    └── aggregator.py        # 결과 통합 + 중복 제거
```

---

## 5. API 명세

### 5.1 Telegram Bot API (Long Polling)

```python
# main.py 핵심 구조
from telegram.ext import Application, MessageHandler, filters

app = Application.builder().token(TELEGRAM_TOKEN).build()
app.add_handler(MessageHandler(filters.LOCATION, handle_location))
app.add_handler(MessageHandler(filters.TEXT, handle_text))
app.run_polling()  # Webhook 없이 로컬에서 바로 실행
```

### 5.2 Google Places API

| 항목 | 내용 |
|---|---|
| Endpoint | `https://places.googleapis.com/v1/places:searchNearby` |
| 파라미터 | `locationRestriction.circle` (위도/경도/반경), `includedTypes` |
| 응답 필드 | `rating`, `userRatingCount`, `currentOpeningHours`, `priceLevel` |

### 5.3 Kakao 로컬 API

| 항목 | 내용 |
|---|---|
| 검색 Endpoint | `https://dapi.kakao.com/v2/local/search/keyword.json` |
| Geocoding Endpoint | `https://dapi.kakao.com/v2/local/search/address.json` |
| 파라미터 | `query`, `x`(경도), `y`(위도), `radius`, `category_group_code=FD6` |
| 인증 | `Authorization: KakaoAK {REST_API_KEY}` |

### 5.4 네이버 지역 검색 API

| 항목 | 내용 |
|---|---|
| Endpoint | `https://openapi.naver.com/v1/search/local.json` |
| 파라미터 | `query` (지역명 + 음식종류), `display=5`, `sort=comment` |
| 제한 | 좌표 필터링 미지원 → 반환된 주소를 Kakao Geocoding으로 변환 후 거리 계산 |

### 5.5 Gemini API

| 항목 | 내용 |
|---|---|
| 모델 | `gemini-2.0-flash` |
| 용도 1 | 의도 분석 (Function Calling) |
| 용도 2 | 랭킹 + 추천 이유 생성 |

---

## 6. Gemini Function Calling 설계

### 6.1 의도 분석 함수

```json
{
  "name": "extract_restaurant_intent",
  "description": "사용자 자연어에서 맛집 검색 조건과 지역 정보를 추출",
  "parameters": {
    "type": "object",
    "properties": {
      "location_text": {
        "type": "string",
        "description": "텍스트에서 추출한 지역/장소명 (예: '강남역', '홍대', '신촌 현대백화점 앞'). 위치 메시지가 있으면 null."
      },
      "cuisine_type": {
        "type": "array",
        "items": { "type": "string" },
        "description": "음식 종류 (예: ['일식', '라멘'])"
      },
      "party_size": { "type": "integer", "description": "인원 수" },
      "budget_per_person": { "type": "integer", "description": "1인당 예산 (원)" },
      "atmosphere": {
        "type": "array",
        "items": { "type": "string" },
        "description": "분위기 키워드 (예: ['조용한', '데이트', '혼밥 가능'])"
      },
      "max_distance_m": {
        "type": "integer",
        "description": "최대 거리 (미터). 언급 없으면 500"
      },
      "open_now": {
        "type": "boolean",
        "description": "현재 영업중인 곳만 필터링 여부"
      }
    },
    "required": ["cuisine_type"]
  }
}
```

### 6.2 추천 랭킹 프롬프트

```
시스템: 당신은 맛집 큐레이터입니다.
        아래 사용자 조건과 후보 식당 목록을 보고 상위 3개를 선정하세요.
        추천 이유는 한국어 1~2문장, 구체적이고 친근한 말투로 작성하세요.

사용자 조건: {intent_slots}
후보 식당 (거리순 정렬):
{restaurant_list_json}

반환 형식 (JSON):
[
  { "index": 0, "rank": 1, "reason": "추천 이유 문장" },
  ...
]
```

---

## 7. 데이터 플로우

```
텔레그램 메시지 수신
    │
    ├─[위치 메시지]──────────────────────────┐
    │                                        │
    └─[텍스트 메시지]                         │
           │                                 │
           ▼                                 │
    Gemini 의도 분석                          │
    → intent_slots 추출                      │
    → location_text 있으면 Kakao Geocoding   │
           │                                 │
           └──────────────────┬──────────────┘
                              │ coordinates 확정
                              ▼
              병렬 API 호출 (asyncio.gather)
              ├── Google Places Nearby Search
              ├── Kakao 키워드 검색 (좌표 + 반경)
              └── 네이버 지역 검색 (지역명 + 음식종류 쿼리)
                              │
                              ▼
                    결과 통합 & 중복 제거
                    (상호명 + 도로명주소 기준)
                              │
                              ▼
                    [Gemini] 상위 3개 선정
                    + 추천 이유 한국어 생성
                              │
                              ▼
                    텔레그램 메시지 포맷 조립
                              │
                              ▼
                         사용자에게 전송
```

---

## 8. 텔레그램 메시지 포맷

```
📍 강남역 기준 · 이탈리안 · 반경 500m

━━━━━━━━━━━━━━━━━━━━
🥇 트라토리아 봉쥬르 (210m)
⭐ 4.7 (342개) · 🟢 영업중
💬 직접 만든 생면이 일품. 데이트하기 좋은 조용한 분위기예요.
🗺 [카카오맵](https://...) · [구글맵](https://...)

🥈 파스타노나나 (380m)
⭐ 4.5 (189개) · 🟢 영업중
💬 런치 세트 ₩13,000으로 가성비 최고. 점심 시간 인기 맛집이에요.
🗺 [카카오맵](https://...) · [구글맵](https://...)

🥉 올리브키친 (490m)
⭐ 4.3 (97개) · 🔴 영업준비중 (11:30~)
💬 통창 뷰가 예쁜 공간. 저녁 방문을 추천드려요.
🗺 [카카오맵](https://...) · [구글맵](https://...)
━━━━━━━━━━━━━━━━━━━━
🔄 더 보기  |  🔍 조건 변경
```

---

## 9. 커맨드 목록

| 커맨드 | 설명 |
|---|---|
| `/start` | 봇 시작 및 사용법 안내 |
| `/help` | 사용 예시 안내 |
| `/location` | 현재 저장된 위치 확인 |
| `/clear` | 세션 초기화 (위치·이력 삭제) |

---

## 10. 환경변수 (.env)

```env
TELEGRAM_BOT_TOKEN=...
GEMINI_API_KEY=...
KAKAO_REST_API_KEY=...
NAVER_CLIENT_ID=...
NAVER_CLIENT_SECRET=...
GOOGLE_PLACES_API_KEY=...
```

---

## 11. 개발 스택

| 레이어 | 기술 |
|---|---|
| 봇 프레임워크 | `python-telegram-bot` v21 (asyncio) |
| AI | `google-generativeai` SDK (Gemini 2.0 Flash) |
| HTTP 클라이언트 | `httpx` (비동기 병렬 API 호출) |
| 환경변수 | `python-dotenv` |
| 실행 | `python main.py` (Long Polling, 로컬 터미널) |

```
requirements.txt:
python-telegram-bot==21.*
google-generativeai
httpx
python-dotenv
```

---

## 12. 개발 단계

### Phase 1 — MVP (1~2주)

- [ ] `@BotFather`로 봇 생성 + 토큰 발급
- [ ] Long Polling 기본 봇 구동 확인
- [ ] Gemini 의도 분석 (위치 텍스트 추출 포함)
- [ ] Kakao Geocoding (텍스트 → 좌표 변환)
- [ ] Kakao 로컬 검색 연동
- [ ] Google Places 연동
- [ ] 결과 통합 + Gemini 랭킹
- [ ] 텔레그램 메시지 포맷 구현

### Phase 2 — 완성 (1주)

- [ ] 네이버 지역 검색 연동
- [ ] 위치 메시지 수신 처리
- [ ] 세션 내 위치 캐시 (이전 위치 재사용)
- [ ] 인라인 버튼 (더 보기, 조건 변경)
- [ ] 에러 처리 (API 실패 시 나머지로 대체)

### Phase 3 — 고도화

- [ ] 멀티턴 대화 ("더 저렴한 곳으로", "500m 더 넓혀줘")
- [ ] 추천 이력 저장 (SQLite)
- [ ] 영업시간 자동 안내

---

## 13. API 키 발급 체크리스트

- [ ] **Telegram** → `@BotFather` → `/newbot` → Token
- [ ] **Google AI Studio** → Gemini API 키
- [ ] **Google Cloud Console** → Places API (New) 활성화 → API 키
- [ ] **Kakao Developers** → 앱 생성 → REST API 키 → 로컬 API 활성화
- [ ] **Naver Developers** → 앱 등록 → 지역 검색 → Client ID/Secret

---

## 14. 예상 비용 (개인 사용 기준)

| 서비스 | 월 예상 비용 |
|---|---|
| Telegram Bot API | 무료 |
| Google Places API | $0 (월 $200 무료 크레딧으로 커버) |
| Kakao 로컬 API | 무료 |
| 네이버 지역 검색 | 무료 |
| Gemini Flash | ~$0~1 |
| 서버 | $0 (로컬 실행) |
| **합계** | **사실상 $0** |

---

## 15. 리스크 및 대응

| 리스크 | 대응 방안 |
|---|---|
| 텍스트에서 지역명 추출 실패 | Gemini가 `location_text: null` 반환 시 위치 입력 요청 안내 |
| 네이버 API 좌표 미지원 | 지역명 + 음식종류로 쿼리 → 반환 주소를 Geocoding으로 거리 계산 |
| Gemini 응답 지연 | `send_chat_action(ChatAction.TYPING)` 로 대기 중 표시 |
| 로컬 PC 종료 시 봇 중단 | 개인용이므로 허용. 필요 시 추후 클라우드 이전 고려 |
| API 키 노출 | `.env` 파일 사용, `.gitignore`에 반드시 추가 |
