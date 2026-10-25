#!/usr/bin/env python3
"""COURTIVE Daily Brief card renderer.

Usage:  python3 render.py data/2026-10-24.json [--out out/2026-10-24]

Reads one day's brief data (see schema.json), applies the Figma rules
(scoreboard layout by game count, game-card type, winner colours, page numbers),
renders each card as 1080x1350 PNG with headless Chromium, and fails loudly when
any text slot overflows its box after the allowed font-size steps.
"""
import argparse, json, math, pathlib, sys, datetime
from jinja2 import Environment, FileSystemLoader

ROOT = pathlib.Path(__file__).resolve().parent

TEAMS = {k: v for k, v in json.loads((ROOT / "teams.json").read_text(encoding="utf-8")).items() if not k.startswith("_")}
TEAM_KO = {k: v["ko"] for k, v in TEAMS.items()}

# COURTIVE backgrounds a team accent can sit on
BG = {"white": "#FFFFFF", "ice": "#EAF4FF", "navy": "#0A2147", "blue": "#146BFF"}
MIN_ACCENT_CONTRAST = 1.8   # 팀 컬러 바·칩이 배경과 구분되는 최소 대비. 미달이면 다음 팀 컬러로


def _lum(hexc):
    r, g, b = (int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _lab(hexc):
    r, g, b = (int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5))
    lin = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = lin(r), lin(g), lin(b)
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e(a, b):
    return sum((p - q) ** 2 for p, q in zip(_lab(a), _lab(b))) ** 0.5


MIN_HUE_DELTA = 45          # 밝기가 비슷해도 색상 차이가 이만큼 크면(예: 빨강 vs 코티브 블루) 구분된다고 본다


def distinct(c, bg):
    return contrast(c, bg) >= MIN_ACCENT_CONTRAST or (delta_e(c, bg) >= MIN_HUE_DELTA and contrast(c, bg) >= 1.15)


def accent(abbr, bg):
    """첫 번째로 배경과 충분히 구분되는 팀 컬러(주 → 보조 → 3차). 모두 미달이면 대비가 가장 큰 색."""
    cols = TEAMS.get(abbr, {}).get("colors") or ["#0A2147"]
    for c in cols:
        if distinct(c, BG[bg]):
            return c
    return max(cols, key=lambda c: contrast(c, BG[bg]))


def accents(abbr):
    return {k: accent(abbr, k) for k in BG}


LOGO_DIR = ROOT / "assets" / "logos"


def logo(abbr):
    """NBA 공식 SVG 원본(assets/logos/ABBR.svg). 없으면 None → 템플릿이 로고 없이 그린다."""
    p = LOGO_DIR / f"{abbr}.svg"
    return p.as_uri() if p.exists() else None
STATUS_CLASS = {"공식 발표": "official", "보도": "report", "부상 업데이트": "injury"}
CLOSE_MARGIN = 5        # 접전: 5점 차 이내
COMEBACK_DEFICIT = 20   # 대역전: 최대 열세 20점 이상을 뒤집은 승리

FIT_JS = """
() => {
  const warn = [];
  for (const el of document.querySelectorAll('[data-fit]')) {
    const cs = getComputedStyle(el);
    const maxLines = +el.dataset.fit;
    const one = el.classList.contains('one');
    const base = parseFloat(cs.fontSize);
    const baseLh = parseFloat(cs.lineHeight);
    const steps = el.dataset.steps ? el.dataset.steps.split(',').map(Number) : [base];
    const lhRatio = el.dataset.lh ? +el.dataset.lh : null;
    let ok = false, used = base, lines = 0;
    for (const s of steps) {
      el.style.fontSize = s + 'px';
      const lh = lhRatio ? s * lhRatio : baseLh;
      if (lhRatio) el.style.lineHeight = lh + 'px';
      if (one) { ok = el.scrollWidth <= el.clientWidth + 1; lines = 1; }
      else { lines = Math.round(el.getBoundingClientRect().height / lh); ok = lines <= maxLines; }
      used = s;
      if (ok) break;
    }
    if (!ok) warn.push({slot: el.dataset.slot, text: el.textContent.trim(), lines, maxLines});
    else if (used !== base) warn.push({slot: el.dataset.slot, shrunk_to: used, text: el.textContent.trim(), info: true});
  }
  const c = document.querySelector('.content');
  if (c && c.scrollHeight > c.clientHeight + 1) warn.push({slot: 'content', text: 'content area overflows by ' + (c.scrollHeight - c.clientHeight) + 'px'});
  // v2: absolutely placed layers must end above the footer
  const ft = document.querySelector('.footer');
  if (!c) {
    const limit = (ft ? ft.getBoundingClientRect().top : 1350 - 40) - 16;
    for (const l of document.querySelectorAll('.layer.pad')) {
      const b = l.getBoundingClientRect().bottom;
      if (b > limit) warn.push({slot: 'layer', text: 'layer runs into the footer by ' + Math.round(b - limit) + 'px'});
    }
  }
  return warn;
}
"""


