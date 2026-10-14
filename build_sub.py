"""Build subscription.txt from your ws configs (OWN_NODES secret), included as they are.
Each ws config gets one copy per ws address in the source list; only the address changes.
Reality configs are not included.
"""
import base64, json, os, urllib.parse, urllib.request

UA = {"User-Agent": "mine-sub/4.0"}
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


def is_my_ws(link):
    return link.startswith(("vless://", "trojan://")) and params(link).get("type") == "ws"


def with_address(link, addr):
    p = urllib.parse.urlsplit(link)
    userinfo = p.netloc.rsplit("@", 1)[0]
    port = p.port
    a = f"[{addr}]" if ":" in addr else addr
    return urllib.parse.urlunsplit((p.scheme, f"{userinfo}@{a}:{port}", p.path, p.query, ""))


def main():
    own = [l.strip() for l in os.environ.get("OWN_NODES", "").splitlines() if is_my_ws(l.strip())]
    src_lines = [l.strip() for l in decode_all(fetch(SOURCE)).splitlines() if l.strip()]
    addrs = ws_addresses(src_lines)
    print("own ws:", len(own), "| ws addresses:", len(addrs))

    bases, seen = [], set()

    def add(link):
        if link not in seen:
            seen.add(link)
            bases.append(link)

    for link in own:
        add(link.split("#", 1)[0])
    for link in own:
        for a in addrs:
            add(with_address(link, a))

    out = [f"{b}#{urllib.parse.quote(f'{NAME} {i}', safe='')}" for i, b in enumerate(bases, 1)]
    open("subscription.txt", "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("written", len(out), "configs")


if __name__ == "__main__":
    main()
