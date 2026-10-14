"""Adapt your ws configs to the ws addresses of the source list.
Your configs come from the OWN_NODES secret. For each of your ws configs, one copy is made per
ws address in the source; only the address changes, UUID/host/sni/path stay yours.
Output: subscription.txt (plain text), rebuilt every 20 minutes.
"""
import base64, json, os, urllib.parse, urllib.request

UA = {"User-Agent": "mine-sub/1.0"}
SOURCE = "https://raw.githubusercontent.com/papa8274/sub-mirror/main/subscription.txt"
NAME = "mine"


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def b64(s):
    s = s.strip().replace("-", "+").replace("_", "/")
    return base64.b64decode(s + "=" * (-len(s) % 4)).decode("utf-8", errors="ignore")


def decode_all(text):
    s = "".join(text.split())
    if s and not s.startswith(("vless://", "vmess://", "trojan://", "ss://")):
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


def is_my_ws(link):
    if not link.startswith(("vless://", "trojan://")):
        return False
    return urllib.parse.parse_qs(urllib.parse.urlsplit(link).query).get("type", [""])[0] == "ws"


def with_address(link, addr):
    p = urllib.parse.urlsplit(link)
    userinfo, hostport = p.netloc.rsplit("@", 1)
    port = hostport.rsplit(":", 1)[1]
    a = f"[{addr}]" if ":" in addr else addr
    query = p.query
    q = urllib.parse.parse_qs(query)
    if q.get("security", [""])[0] == "tls" and "sni" not in q and p.hostname:
        query += f"&sni={p.hostname}"
    return urllib.parse.urlunsplit((p.scheme, f"{userinfo}@{a}:{port}", p.path, query, ""))


def main():
    own = [l.strip() for l in os.environ.get("OWN_NODES", "").splitlines() if is_my_ws(l.strip())]
    addrs = ws_addresses(fetch(SOURCE))
    print("own ws configs:", len(own), "| source ws addresses:", len(addrs))

    bases, seen = [], set()

    def add(base):
        if base not in seen:
            seen.add(base)
            bases.append(base)

    for link in own:
        add(link.split("#", 1)[0])
    for link in own:
        for addr in addrs:
            try:
                add(with_address(link, addr))
            except Exception:
                pass

    out = [f"{b}#{urllib.parse.quote(f'{NAME} {i}', safe='')}" for i, b in enumerate(bases, 1)]
    open("subscription.txt", "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("written", len(out), "configs")


if __name__ == "__main__":
    main()
