"""Build subscription.txt for the ws-based scanning workflow.

Every ws config in the source list (papa8274) is the template: its address, port, security
(TLS or none), sni, host, path, fingerprint and other settings are copied as they are.
Each of your own ws configs (OWN_NODES secret) supplies the credential (UUID or password).
Result: for every source ws config, one copy per own credential. The whole list is rebuilt on
every run and renamed mine N.
"""
import base64, json, os, urllib.parse, urllib.request

UA = {"User-Agent": "mine-sub/5.0"}
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


def params(link):
    return {k: v[0] for k, v in urllib.parse.parse_qs(urllib.parse.urlsplit(link).query).items()}


def is_ws(link):
    return link.startswith(("vless://", "trojan://")) and params(link).get("type") == "ws"


def credential(link):
    """Return the user part (UUID for vless, password for trojan)."""
    return urllib.parse.urlsplit(link).netloc.rsplit("@", 1)[0]


def with_credential(template, cred):
    p = urllib.parse.urlsplit(template)
    host_port = p.netloc.rsplit("@", 1)[1]
    return urllib.parse.urlunsplit((p.scheme, f"{cred}@{host_port}", p.path, p.query, ""))


def main():
    own_creds = []
    for l in os.environ.get("OWN_NODES", "").splitlines():
        l = l.strip()
        if is_ws(l):
            c = credential(l)
            if c and c not in own_creds:
                own_creds.append(c)
    templates = []
    seen = set()
    for l in decode_all(fetch(SOURCE)).splitlines():
        l = l.strip()
        if is_ws(l):
            key = l.split("#", 1)[0]
            if key not in seen:
                seen.add(key)
                templates.append(l.split("#", 1)[0])
    print("own credentials:", len(own_creds), "| ws templates:", len(templates))

    out_bases, done = [], set()
    for t in templates:
        for c in own_creds:
            link = with_credential(t, c)
            if link not in done:
                done.add(link)
                out_bases.append(link)

    out = [f"{b}#{urllib.parse.quote(f'{NAME} {i}', safe='')}" for i, b in enumerate(out_bases, 1)]
    open("subscription.txt", "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("written", len(out), "configs")


if __name__ == "__main__":
    main()
