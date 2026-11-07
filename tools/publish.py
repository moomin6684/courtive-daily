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
  - 중복 방지 (11/7): 인스타는 media_publish 에 403(code 4 · subcode 2207051 "action is blocked")을 돌려주면서도
    실제로는 게시하는 경우가 있다(11/3 · 11/5 · 11/6 · 11/7). 그래서
      1) 올리기 전에 계정의 최근 게시물에서 같은 날 캡션(첫 줄 "… DAILY BRIEF · YYYY.MM.DD")을 먼저 찾고, 있으면 올리지 않고 그 게시물로 기록한다.
      2) media_publish 가 실패해도 잠시 뒤 최근 게시물을 다시 확인해, 올라가 있으면 published 로 기록한다.
      3) stale 로 넘기기 전에도 한 번 확인한다.
      4) 지난 시도가 media_publish 에서 실패했는데 게시물을 못 찾으면 다시 올리지 않고 "unconfirmed" 로 멈춘다 (다시 올리려면 force: true).
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


class Unconfirmed(Exception):
    pass


def caption_key(post_dir, m):
    """그날 게시물을 알아보는 표식 — 캡션 첫 줄 (예: 'NOW / DAILY BRIEF · 2026.11.07')."""
    text = (post_dir / m.get("caption_file", "caption.txt")).read_text(encoding="utf-8")
    return next((ln.strip() for ln in text.splitlines() if ln.strip()), "")


def find_existing(ig_id, token, key, limit=12):
    """계정의 최근 게시물 중 캡션에 key 가 들어간 것을 찾는다. 없으면 None."""
    if not key:
        return None
    res = call("GET", f"{ig_id}/media", token, {"fields": "id,caption,permalink,timestamp", "limit": limit})
    for it in res.get("data", []):
        if key in (it.get("caption") or ""):
            return {"media_id": it["id"], "permalink": it.get("permalink")}
    return None


def account(token):
    me = call("GET", "me", token, {"fields": "user_id,username"})
    return me.get("user_id") or me.get("id"), me.get("username")


def publish(post_dir, m, token, repo, branch, checks=4, every=15):
    ig_id, username = account(token)
    key = caption_key(post_dir, m)
    found = find_existing(ig_id, token, key)
    if found:
        print(f"[exists] {post_dir.name}: 이미 올라가 있음 → {found['permalink']}")
        return {"account": username, **found, "note": "이미 게시돼 있어 다시 올리지 않음"}
    if "media_publish" in (m.get("last_error") or "") and not m.get("force"):
        # 지난번에 media_publish 단계까지 갔다면 실제로 올라갔을 수 있다 — 중복을 피하려고 자동으로 다시 올리지 않는다
        raise Unconfirmed("지난 시도가 media_publish 단계에서 실패했고 최근 게시물에서 찾지 못함 — 인스타를 확인한 뒤 다시 올리려면 force: true")
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
    try:
        res = call("POST", f"{ig_id}/media_publish", token, {"creation_id": car["id"]})
    except RuntimeError as e:
        # 403 을 받아도 실제로는 올라간 경우가 있다 — 잠시 기다리며 확인
        for _ in range(checks):
            time.sleep(every)
            found = find_existing(ig_id, token, key)
            if found:
                print(f"[recovered] {post_dir.name}: media_publish 오류에도 게시 확인 → {found['permalink']}")
                return {"account": username, **found, "note": f"media_publish 오류를 받았지만 게시 확인: {str(e)[:160]}"}
        raise
    media_id = res["id"]
    link = call("GET", media_id, token, {"fields": "permalink"}).get("permalink")
    return {"account": username, "media_id": media_id, "permalink": link}


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
            found = None
            try:
                ig_id, username = account(token)
                found = find_existing(ig_id, token, caption_key(mf.parent, m))
            except Exception as e:
                print(f"[warn] {mf.parent.name}: 게시 여부 확인 실패 {e}", file=sys.stderr)
            if found:
                m.update(status="published", account=username, note="stale 처리 전 확인 — 이미 게시돼 있음", **found)
                print(f"[exists] {mf.parent.name} → {found['permalink']}")
            else:
                m["status"] = "stale"
                m["note"] = f"{STALE_HOURS}시간 안에 승인되지 않아 올리지 않음 (올리려면 force: true)"
                print(f"[stale] {mf.parent.name}")
        else:
            try:
                r = publish(mf.parent, m, token, repo, branch)
                m.update(status="published", published_at=datetime.datetime.now(KST).isoformat(timespec="seconds"), **r)
                m.pop("last_error", None)
                print(f"[published] {mf.parent.name} → {r['permalink']}")
            except Unconfirmed as e:    # 중복 위험 — 사람이 확인할 때까지 멈춤
                m.update(status="unconfirmed", note=str(e))
                failed = True
                print(f"[unconfirmed] {mf.parent.name}: {e}", file=sys.stderr)
            except Exception as e:      # 기록만 하고 다음 실행 때 다시 시도
                m["last_error"] = str(e)[:500]
                m["last_attempt"] = datetime.datetime.now(KST).isoformat(timespec="seconds")
                failed = True
                print(f"[error] {mf.parent.name}: {e}", file=sys.stderr)
        mf.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
