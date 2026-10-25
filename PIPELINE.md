# COURTIVE 데일리 브리프 — 매일 작업 순서

매일 14:07 KST 예약 작업이 이 문서대로 카드를 만들고, **Claude 앱으로 사용자에게 검수를 받는다.**
사용자는 휴대폰 Claude 앱 알림을 열어 완성 이미지와 캡션을 보고 "승인" 또는 수정 요청을 답한다.
승인되면 이 세션이 `post/DATE` 브랜치를 main 에 합치고, GitHub Actions(`publish.yml`)가 15:00 KST 에 인스타그램 @courtive.media 에 올린다.
15:00 이후에 승인하면 바로 올라가고, 21:00(발행 시각 + 6시간)까지 승인이 없으면 올리지 않는다.

## 0. 준비

- 저장소: `moomin6684/courtive-daily` (push 권한으로 붙여서 clone).
- `pip install jinja2 pillow --break-system-packages` (Playwright Chromium 은 이미 설치돼 있음 — 다시 설치하지 말 것).
- 날짜: `DATE` = 오늘 KST(YYYY-MM-DD), `date_kst` = YYYY.MM.DD, `us_game_date` = 미국 동부 기준 어제 날짜.
- 이미 `posts/DATE/manifest.json` 이 `published` 면 아무것도 하지 않고 끝낸다.

## 1. 사실 모으기 (추측 금지)

- 경기: `fetch_sports_data`(nba, scores) → 미국 현지 어제 경기 전부. 주목 경기는 `game_stats` 로 양 팀 최다 득점자 득점·리바운드·어시스트를 확인.
- 순위: `fetch_sports_data`(nba, standings) → 동·서부 15팀씩 순위·승·패.
- 뉴스: WebSearch 로 ESPN · NBA.com · AP · Yahoo Sports 의 지난 24시간 소식. 부상·트레이드·계약·기록. 두 곳 이상에서 확인되거나 공식 발표인 것만 쓴다. 상태는 `공식 발표` / `보도` / `부상 업데이트` 중 하나, `verification` 에 확인 수준을 적는다(예: "보도 · 4~6주 이탈 전망").
- 확인되지 않는 말(인용, 루머, 누적 기록 숫자)은 넣지 않는다. 기록 숫자를 쓰려면 출처를 PR 본문에 남긴다.

## 2. 구성 정하기

템플릿: `templates/card_v3.html.j2` (v3 · 사진 없음 — 로고 · 팀 컬러 · 큰 숫자). `render.py` 기본값.
발행 순서: 표지 → 게임 리포트(최대 3) → 뉴스(1–2) → 스코어보드 → 순위 → 마무리. 총 10장 이하.

- **표지**: 첫 번째 게임 리포트가 '리드 경기'로 표지에 함께 나오므로, 가장 큰 경기 이야기를 `featured` 의 첫 번째에 둔다.
- **표지 헤드라인**: 그날 가장 큰 이야기 하나를 **끝맺은 문장**으로. 2줄, 줄당 한글 9자 안팎(최대 22자). 말이 끊긴 느낌("…의 199번째")이 나면 안 된다. 예: "23점 차 대역전,\n요키치 트리플더블".
- **게임 리포트**: 연장 · 20점 이상 역전 · 5점 차 이내 · 40점 이상/트리플더블 같은 개인 기록 순으로 최대 3경기. 헤드라인 28자 이내(1줄 14자 권장), 라벨 18자 이내.
- **뉴스**: `teams` 에 관련 팀(첫 팀 로고가 위쪽 패널에 나옴). 한눈에 보이는 숫자가 있으면 `key` 를 넣는다 — 예 `{"value": "4–6", "unit": "주", "label": "예상 결장 기간 · 보도"}` (value 5자, label 16자 이내). 숫자가 없으면 넣지 않는다. 제목 3줄·본문 3줄 이내.
- 경기 없는 날: `games: []`, `featured: []` → 표지 · 뉴스 · 순위 · 마무리.
- 마무리: `closing.title` "NBA 소식은\n코티브에서", `follow_cta` "매일 전해주는 NBA 소식" (바꾸지 않음).

## 3. 사진은 쓰지 않는다

v3 부터 카드에 사진을 넣지 않는다(실시간 경기 사진은 라이선스 문제로 쓸 수 없음 — 2026.10.26 결정).
데이터에 `photo` 필드를 넣지 않는다. 로고는 저장소의 `assets/logos/` (NBA 공식 SVG) 만 쓴다.

