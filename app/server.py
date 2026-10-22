#!/usr/bin/env python3
"""mobile-capture: 本地抓包服务（mitmproxy + 网页控制台）"""
import atexit, http.server, io, json, os, shutil, signal, socket, subprocess, threading, time, urllib.parse
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("CAP_HOME", str(Path.home() / ".mobilecapture")))
DATA = ROOT / "data"
SESSION = DATA / "session"
FLOWS = SESSION / "flows.jsonl"
BODIES = SESSION / "bodies"
META = SESSION / "meta.json"
CLIENT = DATA / "client.json"
CAPTURE = DATA / "capture.on"
ADDON = BASE / "addon.py"
UI = BASE / "ui.html"
MITMDUMP = (os.environ.get("CAP_MITMDUMP")
            or shutil.which("mitmdump")
            or "/opt/homebrew/bin/mitmdump")
CA = Path.home() / ".mitmproxy" / "mitmproxy-ca-cert.cer"
PROXY_PORT = int(os.environ.get("CAP_PROXY_PORT", "8080"))
WEB_PORT = int(os.environ.get("CAP_WEB_PORT", "8899"))

state = {"seq": 0, "flows": [], "proc": None}


def lan_ip():
    for iface in ("en0", "en1"):
        try:
            ip = subprocess.check_output(["ipconfig", "getifaddr", iface], text=True).strip()
            if ip:
                return ip
        except Exception:
            pass
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


def port_busy(port):
    s = socket.socket()
    s.settimeout(0.3)
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    finally:
        s.close()


def new_session():
    if SESSION.exists():
        shutil.rmtree(SESSION, ignore_errors=True)
    SESSION.mkdir(parents=True, exist_ok=True)
    BODIES.mkdir(exist_ok=True)
    FLOWS.touch()
    META.write_text(json.dumps({"started": time.strftime("%Y-%m-%d %H:%M:%S")}, ensure_ascii=False))
    if CLIENT.exists():
        CLIENT.unlink()
    CAPTURE.touch()
    state["flows"], state["seq"] = [], 0


def drop_session():
    shutil.rmtree(SESSION, ignore_errors=True)
    if CLIENT.exists():
        CLIENT.unlink()


def start_proxy():
    if state["proc"] and state["proc"].poll() is None:
        return True
    if port_busy(PROXY_PORT):
        state["external"] = True
        return True
    env = dict(os.environ, CAP_SESSION=str(SESSION), CAP_FLAG=str(CAPTURE))
    state["proc"] = subprocess.Popen(
        [MITMDUMP, "--listen-host", "0.0.0.0", "--listen-port", str(PROXY_PORT),
         "-s", str(ADDON), "--set", "block_global=false", "--set", "flow_detail=0"],
        cwd=str(SESSION), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(1.5)
    return state["proc"].poll() is None


def stop_proxy():
    p = state["proc"]
    if p and p.poll() is None:
        p.terminate()
        try:
            p.wait(3)
        except Exception:
            p.kill()


def tailer():
    off = 0
    while True:
        try:
            if FLOWS.exists():
                if FLOWS.stat().st_size < off:
                    off, state["flows"] = 0, []
                with FLOWS.open("rb") as fh:
                    fh.seek(off)
                    data = fh.read()
                    off = fh.tell()
                for line in data.splitlines():
                    if not line.strip():
                        continue
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    state["seq"] += 1
                    obj["_s"] = state["seq"]
                    state["flows"].append(obj)
                if len(state["flows"]) > 400:
                    state["flows"] = state["flows"][-400:]
        except Exception:
            pass
        time.sleep(0.6)


def client_info():
    try:
        c = json.loads(CLIENT.read_text())
    except Exception:
        return {"ip": None, "ago": None}
    return {"ip": c.get("ip"), "ago": int(time.time()) - int(c.get("ts", 0))}


def compact(f):
    return {
        "_s": f.get("_s"), "t": f.get("t"), "m": f.get("m"), "host": f.get("host"),
        "path": (f.get("path") or "")[:300], "st": f.get("st"), "ct": f.get("ct"),
        "cip": f.get("cip"), "rs": (f.get("rs") or "")[:800], "rq": (f.get("rq") or "")[:400],
    }


class H(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        if u.path in ("/", "/index.html"):
            return self._send(200, UI.read_bytes(), "text/html; charset=utf-8")
        if u.path == "/ca":
            if not CA.exists():
                return self._send(404, json.dumps({"error": "CA 未生成，先让代理跑一次"}))
            return self._send(200, CA.read_bytes(), "application/x-x509-ca-cert",
                              {"Content-Disposition": 'attachment; filename="mobilecapture-ca.cer"'})
        if u.path == "/api/status":
            cl = client_info()
            return self._send(200, json.dumps({
                "ip": lan_ip(), "proxyPort": PROXY_PORT, "webPort": WEB_PORT,
                "running": port_busy(PROXY_PORT), "capture": CAPTURE.exists(),
                "client": cl, "total": state["seq"],
                "onboarding": cl["ip"] is None,
                "session": json.loads(META.read_text()) if META.exists() else {},
            }))
        if u.path == "/api/flows":
            after = int(q.get("after", ["0"])[0])
            return self._send(200, json.dumps([compact(f) for f in state["flows"] if f.get("_s", 0) > after]))
        if u.path == "/api/capture":
            on = q.get("on", ["1"])[0] == "1"
            if on:
                CAPTURE.touch()
            elif CAPTURE.exists():
                CAPTURE.unlink()
            return self._send(200, json.dumps({"capture": CAPTURE.exists()}))
        if u.path == "/api/clear":
            new_session()
            return self._send(200, json.dumps({"ok": True}))
        if u.path == "/api/qr":
            import qrcode
            img = qrcode.make(q.get("t", [""])[0])
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return self._send(200, buf.getvalue(), "image/png")
        if u.path == "/api/quit":
            self._send(200, json.dumps({"ok": True}))
            threading.Thread(target=shutdown, daemon=True).start()
            return
        self._send(404, json.dumps({"error": "not found"}))


def shutdown():
    stop_proxy()
    drop_session()
    os._exit(0)


def main():
    url = "http://%s:%d/" % (lan_ip(), WEB_PORT)
    if port_busy(WEB_PORT):
        print("已在运行: %s" % url)
        if not os.environ.get("NO_OPEN"):
            subprocess.run(["open", url])
        return
    DATA.mkdir(parents=True, exist_ok=True)
    new_session()
    atexit.register(lambda: (stop_proxy(), drop_session()))
    threading.Thread(target=tailer, daemon=True).start()
    ok = start_proxy()
    srv = http.server.ThreadingHTTPServer(("0.0.0.0", WEB_PORT), H)
    print("抓包服务: proxy=%d web=%d started=%s" % (PROXY_PORT, WEB_PORT, ok))
    print("控制台: %s" % url)
    if not os.environ.get("NO_OPEN"):
        subprocess.run(["open", url])
    signal.signal(signal.SIGTERM, lambda *a: shutdown())
    srv.serve_forever()


if __name__ == "__main__":
    main()
