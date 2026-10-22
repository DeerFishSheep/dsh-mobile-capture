"""dsh-mobile-capture addon: 记录请求到会话目录，支持热加载规则"""
import json, os, re, time
from pathlib import Path
from mitmproxy import http

SESSION = Path(os.environ.get("CAP_SESSION", str(Path(__file__).resolve().parent)))
FLAG = Path(os.environ.get("CAP_FLAG", str(SESSION.parent / "capture.on")))
FLOWS = SESSION / "flows.jsonl"
BODIES = SESSION / "bodies"
RULES = SESSION / "rules.json"
CLIENT = SESSION.parent / "client.json"

SKIP = (".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".woff",
        ".woff2", ".ttf", ".mp4", ".m4a", ".mp3", ".m4s", ".flv")
MAXB = 4000
HOT = re.compile(r"(token|auth|cookie|sign|secret|session|ticket|passwd|key)", re.I)
_clients = {}
_rules = {"m": 0.0, "v": []}


def _save_clients():
    try:
        CLIENT.write_text(json.dumps({"clients": {ip: {"last": int(v["last"])} for ip, v in _clients.items()}}))
    except Exception:
        pass


def _peer(obj):
    try:
        peer = getattr(obj, "peername", None) or getattr(obj, "address", None)
        return peer[0] if peer else None
    except Exception:
        return None





def _load_rules():
    try:
        m = RULES.stat().st_mtime
    except FileNotFoundError:
        return []
    if m != _rules["m"]:
        try:
            _rules["v"] = json.loads(RULES.read_text()).get("rules", [])
            _rules["m"] = m
        except Exception:
            pass
    return _rules["v"]


def _client(f):
    ip = _peer(f.client_conn)
    if not ip:
        return None
    now = time.time()
    ent = _clients.setdefault(ip, {"last": 0.0})
    if now - ent["last"] > 2:
        ent["last"] = now
        _save_clients()
    return ip


def _clip(b):
    if b is None:
        return None
    if isinstance(b, bytes):
        try:
            b = b.decode("utf-8")
        except UnicodeDecodeError:
            return "<binary %dB>" % len(b)
    return b if len(b) <= MAXB else b[:MAXB] + "...<+%d chars>" % (len(b) - MAXB)


def _dump(name, content):
    BODIES.mkdir(exist_ok=True)
    p = BODIES / name
    p.write_bytes(content or b"")
    return "<full:%s>" % p.name


def _emit(**kw):
    if not FLAG.exists():
        return
    kw["t"] = time.strftime("%H:%M:%S")
    try:
        with FLOWS.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(kw, ensure_ascii=False) + "\n")
    except Exception:
        pass


def request(f: http.HTTPFlow):
    f.metadata["cip"] = _client(f)
    if f.request.path.lower().split("?")[0].endswith(SKIP):
        f.metadata["skip"] = True
        return
    for r in _load_rules():
        host, path = r.get("host"), r.get("path")
        if host and not re.search(host, f.request.pretty_host):
            continue
        if path and not re.search(path, f.request.path):
            continue
        act = r.get("action")
        if act == "block":
            f.response = http.Response.make(403, b'{"blocked":true}', {"Content-Type": "application/json"})
        elif act == "mock":
            f.response = http.Response.make(int(r.get("status", 200)),
                                            str(r.get("body", "")).encode(),
                                            {"Content-Type": r.get("ctype", "application/json")})
        elif act == "rewrite_req":
            f.request.content = str(r.get("body", "")).encode()
        else:
            continue
        f.metadata["rule"] = act
        return


def response(f: http.HTTPFlow):
    if f.metadata.get("skip") or f.response is None:
        return
    ctype = f.response.headers.get("Content-Type", "")
    body = None
    if any(x in ctype for x in ("json", "text", "xml", "javascript", "x-www-form-urlencoded")):
        raw = f.response.content or b""
        body = _clip(raw) if len(raw) <= MAXB * 4 else _dump(time.strftime("%H%M%S") + "-%d.json" % int(time.time() * 1000) % 1000, raw)
    req = None
    if f.request.content:
        req = _clip(f.request.content) if len(f.request.content) <= MAXB * 4 else "<binary %dB>" % len(f.request.content)
    _emit(m=f.request.method, host=f.request.pretty_host, path=f.request.path,
          st=f.response.status_code, ct=ctype, cip=f.metadata.get("cip"), rq=req, rs=body,
          rule=f.metadata.get("rule"))