## 4. 데이터 → 렌더 → 발행 폴더

1. `data/DATE.json` 작성 — `schema.json` 과 예시 `data/2026-10-25.json` 형식 그대로. `timestamp: "auto"`.
2. `python3 render.py data/DATE.json` → **종료 코드 0** 이어야 한다. 1이면 report.json 의 overflow 를 보고 문장을 줄여 다시.
3. `out/DATE/contact-sheet.png` 를 직접 열어 본다: 숫자·이름·팀이 데이터와 같은지, 글자가 겹치거나 잘리지 않았는지.
4. `python3 tools/make_post.py data/DATE.json` → `posts/DATE/` (01.jpg…, caption.txt, preview.jpg, manifest.json).

## 5. 기록(PR)과 Claude 앱 검수 요청

1. 브랜치 `post/DATE` 에 `data/DATE.json`, `posts/DATE/` 를 커밋하고 push. PR 을 연다(기록용 — 사용자는 GitHub 을 보지 않는다).
   Claude 세션에서는 GitHub GraphQL 이 막혀 있으므로 `gh pr create` 대신 REST 로: `gh api repos/moomin6684/courtive-daily/pulls -f title=… -f head=post/DATE -f base=main -f body=@body.md` (Actions 수동 실행도 `gh api -X POST …/actions/workflows/<파일>/dispatches -f ref=main`).
   제목 `[검수] 코티브 데일리 YYYY.MM.DD — <표지 헤드라인 한 줄>`, 본문에 캡션 전문 · 사실 확인 목록(숫자·뉴스마다 출처 링크).
2. 사용자에게 보낸다 (휴대폰에서 보므로 짧게):
   - `PushNotification` 도구가 있으면 "오늘 카드 검수 준비됐어요 — <표지 헤드라인>" 으로 알림.
   - `SendUserFile` 로 `posts/DATE/01.jpg … NN.jpg` 를 순서대로 한 번에 보낸다 (display: render).
   - `SendUserMessage` 로 캡션 전문(코드 블록)과 아래 안내:
     "승인이라고 답하시면 오늘 15:00에 올라갑니다. 고칠 곳은 '3번 제목을 …로'처럼 말씀해 주세요. 21:00까지 답이 없으면 올리지 않습니다."
   - 확인이 덜 된 사실이 있으면 무엇인지 한 줄로 함께 알린다.
3. 여기서 차례를 끝내고 사용자의 답을 기다린다. **답 없이 main 에 합치지 않는다.**

## 5-1. 사용자가 수정을 요청하면

- 문장·숫자·라벨·뉴스 숫자(`key`) → `data/DATE.json` 수정.
- 캡션을 직접 고쳐 달라고 하면 `data/DATE.json` 에 `"caption": "<전문>"` 을 넣는다 (자동 캡션 대신 그대로 쓰임).
- 다시 `render.py` → contact sheet 확인 → `make_post.py` → 브랜치에 커밋·push.
- 바뀐 카드만 `SendUserFile` 로 다시 보내고, 무엇을 바꿨는지 한두 줄로 말한 뒤 다시 승인을 묻는다. 템플릿 디자인을 바꾸는 요청이면 오늘 데이터로 할 수 있는 만큼만 하고, 디자인 변경은 따로 하자고 알린다.

## 5-2. 사용자가 승인하면

- `git checkout main && git pull && git merge --no-ff post/DATE -m "approve: DATE" && git push origin main` (PR 은 이것으로 함께 닫힌다).
- 지금이 15:00 KST 이전이면 "15:00에 올라갑니다", 이후면 "곧 올라갑니다(몇 분 걸림)" 라고 답한다.
- 15:00 이후라면 2–3분 뒤 `posts/DATE/manifest.json` 을 다시 받아 status 가 published 인지 확인하고 permalink 를 알려 준다. 실패(last_error)면 이유를 쉬운 말로 알린다.

## 6. 하지 않는 것

- 사용자의 "승인" 없이 main 에 합치거나 push 하지 않는다 (승인 없이 발행되는 길을 만들지 않음). "좋네", "괜찮아" 처럼 애매하면 "승인으로 올릴까요?" 라고 한 번 묻는다.
- 템플릿(`templates/card_v3.html.j2`) · 렌더러를 매일 작업 중에 고치지 않는다. 문제가 있으면 PR 본문에 적는다.
- 토큰·비밀번호를 파일이나 PR 에 쓰지 않는다.