def side(abbr, score, win):
    return {"abbr": abbr, "ko": TEAM_KO.get(abbr, abbr), "score": score, "win": win, "c": accents(abbr), "logo": logo(abbr)}


def prep_game(g):
    a, h = g["away"], g["home"]
    aw = a["score"] > h["score"]
    ot = int(g.get("ot", 0))
    ot_label = "" if ot == 0 else ("OT" if ot == 1 else f"{ot}OT")
    return {
        **g,
        "away": side(a["abbr"], a["score"], aw),
        "home": side(h["abbr"], h["score"], not aw),
        "ot_label": ot_label,
        "status_label": "FINAL" if not ot else f"FINAL · {ot_label}",
        "margin": abs(a["score"] - h["score"]),
    }


def game_type(g, comeback):
    if g["ot_label"]:
        return "연장"
    if comeback is not None and comeback >= COMEBACK_DEFICIT:
        return "대역전"
    if g["margin"] <= CLOSE_MARGIN:
        return "접전"
    return "일반"


def default_label(t, g, comeback):
    return {"연장": f"연장 · {g['ot_label']}", "대역전": f"대역전 · {comeback}점 차 극복",
            "접전": f"접전 · {g['margin']}점 차", "일반": "일반"}[t]


def build_cards(d):
    games = [prep_game(g) for g in d.get("games", [])]
    n = len(games)
    # 순서(10/26 확정): 표지 → 게임 리포트 → 뉴스 → 스코어보드 → 순위 → 마무리
    cards = [{"kind": "cover"}]
    boards = []
    if n:
        if n <= 4:
            boards.append({"kind": "scoreboard", "dense": False, "games": games, "summary": f"{n}경기 · 최종 스코어"})
        elif n <= 8:
            boards.append({"kind": "scoreboard", "dense": True, "games": games, "summary": f"{n}경기 · 최종 스코어"})
        else:
            first = math.ceil(n / 2)
            parts = [games[:first], games[first:]]
            start = 1
            for i, part in enumerate(parts):
                end = start + len(part) - 1
                boards.append({"kind": "scoreboard", "dense": True, "games": part,
                              "summary": f"{n}경기 중 {start}–{end} · {i + 1} / 2"})
                start = end + 1
        for f in d.get("featured", []):
            g = next((x for x in games if x["away"]["abbr"] == f["away"] and x["home"]["abbr"] == f["home"]), None)
            if g is None:
                raise SystemExit(f"featured game {f['away']}@{f['home']} is not in games[]")
            comeback = f.get("max_deficit_overcome")
            t = f.get("type") or game_type(g, comeback)
            cards.append({"kind": "game", "game": g, "type": t,
                          "label": f.get("label") or default_label(t, g, comeback),
                          "headline": f["headline"],
                          "photo": f.get("photo"), "photo_credit": f.get("photo_credit", ""), "photo_pos": f.get("photo_pos"), "photo_zoom": f.get("photo_zoom"),
                          "away_leader": {**f["away_leader"], "team": g["away"]["abbr"], "c": g["away"]["c"], "logo": g["away"]["logo"]},
                          "home_leader": {**f["home_leader"], "team": g["home"]["abbr"], "c": g["home"]["c"], "logo": g["home"]["logo"]}})
    for nws in d.get("news", []):
        tags = [{"abbr": t, "ko": TEAM_KO.get(t, t), "c": accents(t), "logo": logo(t)} for t in nws.get("teams", [])]
        cards.append({"kind": "news", "news": {**nws, "tags": tags, "status_class": STATUS_CLASS[nws["status"]]}})
    # v3 표지: 첫 게임 리포트를 '리드 경기'로, 오늘 구성 개수를 색인으로 보여 준다
    games_cards = [c for c in cards if c["kind"] == "game"]
    cards[0]["lead"] = games_cards[0] if games_cards else None
    cards[0]["counts"] = {"games": n, "reports": len(games_cards), "news": len(d.get("news", []))}
    cards.extend(boards)
    cards.append({"kind": "standings"})
    cards.append({"kind": "closing"})
    total = len(cards)
    for i, c in enumerate(cards, 1):
        c["page"] = f"{i:02d} / {total:02d}"
    return cards


