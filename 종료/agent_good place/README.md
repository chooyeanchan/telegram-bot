# 🍽️ 맛집 추천

텔레그램으로 위치와 원하는 음식을 말하면, 여러 지도 API를 조합해 맛집/장소를 추천해주는 봇입니다.

## 주요 기능

- 텔레그램 위치 공유 + 텍스트("혼밥하기 좋은 일식집") → 주변 맛집 추천
- 지역명만 텍스트로 입력해도 검색 가능 ("강남역 근처 파스타 맛집 알려줘")
- Google Places, 카카오 로컬, 네이버 로컬 검색 결과를 종합해 랭킹
- `/location` — 저장된 위치 확인, `/clear` — 세션 초기화

## 설치

```bash
cd "종료/agent_good place"
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

## 환경 변수 (`.env`)

| 변수 | 설명 | 발급처 |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | 텔레그램 봇 토큰 | [@BotFather](https://t.me/BotFather) |
| `GEMINI_API_KEY` | 의도 파싱에 사용하는 Gemini API 키 | [Google AI Studio](https://aistudio.google.com) |
| `GEMINI_MODEL` | 사용할 Gemini 모델 | — |
| `GOOGLE_PLACES_API_KEY` | 장소 검색 | [Google Cloud Console](https://console.cloud.google.com) |
| `KAKAO_REST_API_KEY` | 카카오 로컬 검색 | [Kakao Developers](https://developers.kakao.com) |
| `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` | 네이버 로컬 검색 | [Naver Developers](https://developers.naver.com) |
| `ALLOWED_CHAT_ID` | 이 봇을 사용할 수 있는 유일한 텔레그램 chat ID | [@userinfobot](https://t.me/userinfobot) 등으로 확인 |

## 실행

```bash
python3 main.py
```

## 보안

- `ALLOWED_CHAT_ID`와 일치하지 않는 사용자의 요청은 무시합니다.
- API 키가 5개나 관여하는 만큼, `.env` 커밋 여부를 반드시 두 번 확인하세요.
- `.env`, `nohup.out`은 `.gitignore`에 포함되어 있습니다.
