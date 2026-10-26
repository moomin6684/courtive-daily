"""렌더 결과를 발행 폴더(posts/<날짜>/)로 옮긴다.

    python3 render.py data/2026-10-27.json
    python3 tools/make_post.py data/2026-10-27.json

posts/<날짜>/ 에 01.jpg … NN.jpg, caption.txt, preview.jpg, manifest.json 을 만든다.
manifest.status 는 "pending" 으로 시작하고, main 에 머지되면 GitHub Actions(publish.yml)가 publish_at 이후에 발행한다.
"""
import datetime
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PUBLISH_HOUR_KST = 16          # 발행 시각 (KST)
CAPTION_LIMIT = 2200           # 인스타그램 캡션 최대 길이
HASHTAG_LIMIT = 30


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    data_path = pathlib.Path(sys.argv[1])
    stem = data_path.stem                       # 2026-10-27
    out = ROOT / "out" / stem
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    if report["overflow"]:
        raise SystemExit(f"렌더 검사에서 문제가 남아 있음 — 발행 폴더를 만들지 않는다: {report['overflow']}")
    jpgs = sorted((out / "jpg").glob("*.jpg"))
    if not 2 <= len(jpgs) <= 10:
        raise SystemExit(f"캐러셀은 2–10장이어야 함 (지금 {len(jpgs)}장)")
    caption = (out / "caption.txt").read_text(encoding="utf-8").strip()
    if len(caption) > CAPTION_LIMIT:
        raise SystemExit(f"캡션이 {len(caption)}자 — {CAPTION_LIMIT}자 이하로 줄일 것")
    if caption.count("#") > HASHTAG_LIMIT:
        raise SystemExit("해시태그가 30개를 넘음")

    post = ROOT / "posts" / stem
    if post.exists():
        old = json.loads((post / "manifest.json").read_text(encoding="utf-8"))
        if old.get("status") == "published":
            raise SystemExit(f"{stem} 은 이미 발행됨 ({old.get('permalink')}) — 덮어쓰지 않는다")
        shutil.rmtree(post)
    post.mkdir(parents=True)
    images = []
    for k, src in enumerate(jpgs, 1):
        name = f"{k:02d}.jpg"
        shutil.copy2(src, post / name)
        images.append({"file": name, "card": src.stem})
    (post / "caption.txt").write_text(caption + "\n", encoding="utf-8")
    from PIL import Image
    Image.open(out / "contact-sheet.png").convert("RGB").save(post / "preview.jpg", quality=85)

    y, m, d = map(int, stem.split("-"))
    kst = datetime.timezone(datetime.timedelta(hours=9))
    manifest = {
        "date": stem,
        "publish_at": datetime.datetime(y, m, d, PUBLISH_HOUR_KST, 0, tzinfo=kst).isoformat(),
        "images": images,
        "caption_file": "caption.txt",
        "status": "pending",
        "created_at": datetime.datetime.now(kst).isoformat(timespec="seconds"),
        "source_data": f"data/{data_path.name}",
    }
    (post / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"post": str(post.relative_to(ROOT)), "images": len(images), "caption_chars": len(caption),
                      "publish_at": manifest["publish_at"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