def caption(d, cards):
    """발행용 캡션(2,200자 · 해시태그 30개 이내). 카드에 없는 출처와 사진 크레딧을 여기서 밝힌다."""
    lines = [f"NOW / DAILY BRIEF · {d['date_kst']}", "", d["cover"]["headline"].replace("\n", " "), ""]
    for c in cards:
        if c["kind"] == "game":
            g = c["game"]; w, l = (g["away"], g["home"]) if g["away"]["win"] else (g["home"], g["away"])
            ot = f" ({g['ot_label']})" if g["ot_label"] else ""
            lines.append(f"▸ {w['ko']} {w['score']}-{l['score']} {l['ko']}{ot} · {c['headline']}")
        elif c["kind"] == "news":
            n = c["news"]; lines.append(f"▸ {n['title'].replace(chr(10), ' ')} ({n.get('verification') or n['status']})")
    n_games = len(d.get("games", []))
    lines += ["", (f"미국 현지 {d['us_game_date']} {n_games}경기 결과와 동·서부 순위는 슬라이드에서 확인하세요." if n_games
                   else "오늘은 경기가 없는 날이라 뉴스와 순위만 정리했어요."), ""]
    refs = d.get("closing", {}).get("references", "").replace("\n", " / ")
    if refs:
        lines.append("출처 " + refs)
    credits = [h.get("photo_credit") for h in [d["cover"], *d.get("featured", []), *d.get("news", [])] if h.get("photo") and h.get("photo_credit")]
    for cr in dict.fromkeys(credits):
        lines.append("사진 " + cr)
    tags = ["#NBA", "#NBA데일리", "#코티브", "#COURTIVE", "#농구", "#NBA결과"]
    for c in cards:
        if c["kind"] == "game":
            for side in ("away", "home"):
                t = "#" + TEAMS.get(c["game"][side]["abbr"], {}).get("name", "").replace(" ", "")
                if t != "#" and t not in tags:
                    tags.append(t)
    lines += ["", " ".join(tags[:30])]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("--out")
    ap.add_argument("--template", default="card_v3.html.j2", help="card_v3.html.j2 (사진 없음, 기본) · card_v2.html.j2 (사진) · card.html.j2 (v1)")
    args = ap.parse_args()
    d = json.loads(pathlib.Path(args.data).read_text(encoding="utf-8"))
    if d.get("timestamp", "auto") == "auto":
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        d["timestamp"] = now.strftime("%Y.%m.%d %H:%M KST")
    d.setdefault("disclaimer", "")
    d.setdefault("data_source", "경기 데이터 · Sportradar")
    d["coverage_parts"] = [{"t": "미국 경기일 "}, {"t": f"{d['us_game_date']} (ET)", "n": True}]
    st = d["standings"]
    for conf in ("east", "west"):
        for t in st[conf]:
            t.setdefault("ko", TEAM_KO.get(t["abbr"], t["abbr"]))
            t["c"] = accents(t["abbr"])
            t["logo"] = logo(t["abbr"])
    # 사진: 데이터 파일 기준 상대 경로. 파일이 없으면 사진 없는 레이아웃으로 그리고 경고만 남긴다.
    base = pathlib.Path(args.data).resolve().parent
    photo_notes = []
    for holder in [d["cover"], *d.get("featured", []), *d.get("news", [])]:
        ph = holder.get("photo")
        if not ph:
            continue
        p = (base / ph).resolve()
        if p.exists():
            if not holder.get("photo_credit"):
                raise SystemExit(f"photo {ph} has no photo_credit — 크레딧 없는 사진은 쓰지 않는다")
            holder["photo"] = p.as_uri()
        else:
            photo_notes.append(f"사진 없음 → 사진 없이 렌더: {ph}")
            holder["photo"] = None
    st["as_of_parts"] = [{"t": "기준 "}, {"t": st.get("as_of", d["timestamp"]), "n": True}, {"t": " · " + st.get("note", "리그 순위")}]

    out = pathlib.Path(args.out or ROOT / "out" / pathlib.Path(args.data).stem).resolve()
    (out / "html").mkdir(parents=True, exist_ok=True)
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True)
    tpl = env.get_template(args.template)
    cards = build_cards(d)

    from playwright.sync_api import sync_playwright
    problems, notes, pngs = [], [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
        for i, c in enumerate(cards, 1):
            html = tpl.render(d=d, card=c, page=c["page"], fonts=(ROOT / "assets" / "fonts").as_uri())
            hp = out / "html" / f"{i:02d}-{c['kind']}.html"
            hp.write_text(html, encoding="utf-8")
            page.goto(hp.as_uri())
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(150)
            for w in page.evaluate(FIT_JS):
                (notes if w.get("info") else problems).append({"card": i, "kind": c["kind"], **w})
            png = out / f"{i:02d}-{c['kind']}.png"
            page.screenshot(path=str(png), clip={"x": 0, "y": 0, "width": 1080, "height": 1350})
            pngs.append(png)
            # 인스타그램 업로드용 JPEG (게시 API는 JPEG만 받는다)
            (out / "jpg").mkdir(exist_ok=True)
            from PIL import Image as _I
            _I.open(png).convert("RGB").save(out / "jpg" / f"{i:02d}-{c['kind']}.jpg", quality=92, subsampling=0)
        browser.close()
    # v2: 뉴스는 사진으로 쓴다. 로고 패널은 사진을 끝내 못 구했을 때만 쓰는 예비 레이아웃이라 발행 전에 막는다.
    if "v2" in args.template:
        for i, c in enumerate(cards, 1):
            if c["kind"] == "news" and not c["news"].get("photo") and not c["news"].get("allow_logo_panel"):
                problems.append({"card": i, "kind": "news", "slot": "news[].photo",
                                 "text": "뉴스 카드에 사진이 없음 — 출처가 분명한 CC 사진을 넣거나, 정말 없으면 allow_logo_panel: true"})

    # contact sheet for quick review
    from PIL import Image
    cols, scale = 3, 0.32
    w, h = int(1080 * scale), int(1350 * scale)
    rows = math.ceil(len(pngs) / cols)
    sheet = Image.new("RGB", (cols * w + (cols + 1) * 16, rows * h + (rows + 1) * 16), "#d9dde3")
    for k, pth in enumerate(pngs):
        im = Image.open(pth).convert("RGB").resize((w, h), Image.LANCZOS)
        sheet.paste(im, (16 + (k % cols) * (w + 16), 16 + (k // cols) * (h + 16)))
    sheet.save(out / "contact-sheet.png")

    # 인스타그램 캡션: 카드에서 뺀 출처·사진 크레딧은 여기에 모은다
    # 검수 중 사용자가 캡션 문장을 직접 고치면 data 의 "caption" 에 전문을 넣는다 → 그대로 쓴다
    (out / "caption.txt").write_text(d.get("caption") or caption(d, cards), encoding="utf-8")

    report = {"cards": [f"{c['page']} {c['kind']}" + (f" ({c.get('type')})" if c['kind'] == 'game' else '') for c in cards],
              "shrunk": notes, "photos": photo_notes, "overflow": problems}
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
