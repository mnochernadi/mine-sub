"""Build subscription.txt (ws only, no reality).

Template: every ws config in the papa8274 source list. Its address, port, security (TLS or none),
fingerprint and other settings are kept.
Overrides from your own ws configs (OWN_NODES secret), matched by protocol (vless/trojan):
credential (UUID or password), host, path, and sni (only when the template uses TLS).
Output: one config per (template, own config) pair, named mine N.
"""
import base64, os, urllib.parse, urllib.request

UA = {"User-Agent": "mine-sub/6.0"}
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


def qparams(link):
    return dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(link).query, keep_blank_values=True))


def proto(link):
    return link.split("://", 1)[0]


def is_ws(link):
    return link.startswith(("vless://", "trojan://")) and qparams(link).get("type") == "ws"


def cred(link):
    return urllib.parse.urlsplit(link).netloc.rsplit("@", 1)[0]


def main():
    own = [l.strip() for l in os.environ.get("OWN_NODES", "").splitlines() if is_ws(l.strip())]
    templates, seen = [], set()
    for l in decode_all(fetch(SOURCE)).splitlines():
        l = l.strip()
        if is_ws(l):
            base = l.split("#", 1)[0]
            if base not in seen:
                seen.add(base)
                templates.append(base)
    print("own ws:", len(own), "| papa ws templates:", len(templates))

    out, done = [], set()
    for t in templates:
        tp = urllib.parse.urlsplit(t)
        tq = qparams(t)
        for o in own:
            if proto(o) != proto(t):
                continue
            oq = qparams(o)
            q = dict(tq)
            for k in ("host", "path"):
                if k in oq:
                    q[k] = oq[k]
            if tq.get("security") == "tls":
                q["sni"] = oq.get("sni") or oq.get("host") or tp.hostname or ""
            hostport = tp.netloc.rsplit("@", 1)[1]
            link = urllib.parse.urlunsplit(
                (tp.scheme, f"{cred(o)}@{hostport}", "", urllib.parse.urlencode(q, quote_via=urllib.parse.quote), "")
            )
            if link not in done:
                done.add(link)
                out.append(link)

    named = [f"{b}#{urllib.parse.quote(f'{NAME} {i}', safe='')}" for i, b in enumerate(out, 1)]
    open("subscription.txt", "w", encoding="utf-8").write("\n".join(named) + "\n")
    print("written", len(named), "configs")


if __name__ == "__main__":
    main()
