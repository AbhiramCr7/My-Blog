#!/usr/bin/env python3
"""Technical SVG diagrams for the Burp interception article. Dark lab, no decoration."""
from pathlib import Path
OUT = Path(__file__).resolve().parent.parent / "public" / "assets" / "burp"
OUT.mkdir(parents=True, exist_ok=True)

BG, INK, DIM, RED, LINE, BOX, OK = "#14060a", "#ffe8ea", "#c9a0a6", "#ff5468", "#5a2a32", "#241014", "#7ee2a8"

def svg(w, h, body, title=""):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-label="{title}">
<rect width="{w}" height="{h}" fill="{BG}"/>
{body}
</svg>'''

def box(x, y, w, h, title, sub="", kind=""):
    stroke = RED if kind == "burp" else OK if kind == "ok" else LINE
    sw = 2 if kind else 1.5
    t = f'<text x="{x+w/2}" y="{y+h/2-6}" text-anchor="middle" fill="{INK}" font-family="ui-sans-serif,system-ui,sans-serif" font-size="15" font-weight="700">{title}</text>'
    s = f'<text x="{x+w/2}" y="{y+h/2+14}" text-anchor="middle" fill="{DIM}" font-family="ui-sans-serif,system-ui,sans-serif" font-size="12">{sub}</text>' if sub else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{BOX}" stroke="{stroke}" stroke-width="{sw}"/>{t}{s}'

def label(x, y, text, color=DIM, size=12, anchor="middle", weight="400"):
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" fill="{color}" font-family="ui-sans-serif,system-ui,sans-serif" font-size="{size}" font-weight="{weight}">{text}</text>'

def arrow(x1, y1, x2, y2, color=RED):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="2" marker-end="url(#ah)"/>'

def defs():
    return f'''<defs>
  <marker id="ah" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
    <path d="M0,0 L8,4 L0,8 z" fill="{RED}"/>
  </marker>
