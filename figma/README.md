# 피그마 ↔ 카드 생성기 동기화

피그마 파일 `Lah0vPR16klwJSmKtHljcI`, 페이지 `02 · Instagram & Daily Brief`(55:54), 섹션 `G · Daily Brief v2 · 편집용 템플릿`(106:3621).

## 흐름

1. 사용자가 ① 마스터 또는 ② 부품을 고친다.
2. `snapshot.js`의 `__MODE__`를 `diff`로 바꿔 use_figma로 실행 → 처음 그린 상태(숨긴 `_sync` 노드에 저장된 기준값)와 비교해 **바뀐 속성만** 돌려준다.
3. 아래 대응표로 `templates/card_v2.html.j2`의 CSS·마크업을 고치고 `render.py`로 다시 그린다. 렌더 결과와 피그마 스크린샷을 나란히 비교한다.
4. 반영이 끝나면 `__MODE__`를 `baseline`으로 실행해 기준값을 새로 저장한다.

## v3 (기본, 사진 없음) — 섹션 `H · Daily Brief v3 · 사진 없음` (119:7350)

| 마스터 | id | 템플릿 분기 (`card_v3.html.j2`) |
|---|---|---|
| v3/Card/01 Cover | 120:7436 | `cover` (v3.1: `{{date_kst}}` top 88 · `Title Area (skew -9°)` 200–1130 가운데 정렬 → `.cv-title`(skewX(-9deg)) · `Stripe` → `cut(1250)`) |
| v3/Part/Court Lines (Tone=Navy) | 134:9597 (Navy 134:9582) | `court('navy')` 매크로 — 남색 카드(표지·게임 리포트·마무리) 맨 아래 레이어 `Court Lines`(잠금). 밝은 카드에는 쓰지 않음. 뉴스 위쪽 패널은 `Panel Court Lines`(패널 모양 마스크) = `court('navy', clip)` |
| v3/Card/04c Scoreboard · Grid (11–15경기) | 152:10303 | `scoreboard` + `card.grid` (`.rows.grid`, 두 열 · 줄 높이 `--rh`) — Score Row `Density=Grid` (152:10195) 사용 |
| v3/Part/Result Mark (W / L) | 152:9716 (W 152:9712 · L 152:9715) | 순위표 `tri()` — Standing Row 의 `{{today}}` 칸(20px) 안 `Result Mark`, 그날 경기 안 한 팀은 숨김 |
| v3/Card/01b Cover · Score (보관) | 120:7576 | 10/26부터 안 씀 — 스냅샷 대상에서 뺌 |
| v3/Card/02 Game Report | 121:7795 | `game` (`.hero`, `.top`) |
| v3/Card/03 News | 121:7844 | `news` (패널 · `.key` · 본문) |
| 04 Scoreboard · 05 Standings · 06 Closing | G 섹션 v2 마스터 | v2 와 같은 마크업 |

| v3 부품 | id | CSS |
|---|---|---|
| v3/Hero Team | 119:7377 | `.hero .tm`, `.dsc`, `.hero .ab/.ko` |
| v3/Top Scorer | 119:7411 | `.top .who/.nm/.line/.v/.k` |

미리보기(③): 121:8066 … 121:10216. 기준값(`_sync`)은 G 섹션에 v2 · v3 를 함께 저장한다.

## v2 노드 (G 섹션)

| 마스터 (발행 순서) | id | 템플릿 분기 |
|---|---|---|
| v2/Card/01 Cover | 108:3881 | `card.kind == 'cover'` (사진 있음) |
| v2/Card/02 Game Report | 108:4174 | `game` (사진 있음) |
| v2/Card/03 News · Photo | 110:4771 | `news`, 사진 있음 (기본) |
| v2/Card/04 Scoreboard · Dense | 109:5169 | `scoreboard`, `card.dense` |
| v2/Card/04b Scoreboard · Sparse | 109:5548 | `scoreboard`, sparse |
| v2/Card/05 Standings | 111:6238 | `standings` |
| v2/Card/06 Closing | 110:4797 | `closing` |
| v2/Card/99 News · Logo Panel (예비) | 110:4744 | `news`, 사진 없음 + `allow_logo_panel` |

