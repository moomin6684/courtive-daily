"""COURTIVE 인스타그램 계정 세팅 키트: 프로필 사진 2종 + 하이라이트 커버 5종."""
import pathlib
from playwright.sync_api import sync_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "instagram-kit"; OUT.mkdir(parents=True, exist_ok=True)
FONTS = (ROOT / "assets" / "fonts").as_uri()
SYM = 'M384 0H960L328.226 273.933C311.4 281.226 299.22 297.84 294.54 317.46L268.997 424.473C262.86 450.18 271.02 471.362 301.08 471.362H577.481C588 471.362 596.1 475.242 604.627 481.234L804.524 621.902L792.185 656.452C785.436 675.336 762.84 686.067 742.828 686.067H160.411C64.5 686.067 0 621.6 0 527.4C0 507 3.6 492 7.2 475.2L48.21 283.8C57.81 238.77 80.1 204.12 115.99 172.751L254.19 51.8252C292.5 18.3 327.6 0 384 0ZM927.918 130.797L826.735 547.866L602.159 387.455L629.306 286.272C631.548 277.914 640.2 272.13 646.581 268.997L927.918 130.797Z'
HEAD = f'''<!doctype html><meta charset="utf-8"><style>
@font-face{{font-family:Anton;src:url("{FONTS}/anton-latin-400-normal.woff2")}}
@font-face{{font-family:"Noto Sans KR";font-weight:700;src:url("{FONTS}/noto-sans-kr-korean-700-normal.woff2");unicode-range:U+AC00-D7A3,U+3130-318F}}
*{{margin:0;padding:0;box-sizing:border-box}} body{{overflow:hidden}}
</style>'''
def profile(bg, fg):
    # Instagram crops a circle; the symbol sits inside its 80% safe zone, optically centred
    return HEAD + f'''<body style="width:1080px;height:1080px;background:{bg};display:flex;align-items:center;justify-content:center">
<svg width="640" height="457" viewBox="0 0 960 686" style="margin-left:24px"><path fill="{fg}" fill-rule="evenodd" d="{SYM}"/></svg></body>'''
def cover(word, ko, accent):
    return HEAD + f'''<body style="width:1080px;height:1920px;background:#0A2147;position:relative">
<svg width="1080" height="1920" style="position:absolute;inset:0"><path d="M0 1180 L1080 1080 L1080 1094 L0 1194 Z" fill="{accent}"/></svg>
<div style="position:absolute;left:0;right:0;top:790px;text-align:center;color:#fff;font:400 150px/150px Anton;letter-spacing:.01em">{word}</div>
<div style="position:absolute;left:0;right:0;top:1250px;text-align:center;color:#8FA3C7;font:700 44px/56px 'Noto Sans KR'">{ko}</div>
</body>'''
jobs = {"profile-blue": (profile("#146BFF", "#FFFFFF"), 1080, 1080),
        "profile-navy": (profile("#0A2147", "#4DDCFF"), 1080, 1080)}
for i, (w, ko, acc) in enumerate([("DAILY", "데일리 브리프", "#146BFF"), ("STORY", "선수 · 팀 이야기", "#4DDCFF"),
                                  ("REPLAY", "장면 다시 보기", "#4DDCFF"), ("NOTE", "룰 · 전술 · 용어", "#4DDCFF"),
                                  ("ABOUT", "코티브 소개", "#146BFF")], 1):
    jobs[f"highlight-{i}-{w.lower()}"] = (cover(w, ko, acc), 1080, 1920)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    for name, (html, w, h) in jobs.items():
        f = OUT / f"{name}.html"; f.write_text(html, encoding="utf-8")
        pg.set_viewport_size({"width": w, "height": h}); pg.goto(f.as_uri()); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(150)
        pg.screenshot(path=str(OUT / f"{name}.png")); f.unlink()
    b.close()
# preview: profile as a circle at feed size + highlight circles
from PIL import Image, ImageDraw
sheet = Image.new("RGB", (1500, 560), "white"); d = ImageDraw.Draw(sheet)
for k, n in enumerate(["profile-blue", "profile-navy"]):
    im = Image.open(OUT / f"{n}.png").resize((300, 300)); m = Image.new("L", (300, 300), 0); ImageDraw.Draw(m).ellipse((0, 0, 299, 299), fill=255)
    sheet.paste(im, (40 + k * 340, 40), m)
for k, n in enumerate(sorted(OUT.glob("highlight-*.png"))):
    im = Image.open(n); c = im.crop((0, 420, 1080, 1500)).resize((200, 200)); m = Image.new("L", (200, 200), 0); ImageDraw.Draw(m).ellipse((0, 0, 199, 199), fill=255)
    sheet.paste(c, (40 + k * 280, 340), m)
sheet.save(OUT / "preview.png")
print(sorted(x.name for x in OUT.iterdir()))