</defs>'''

def title(t):
    return label(500, 28, t.upper(), RED, 13, "middle", "700")

files = {}

files["d-normal-vs-burp.svg"] = svg(1000, 380, defs()+title("Normal HTTPS vs Burp HTTPS")+
box(80, 90, 160, 72, "Browser")+
box(80, 250, 160, 72, "shop.test", "real cert")+
arrow(160, 162, 160, 250)+
label(200, 215, "one TLS session", DIM, 12, "start")+
label(160, 70, "NORMAL", INK, 12, "middle", "700")+
box(480, 70, 160, 64, "Browser")+
box(480, 168, 160, 70, "Burp", "TLS endpoint", "burp")+
box(480, 272, 160, 64, "shop.test", "real cert")+
arrow(560, 134, 560, 168)+
arrow(560, 238, 560, 272)+
label(590, 158, "TLS A", RED, 12, "start")+
label(590, 262, "TLS B", OK, 12, "start")+
label(560, 52, "BURP", INK, 12, "middle", "700")+
label(500, 360, "No single Browser → shop.test TLS session once Burp terminates TLS.", DIM, 13),
"Side-by-side: one TLS hop versus two independent TLS sessions")

files["d-two-tls.svg"] = svg(1000, 420, defs()+title("Two independent TLS sessions")+
box(40, 80, 180, 80, "Browser")+
box(410, 80, 180, 80, "Burp Proxy", "terminates + originates", "burp")+
box(780, 80, 180, 80, "shop.test")+
arrow(220, 110, 410, 110)+
arrow(590, 110, 780, 110)+
label(315, 98, "TLS SESSION A", RED, 11)+
label(315, 142, "Burp-generated host cert", DIM, 11)+
label(685, 98, "TLS SESSION B", OK, 11)+
label(685, 142, "real shop.test cert", DIM, 11)+
f'<rect x="250" y="210" width="500" height="150" rx="14" fill="{BOX}" stroke="{RED}" stroke-width="1.5"/>'+
label(500, 240, "HTTP plaintext  ·  only here", INK, 15, "middle", "700")+
label(500, 268, "inspect  ·  modify  ·  intercept pause  ·  history", DIM, 13)+
label(500, 300, "Browser never holds session B. Server never holds session A.", DIM, 12)+
label(500, 328, "Burp does not decrypt shop.test’s original end-to-end session.", DIM, 12)+
arrow(500, 160, 500, 210),
"Browser to Burp TLS A, plaintext in Burp, Burp to server TLS B")

files["d-connect.svg"] = svg(1000, 360, defs()+title("Before TLS: CONNECT then handshake")+
box(60, 80, 200, 70, "1. TCP to :8080")+
box(400, 80, 200, 70, "2. CONNECT", "shop.test:443")+
box(740, 80, 200, 70, "3. 200 Established")+
arrow(260, 115, 400, 115)+
arrow(600, 115, 740, 115)+
box(60, 220, 200, 70, "4. ClientHello", "SNI = shop.test")+
box(400, 220, 200, 70, "5. Host cert", "signed by Burp CA", "burp")+
box(740, 220, 200, 70, "6. TLS A up", "session keys A")+
arrow(260, 255, 400, 255)+
arrow(600, 255, 740, 255)+
label(500, 340, "CONNECT names the hop. SNI names the cert. Cert is not sent before the destination is known.", DIM, 13),
"CONNECT then TLS ClientHello with SNI then Burp host certificate")

files["d-ca-tree.svg"] = svg(1000, 340, defs()+title("One installation CA, many per-host certificates")+
box(400, 50, 200, 70, "Burp CA", "self-signed, once per install", "burp")+
arrow(500, 120, 170, 180)+
arrow(500, 120, 500, 180)+
arrow(500, 120, 830, 180)+
box(70, 180, 200, 80, "shop.test cert", "SAN = shop.test")+
box(400, 180, 200, 80, "api.shop.test", "SAN = api.shop.test")+
box(730, 180, 200, 80, "auth.shop.test", "SAN = auth.shop.test")+
label(500, 300, "The CA is the signer. The host certificate is not the CA.", DIM, 14),
"Burp CA signs per-host certificates for each destination")

files["d-trust.svg"] = svg(1000, 360, defs()+title("Two separate trust relationships")+
box(80, 80, 200, 70, "Browser")+
arrow(180, 150, 180, 200)+
label(300, 180, "validates hostname, chain, signature, trust anchor", DIM, 12, "start")+
box(80, 200, 200, 70, "Host cert", "issuer = Burp CA")+
arrow(180, 270, 180, 300)+
box(80, 300, 200, 50, "Trust store", "Burp CA installed")+
box(560, 80, 200, 70, "Burp", "", "burp")+
arrow(660, 150, 660, 200)+
label(780, 180, "validates upstream cert (configurable)", DIM, 12, "start")+
box(560, 200, 200, 70, "Real cert", "public CA / private PKI")+
arrow(660, 270, 660, 300)+
box(560, 300, 200, 50, "shop.test", "server private key stays here")+
label(500, 48, "", DIM, 1),
"Browser trusts Burp CA; Burp validates the real server certificate")

files["d-keys.svg"] = svg(1000, 300, defs()+title("Which keys are involved")+
box(40, 70, 220, 160, "CA private key", "signs host certs", "burp")+
box(280, 70, 220, 160, "Host key pair", "TLS server to browser")+
box(520, 70, 220, 160, "Session keys A / B", "encrypt HTTP records")+
box(760, 70, 200, 160, "shop.test key", "never in Burp")+
label(500, 270, "Burp does not possess the origin server’s private key.", DIM, 14),
"CA key, per-host key, TLS session keys, origin private key stays on server")

files["d-request.svg"] = svg(1000, 520, defs()+title("Request lifecycle")+
"".join(
    f'<rect x="40" y="{50+i*38}" width="36" height="28" rx="14" fill="{RED}"/><text x="58" y="{70+i*38}" text-anchor="middle" fill="#fff" font-size="12" font-family="ui-sans-serif,system-ui,sans-serif" font-weight="700">{i+1}</text>'
    f'<text x="92" y="{70+i*38}" fill="{INK}" font-size="13" font-family="ui-sans-serif,system-ui,sans-serif">{t}</text>'
    for i, t in enumerate([
        "Browser opens TCP to 127.0.0.1:8080",
        "CONNECT shop.test:443 HTTP/1.1",
        "Burp: 200 Connection Established",
        "ClientHello (SNI=shop.test, ALPN…)",
        "Burp presents per-host cert signed by Burp CA",
        "Browser validates chain → TLS session A",
        "Encrypted HTTP on session A",
        "Burp decrypts — HTTP plaintext in process memory",
        "Inspect / modify / intercept pause",
        "Burp opens TLS session B to shop.test",
        "Encrypted HTTP on session B",
        "Origin processes the request",
    ])
), "Numbered request path from CONNECT to upstream TLS")

files["d-response.svg"] = svg(1000, 300, defs()+title("Response lifecycle")+
box(40, 90, 160, 80, "shop.test")+
box(280, 90, 160, 80, "TLS B", "decrypt in Burp")+
box(520, 90, 160, 80, "HTTP", "inspect / modify", "burp")+
box(760, 90, 160, 80, "TLS A", "browser")+
arrow(200, 130, 280, 130)+
arrow(440, 130, 520, 130)+
arrow(680, 130, 760, 130)+
label(500, 230, "Same buffer, opposite direction. Plaintext exists only after session B is terminated.", DIM, 13),
"Server response decrypted on session B then re-encrypted on session A")

files["d-passthrough.svg"] = svg(1000, 260, defs()+title("TLS passthrough — no termination")+
box(80, 80, 180, 80, "Browser")+
box(410, 80, 180, 80, "Burp", "forwards TLS records", "burp")+
box(740, 80, 180, 80, "shop.test")+
arrow(260, 120, 410, 120)+
arrow(590, 120, 740, 120)+
label(500, 200, "No HTTP visibility. No Intercept. No history of bodies. Ciphertext in, ciphertext out.", DIM, 13)+
label(335, 70, "encrypted", DIM, 11)+
label(665, 70, "encrypted", DIM, 11),
"TLS passthrough forwards encrypted records without decrypting")

files["d-pinning.svg"] = svg(1000, 300, defs()+title("Certificate pinning vs CA trust")+
box(60, 70, 400, 180, "Normal trust", "signed by a trusted CA → accept")+
box(540, 70, 400, 180, "Pinning", "also: does SPKI / cert match the pin?")+
label(500, 280, "Burp CA trusted + pin mismatch = handshake failure. Installing the CA is not enough.", DIM, 13),
"Pinning rejects Burp host certificates even if the CA is trusted")

files["d-h2.svg"] = svg(1000, 280, defs()+title("HTTP/1.1 vs HTTP/2 on the wire")+
box(60, 70, 420, 160, "HTTP/1.1", "GET /account HTTP/1.1   Host: shop.test")+
box(520, 70, 420, 160, "HTTP/2", ":method GET   :path /account   :authority shop.test")+
label(500, 260, "ALPN in ClientHello advertises h2 / http/1.1. Burp can speak either hop independently.", DIM, 13),
"HTTP/1.1 request line versus HTTP/2 pseudo-headers")

files["d-invisible.svg"] = svg(1000, 300, defs()+title("Invisible proxying — no CONNECT")+
box(40, 70, 200, 90, "Thick client", "not proxy-aware")+
box(400, 70, 200, 90, "Burp listener", "invisible mode", "burp")+
box(760, 70, 200, 90, "Origin")+
arrow(240, 115, 400, 115)+
arrow(600, 115, 760, 115)+
label(500, 200, "DNS/hosts points the name at Burp. TLS starts immediately. Hostname from SNI or Host.", DIM, 13)+
label(500, 228, "No CONNECT. Destination for outbound must not loop back to the same listener.", DIM, 13),
"Non-proxy-aware client connects directly to an invisible Burp listener")

files["d-mtls.svg"] = svg(1000, 280, defs()+title("mTLS: client certificate on the upstream hop")+
box(60, 80, 180, 80, "Browser / client")+
box(410, 80, 180, 80, "Burp", "client cert for origin", "burp")+
box(760, 80, 180, 80, "API", "requests client cert")+
arrow(240, 120, 410, 120)+
arrow(590, 120, 760, 120)+
label(500, 210, "Server proves itself with its cert. Client must also prove itself.", DIM, 13)+
label(500, 238, "Burp presents a configured PKCS#12 / PKCS#11 cert when the origin asks.", DIM, 13),
"Mutual TLS with Burp presenting a client certificate upstream")

files["d-master.svg"] = svg(1000, 560, defs()+title("Master architecture")+
box(40, 70, 160, 70, "Browser")+
label(120, 160, "CONNECT shop.test:443", DIM, 11)+
arrow(120, 140, 120, 190)+
f'<rect x="300" y="60" width="400" height="430" rx="16" fill="{BOX}" stroke="{RED}" stroke-width="2"/>'+
label(500, 90, "BURP SUITE", INK, 16, "middle", "700")+
label(500, 114, "Proxy listener  ·  127.0.0.1:8080", DIM, 12)+
box(360, 140, 280, 50, "Burp CA  →  per-host cert", "", "burp")+
box(360, 210, 280, 50, "TLS session A  (browser)")+
box(360, 280, 280, 50, "HTTP plaintext  inspect/modify", "", "burp")+
box(360, 350, 280, 50, "TLS session B  (upstream)")+
label(500, 430, "Does not hold shop.test private key", DIM, 12)+
label(500, 454, "Browser validates host cert  ·  Burp validates origin cert", DIM, 12)+
arrow(120, 250, 300, 250)+
arrow(700, 375, 820, 375)+
box(800, 340, 160, 70, "shop.test")+
label(880, 430, "real certificate", DIM, 11)+
label(880, 448, "real private key", DIM, 11),
"Full Burp HTTPS interception architecture with two TLS sessions")

files["d-packet.svg"] = svg(1000, 480, defs()+title("Packet flow 1–12")+
"".join(
    f'<rect x="40" y="{48+i*34}" width="28" height="24" rx="12" fill="{RED}"/><text x="54" y="{65+i*34}" text-anchor="middle" fill="#fff" font-size="11" font-family="ui-sans-serif,system-ui,sans-serif" font-weight="700">{i+1}</text>'
    f'<text x="84" y="{65+i*34}" fill="{INK}" font-size="13" font-family="ui-sans-serif,system-ui,sans-serif">{t}</text>'
    for i, t in enumerate([
        "CONNECT shop.test:443",
        "200 Connection Established",
        "ClientHello + SNI (+ ALPN)",
        "Burp per-host certificate (issuer = Burp CA)",
        "TLS handshake completes → session A",
        "Encrypted HTTP request on A",
        "Burp decrypts to HTTP",
        "Forward over new TLS session B",
        "Origin HTTP response on B",
        "Burp decrypts response",
        "Re-encrypt on session A",
        "Browser consumes the response",
    ])
), "Twelve-step packet flow of HTTPS through Burp")

for name, content in files.items():
    (OUT / name).write_text(content)
print("wrote", len(files), "svgs")