| 부품 | id | CSS |
|---|---|---|
| v2/Header (Tone=Dark/Light) | 107:3628 | `.header`, `.header.dark/.light` (워드마크만) |
| v2/Footer (Tone=Dark/Light) | 107:3645 | `.footer .note` (크레딧 한 줄, 비면 안 그림) |
| v2/Score Row (Density) | 107:3864 | `.srow`, `.sside`, `.score .p/.sep` (+ `.sparse`) |
| v2/Standing Row | 107:3894 | `.trow` |
| v2/Leader | 107:3928 | `.leader .who/.nm/.line/.v/.k` |
| v2/Duel Team | 107:3952 | `.team`, `.disc`, `.team .ab` |

미리보기(③, 마스터의 인스턴스): 112:5793 … 112:7955. 그리지 않은 변형: 사진 없는 표지(심벌), 사진 없는 게임 리포트(사선만) — 마스터가 바뀌면 같은 규칙으로 맞춘다.

## 대응 규칙

- 카드 직속 레이어의 `x, y` = CSS `left`(56 = `--pad`)와 `top`. 예: Cover `Lede` y=930 → `.layer` `top:930px`.
- 오토 레이아웃 `gap` = 형제 사이 `margin-top`(세로) 또는 `gap`(가로). `padding` = CSS padding.
- 글자: Figma `size / lh` = CSS `font-size / line-height`, `ls -1%` = `letter-spacing:-.01em`. 글꼴 Noto Sans KR Regular/Bold/Black = 400/700/900, Barlow Condensed Bold = `--num` 700, Anton = `--display`.
- 색: `var:Color/Blue` → `var(--blue)`, Navy/Ice/White/Cyan 동일, `Color/Mute On Light` → `--mute-on-white`, `Color/Mute On Dark` → `--mute-on-navy`, `Color/Line Ice` → `--line-on-ice`. `var:Team/ABBR/Role`는 데이터(`accent()`)가 고르므로 템플릿에 고정하지 않는다.
- 배경 `fills` 의 그라디언트(아래부터: 단색 변수 → 세로 선형 → 원형 3개) = CSS `--bg-navy` / `--bg-ice` (아래 층이 CSS 목록의 뒤쪽). 원형 그라디언트 중심·반지름은 `gradientTransform` 에서 cx = (0.5−tx)/a, rx = 0.5/a. 효과 `Noise` = CSS `.card::after` 그레인(`assets/texture/grain.png`, 남색 overlay `--grain-navy`, 밝은 카드 normal `--grain-ice`) — Figma 노이즈와 코드 그레인은 모양이 조금 달라서 세기(투명도)만 맞춘다.
- `Photo` 높이 = `photo(src, h)`의 h, `Cut mask` 오른쪽 높이 차 = `--cut`(100). `Stripe` 두께 = `--stripe`(14).
- 로고 슬롯 `{{…logo}}` 프레임 크기 = CSS 로고 너비·높이. 안의 Team Logo 인스턴스는 슬롯 크기 ÷ 0.85로 그려 보이는 크기를 맞춘다.
- `{{ }}` 레이어의 글자 내용은 데이터라서 반영하지 않는다. 스타일·위치·크기만 반영한다.
- 이긴 팀 점수 색(스코어 행 Blue, 게임 리포트 Cyan)은 인스턴스 덮어쓰기로 칠한 규칙이다. 마스터의 승패 예시 색을 바꾸면 그 규칙을 바꾼 것으로 본다.

## 반영 기록

