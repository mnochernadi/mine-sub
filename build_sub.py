"""Build subscription.txt (ws only).

Your own ws configs (OWN_NODES secret) are the templates. Everything stays yours (protocol,
port, security/TLS, host, path, sni, fingerprint, UUID/password). Only the address is replaced
with each address found in the papa8274 source list (ws entries).
Output: one config per (own config, address) pair, named mine N.
"""
import base64, os, urllib.parse, urllib.request

UA = {"User-Agent": "mine-sub/7.0"}
SOURCE = "https://raw.githubusercontent.com/papa8274/sub-mirror/main/subscription.txt"
NAME = "mine"
PROTOCOLS = ("vless://", "vmess://", "trojan://", "ss://")


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
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


def qtype(link):
    return dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(link).query, keep_blank_values=True)).get("type")


def is_ws(link):
    return link.startswith(("vless://", "trojan://")) and qtype(link) == "ws"


def is_ws_tls(link):
    return is_ws(link) and qparam(link, "security") == "tls"


def qparam(link, key):
    return dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(link).query, keep_blank_values=True)).get(key)


def source_addresses(text):
    addrs = []
    for line in decode_all(text).splitlines():
        line = line.strip()
        if is_ws(line):
            host = urllib.parse.urlsplit(line).hostname
            if host and host not in addrs:
                addrs.append(host)
    return addrs


def with_address(own, addr):
    p = urllib.parse.urlsplit(own)
    userinfo, hostport = p.netloc.rsplit("@", 1)
    port = hostport.rsplit(":", 1)[1]
    a = f"[{addr}]" if ":" in addr else addr
    return urllib.parse.urlunsplit((p.scheme, f"{userinfo}@{a}:{port}", p.path, p.query, ""))


def main():
    own = []
    for l in os.environ.get("OWN_NODES", "").splitlines():
        l = l.strip()
        if is_ws_tls(l):
            base = l.split("#", 1)[0]
            if base not in own:
                own.append(base)
    addrs = source_addresses(fetch(SOURCE))
    print("own ws:", len(own), "| source addresses:", len(addrs))

    out, done = [], set()
    for o in own:
        for a in addrs:
            link = with_address(o, a)
            if link not in done:
                done.add(link)
                out.append(link)

    named = [f"{b}#{urllib.parse.quote(f'{NAME} {i}', safe='')}" for i, b in enumerate(out, 1)]
    open("subscription.txt", "w", encoding="utf-8").write("\n".join(named) + "\n")
    print("written", len(named), "configs")


if __name__ == "__main__":
    main()
