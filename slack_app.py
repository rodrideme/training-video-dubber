import hashlib
import hmac
import os
import re
import threading
import time

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request

load_dotenv()

app = Flask(__name__)

LOOM_RE = re.compile(r'https://(?:www\.)?loom\.com/share/[a-zA-Z0-9]+')

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "")


# ── Slack helpers ─────────────────────────────────────────────────────────────

def _verify_signature(req) -> bool:
    timestamp = req.headers.get("X-Slack-Request-Timestamp", "")
    if not timestamp or abs(time.time() - int(timestamp)) > 300:
        return False
    body = req.get_data(as_text=True)
    base = f"v0:{timestamp}:{body}"
    expected = "v0=" + hmac.new(
        SLACK_SIGNING_SECRET.encode(),
        base.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, req.headers.get("X-Slack-Signature", ""))


def _post(channel: str, thread_ts: str, text: str) -> None:
    requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
        json={"channel": channel, "thread_ts": thread_ts, "text": text},
        timeout=10,
    )


# ── Background worker ─────────────────────────────────────────────────────────

def _process(urls: list, channel: str, thread_ts: str) -> None:
    from src.pipeline import run_pipeline

    count = len(urls)
    if count == 1:
        _post(channel, thread_ts, f"⏳ Got it! Starting pipeline for:\n`{urls[0]}`")
    else:
        _post(channel, thread_ts, f"⏳ Got it! Processing *{count} videos* one by one...")

    for i, url in enumerate(urls, 1):
        prefix = f"*[{i}/{count}]* " if count > 1 else ""
        try:
            result = run_pipeline(url)
            _post(
                channel,
                thread_ts,
                f"✅ {prefix}*{result['title']}*\n{result['vimeo_url']}",
            )
        except Exception as exc:
            _post(channel, thread_ts, f"❌ {prefix}Pipeline failed for `{url}`:\n`{exc}`")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return "ok"


@app.route("/slack/events", methods=["POST"])
def slack_events():
    # Ignore Slack retries — the job is already running
    if request.headers.get("X-Slack-Retry-Num"):
        return jsonify({"ok": True})

    if not _verify_signature(request):
        return "Unauthorized", 401

    data = request.get_json(force=True)

    # Slack URL verification handshake
    if data.get("type") == "url_verification":
        return jsonify({"challenge": data["challenge"]})

    if data.get("type") == "event_callback":
        event = data.get("event", {})
        is_user_message = (
            event.get("type") == "message"
            and "bot_id" not in event
            and "subtype" not in event
        )
        if is_user_message:
            urls = LOOM_RE.findall(event.get("text", ""))
            if urls:
                channel = event["channel"]
                thread_ts = event.get("thread_ts") or event["ts"]
                threading.Thread(
                    target=_process,
                    args=(urls, channel, thread_ts),
                    daemon=True,
                ).start()

    # Always respond within 3 s or Slack will retry
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
