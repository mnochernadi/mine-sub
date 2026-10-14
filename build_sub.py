"""Build subscription.txt from your own configs (OWN_NODES secret), included as they are.
- ws configs: one copy per ws address in the source list (only the address changes).
- reality configs: one copy per reality endpoint in the source list. Address, port, flow and
  fingerprint come from the source; pbk, sid, sni, UUID/password stay yours.
"""
import base64, json, os, urllib.parse, urllib.request

UA = {"User-Agent": "mine-sub/3.0"}
SOURCE = "https://raw.githubusercontent.com/papa8274/sub-mirror/main/subscription.txt"
NAME = "mine"
PROTOCOLS = ("vless://", "vmess://", "trojan://", "ss://")


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def b64(s):
    s = s.strip().replace("-", "+").replace("_", "/")
    return base64.b64decode(s + "=" * (-len(s) % 4)).decode("utf-8", errors="ignore")


def decode_all(text):
    s = "".join(text.split())
    if s and not s.startswith(PROTOCOLS):
        try:
            return b64(s)
        except Exception:
            pass
    return text


def params(link):
    return {k: v[0] for k, v in urllib.parse.parse_qs(urllib.parse.urlsplit(link).query).items()}


def ws_addresses(lines):
    addrs = set()
    for line in lines:
        try:
            if line.startswith("vmess://"):
                d = json.loads(b64(line[8:]))
                if d.get("net") == "ws" and d.get("add"):
                    addrs.add(str(d["add"]))
            elif line.startswith(("vless://", "trojan://")):
                p = urllib.parse.urlsplit(line)
                if params(line).get("type") == "ws" and p.hostname:
                    addrs.add(p.hostname)
        except Exception:
            pass
    return sorted(addrs)


def reality_endpoints(lines):
    eps = []
    for line in lines:
        if line.startswith(("vless://", "trojan://")) and params(line).get("security") == "reality":
            p = urllib.parse.urlsplit(line)
            q = params(line)
            eps.append({"host": p.hostname, "port": p.port, "flow": q.get("flow"), "fp": q.get("fp"), "type": q.get("type")})
    return eps


def kind(link):
    if not link.startswith(("vless://", "trojan://")):
        return None
    q = params(link)
    if q.get("security") == "reality":
        return "reality"
    if q.get("type") == "ws":
        return "ws"
    return None


def set_params(query, updates):
    pairs = urllib.parse.parse_qsl(query, keep_blank_values=True)
    out, seen = [], set()
    for k, v in pairs:
        if k in updates:
            seen.add(k)
            if updates[k] is not None:
                out.append((k, updates[k]))
        else:
            out.append((k, v))
    for k, v in updates.items():
        if k not in seen and v is not None:
            out.append((k, v))
    return urllib.parse.urlencode(out, quote_via=urllib.parse.quote)


def with_endpoint(link, host, port, updates=None):
    p = urllib.parse.urlsplit(link)
    userinfo = p.netloc.rsplit("@", 1)[0]
    h = f"[{host}]" if ":" in host else host
    query = set_params(p.query, updates) if updates else p.query
    return urllib.parse.urlunsplit((p.scheme, f"{userinfo}@{h}:{port}", p.path, query, ""))


def main():
    own = [l.strip() for l in os.environ.get("OWN_NODES", "").splitlines() if kind(l.strip())]
    src_lines = [l.strip() for l in decode_all(fetch(SOURCE)).splitlines() if l.strip()]
    ws_addrs = ws_addresses(src_lines)
    rel_eps = reality_endpoints(src_lines)
    print("own:", len(own), "| ws addresses:", len(ws_addrs), "| reality endpoints:", len(rel_eps))

    bases, seen = [], set()

    def add(link):
        if link not in seen:
            seen.add(link)
            bases.append(link)

    for link in own:
        add(link.split("#", 1)[0])
    for link in own:
        k = kind(link)
        if k == "ws":
            port = urllib.parse.urlsplit(link).port
            for a in ws_addrs:
                add(with_endpoint(link, a, port))
        elif k == "reality":
            is_vless = link.startswith("vless://")
            own_type = params(link).get("type")
            for ep in rel_eps:
                if ep["type"] != own_type:
                    continue
                upd = {}
                if ep["fp"]:
                    upd["fp"] = ep["fp"]
                if is_vless:
                    upd["flow"] = ep["flow"]
                add(with_endpoint(link, ep["host"], ep["port"], upd))

    out = [f"{b}#{urllib.parse.quote(f'{NAME} {i}', safe='')}" for i, b in enumerate(bases, 1)]
    open("subscription.txt", "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("written", len(out), "configs")


if __name__ == "__main__":
    main()
