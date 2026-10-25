"""승인된(main 에 머지된) 게시물을 인스타그램에 캐러셀로 발행한다. GitHub Actions(publish.yml)에서 실행.

환경 변수
  IG_ACCESS_TOKEN    인스타그램 로그인 방식 장기 토큰 (저장소 Secrets)
  GITHUB_REPOSITORY  owner/repo — 이미지 공개 주소(raw.githubusercontent.com)를 만들 때 쓴다
  PUBLISH_BRANCH     기본 main
  IG_API_BASE        기본 https://graph.instagram.com/v26.0 (테스트 때 가짜 서버로 바꿈)

규칙
  - status 가 "pending" 인 manifest 만 다룬다.
  - publish_at 이전이면 기다린다(다음 예약 실행이 처리).
  - publish_at 에서 STALE_HOURS 가 지나도록 승인이 안 됐으면 "stale" 로 두고 올리지 않는다 (manifest 에 "force": true 면 올림).
  - 발행하면 status/media_id/permalink/published_at 을 manifest 에 적는다 — 워크플로가 커밋한다.
"""
import datetime
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
API = os.environ.get("IG_API_BASE", "https://graph.instagram.com/v26.0").rstrip("/")
STALE_HOURS = 6
KST = datetime.timezone(datetime.timedelta(hours=9))


def call(method, path, token, params=None):
    url = f"{API}/{path.lstrip('/')}"
    data = None
    headers = {"Authorization": f"Bearer {token}"}
    if method == "GET" and params:
        url += "?" + urllib.parse.urlencode(params)
    elif params is not None:
        data = json.dumps(params).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"{method} {path} → HTTP {e.code}: {body[:500]}") from None


def wait_ready(container_id, token, tries=10, every=6):
    for _ in range(tries):
        st = call("GET", container_id, token, {"fields": "status_code"}).get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"container {container_id} status {st}")
        time.sleep(every)
    raise RuntimeError(f"container {container_id} not ready after {tries * every}s")


def publish(post_dir, m, token, repo, branch):
    me = call("GET", "me", token, {"fields": "user_id,username"})
    ig_id = me.get("user_id") or me.get("id")
    base = f"https://raw.githubusercontent.com/{repo}/{branch}/posts/{post_dir.name}"
    children = []
    for img in m["images"]:
        c = call("POST", f"{ig_id}/media", token, {"image_url": f"{base}/{img['file']}", "is_carousel_item": True})
        children.append(c["id"])
    for cid in children:
        wait_ready(cid, token)
    caption = (post_dir / m.get("caption_file", "caption.txt")).read_text(encoding="utf-8").strip()
    car = call("POST", f"{ig_id}/media", token, {"media_type": "CAROUSEL", "children": ",".join(children), "caption": caption})
    wait_ready(car["id"], token)
    res = call("POST", f"{ig_id}/media_publish", token, {"creation_id": car["id"]})
    media_id = res["id"]
    link = call("GET", media_id, token, {"fields": "permalink"}).get("permalink")
    return {"account": me.get("username"), "media_id": media_id, "permalink": link}


def main():
    token = os.environ.get("IG_ACCESS_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    branch = os.environ.get("PUBLISH_BRANCH", "main")
    if not token or not repo:
        raise SystemExit("IG_ACCESS_TOKEN 과 GITHUB_REPOSITORY 가 필요함")
    now = datetime.datetime.now(KST)
    failed = False
    for mf in sorted((ROOT / "posts").glob("*/manifest.json")):
        m = json.loads(mf.read_text(encoding="utf-8"))
        if m.get("status") != "pending":
            continue
        at = datetime.datetime.fromisoformat(m["publish_at"])
        if now < at:
            print(f"[wait] {mf.parent.name}: {at.isoformat()} 에 발행 예정")
            continue
        if now - at > datetime.timedelta(hours=STALE_HOURS) and not m.get("force"):
            m["status"] = "stale"
            m["note"] = f"{STALE_HOURS}시간 안에 승인되지 않아 올리지 않음 (올리려면 force: true)"
            print(f"[stale] {mf.parent.name}")
        else:
            try:
                r = publish(mf.parent, m, token, repo, branch)
                m.update(status="published", published_at=datetime.datetime.now(KST).isoformat(timespec="seconds"), **r)
                print(f"[published] {mf.parent.name} → {r['permalink']}")
            except Exception as e:      # 기록만 하고 다음 실행 때 다시 시도
                m["last_error"] = str(e)[:500]
                m["last_attempt"] = datetime.datetime.now(KST).isoformat(timespec="seconds")
                failed = True
                print(f"[error] {mf.parent.name}: {e}", file=sys.stderr)
        mf.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