- 10/26 1차 수정: 헤더는 워드마크만 · 푸터는 사진 크레딧 한 줄(출처·시각·쪽 번호 삭제) · 표지 '미국 현지 … 경기' 줄 삭제 · 뉴스 본문 top 704 + 흰 심벌 워터마크 50% · 순위 표 top 339 + 블루 심벌 6% · 마무리는 시안 제목(top 220) + 하단 한 줄 안내(top 1214), STAY COURTIVE·저장 안내·참고 출처 삭제. 함께 고친 것: 1–4경기 스코어 점수 칸 300 → 380(숫자 156), 뉴스는 사진 기본(로고 패널은 예비). 사진 카드에서는 라이선스 때문에 크레딧 줄을 지우지 않는다.
- 인스턴스 안에서 숨기거나 지운 글자도 잡도록 스냅샷에 `kids`를 추가했다.
- 10/26 확정(v2.0): 발행 순서를 표지 → 게임 리포트(최대 3) → 뉴스 → 스코어보드 → 순위 → 마무리로 바꿨다(`build_cards`).
- 10/26 v3: 사진을 쓰지 않기로 하고 v3 를 만듦. 표지는 로고 · DAILY BRIEF 날짜 · 강조 타이틀(*별표* → 시안) · 핵심 숫자 하나(스코어형 / 선수 기록형). 점수는 176px, 259px 칸 고정 + 넘침 검사.
- 10/26 v3 1차 수정: 표지 타이틀 top 316 → 294 · 게임 리포트 점수와 상태 사이 20px · 헤드라인 가운데 정렬 top 734 · TOP SCORERS 는 한 줄 헤드라인 기준 860 (두 줄이면 그만큼 아래로) · 뉴스 큰 숫자 자간 4%.
- 10/26 v3.1 표지 단순화: 피드 그리드를 위해 표지는 날짜(64px 시안, top 88) + 가운데 큰 타이틀 하나(132px Black, 2줄, 넘으면 120→108→96)만. 헤더·DAILY BRIEF·스코어·선수 기록 삭제. 사선 띠는 맨 아래(top 1150)로, 그날 주인공 팀 컬러. 마스터 예시 문장은 120px 단계(코드의 자동 축소와 같은 결과). Cover · Score 는 보관(반투명).
- 10/26 v3.2 배경 질감: 남색 카드(표지·게임 리포트·마무리, 뉴스 위쪽 패널)는 세로 그라디언트 + 푸른 빛 번짐 3개, 밝은 카드(뉴스·스코어보드·순위)는 옅은 하늘색 번짐 2개. 모든 카드에 노이즈 질감. v3 가 함께 쓰는 v2 마스터(04 스코어보드·05 순위·06 마무리)에도 적용됨.
- 10/26 v3.3 코트 라인 패턴: 카드 가로 1080 = 코트 폭 50ft(21.6px/ft), 아래가 베이스라인인 실제 비율 하프코트를 2px 얇은 선으로 모든 카드 바닥에 깖(남색 카드 흰색 12%, 밝은 카드 블루 13%). 레인 두 줄(x 367·713)·자유투 라인(y 940)·하프 라인(y 335)은 카드 끝까지 늘려 격자 역할. 자유투 원 아래 반은 점선(실제 코트 규칙).
- 10/26 v3.4: 그라디언트 세기 절반(남색 번짐 .17/.12/.08, 밝은 카드 .06/.045). 카드 문구 쉼표·마침표 금지 — 피그마 예시 문장도 같이 고침, 스코어보드 안내 '원정 왼쪽 · 홈 오른쪽'.
- 10/26 v3.5: 코트 라인 패턴은 어두운 면에만 — 밝은 하늘색 카드(뉴스 본문·스코어보드·순위)에서 뺌, Ice 변형 삭제.
- 10/26 v3.6 표지 타이틀 강조: 시안 A~D 중 사용자가 A(기울임) 선택. 로고 사선처럼 9° 기울임(피그마는 Title Area 프레임에 기울임 변환), 150px 시작(→136→124→112), 자간 -5%. 강조 단어는 그대로 시안 글자.
- 10/27 v3.7: 스코어보드는 경기 수와 상관없이 한 장 — 9–10경기는 한 줄 목록(줄 높이 87/77), 11–15경기는 두 줄 격자(한국어 팀명 생략). 순위표에 그날 경기 결과 ▲ 승(#14A85A) ▼ 패(#E5374B) 칸 추가(한국어 팀명 칸 204→176), 머리글에 범례 '▲ 승 ▼ 패 · 오늘 경기'.
