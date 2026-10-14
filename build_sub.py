"""Build subscription.txt from your own configs.
Your configs come from the OWN_NODES secret and are included as they are. Then:
- each ws config gets one copy per ws address in the source list (only the address changes);
- each reality config gets one copy per reality endpoint in the source list (only host and port change).
Keys (pbk, sid), UUID/password, sni, host and path stay yours.
Note: reality only works on servers that hold your private key, so most reality copies will not connect.
"""
import base64, json, os, re, urllib.parse, urllib.request

UA = {"User-Agent": "mine-sub/2.0"}
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


def ws_addresses(text):
    addrs = set()
    for line in decode_all(text).splitlines():
        line = line.strip()
        try:
            if line.startswith("vmess://"):
                d = json.loads(b64(line[8:]))
                if d.get("net") == "ws" and d.get("add"):
                    addrs.add(str(d["add"]))
            elif line.startswith(("vless://", "trojan://")):
                p = urllib.parse.urlsplit(line)
                if urllib.parse.parse_qs(p.query).get("type", [""])[0] == "ws" and p.hostname:
                    addrs.add(p.hostname)
        except Exception:
            pass
    return sorted(addrs)


def reality_endpoints(text):
    eps = set()
    for line in decode_all(text).splitlines():
        if "security=reality" in line:
            m = re.search(r"@(\[[^\]]+\]|[^:/?#]+):(\d+)", line)
            if m:
                eps.add((m.group(1).strip("[]"), m.group(2)))
    return sorted(eps)


def kind(link):
    if not link.startswith(("vless://", "trojan://")):
        return None
    q = urllib.parse.parse_qs(urllib.parse.urlsplit(link).query)
    if q.get("security", [""])[0] == "reality":
        return "reality"
    if q.get("type", [""])[0] == "ws":
        return "ws"
    return None


def with_endpoint(link, host, port):
    p = urllib.parse.urlsplit(link)
    userinfo = p.netloc.rsplit("@", 1)[0]
    h = f"[{host}]" if ":" in host else host
    return urllib.parse.urlunsplit((p.scheme, f"{userinfo}@{h}:{port}", p.path, p.query, ""))


def main():
    own = [l.strip() for l in os.environ.get("OWN_NODES", "").splitlines() if kind(l.strip())]
    text = fetch(SOURCE)
    ws_addrs = ws_addresses(text)
    rel_eps = reality_endpoints(text)
    print("own configs:", len(own), "| ws addresses:", len(ws_addrs), "| reality endpoints:", len(rel_eps))

    bases, seen = [], set()

    def add(base):
        if base not in seen:
            seen.add(base)
            bases.append(base)

    for link in own:
        add(link.split("#", 1)[0])
    for link in own:
        k = kind(link)
        port = urllib.parse.urlsplit(link).port
        if k == "ws":
            targets = [(a, port) for a in ws_addrs]
        elif k == "reality":
            targets = rel_eps
        else:
            targets = []
        for host, p in targets:
            try:
                add(with_endpoint(link, host, p))
            except Exception:
                pass

    out = [f"{b}#{urllib.parse.quote(f'{NAME} {i}', safe='')}" for i, b in enumerate(bases, 1)]
    open("subscription.txt", "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("written", len(out), "configs")


if __name__ == "__main__":
    main()
