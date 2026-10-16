#!/usr/bin/env python3
"""Hand-drawn-style traffic diagrams for the Burp proxy post. No photos, no AI art."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "public" / "assets" / "burp"
OUT.mkdir(parents=True, exist_ok=True)

CSS = """
:root { --bg:#14060a; --ink:#ffe8ea; --dim:#c9a0a6; --red:#ff5468; --line:#5a2a32; --box:#241014; --ok:#7ee2a8; }
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--ink);font-family:ui-sans-serif,system-ui,-apple-system,sans-serif}
.wrap{padding:28px 32px 24px;width:1000px}
h1{font-size:15px;letter-spacing:.16em;text-transform:uppercase;color:var(--red);font-weight:700;margin-bottom:18px}
.row{display:flex;align-items:stretch;gap:16px;justify-content:center}
.col{display:flex;flex-direction:column;align-items:center;gap:10px}
.box{background:var(--box);border:1.5px solid var(--line);border-radius:14px;padding:16px 18px;min-width:170px;text-align:center}
.box b{display:block;font-size:16px;margin-bottom:4px}
.box small{color:var(--dim);font-size:12px;line-height:1.4}
.box.red{border-color:var(--red);box-shadow:0 0 0 1px rgb(255 84 104 / .25)}
.box.ok{border-color:var(--ok)}
.arrow{align-self:center;color:var(--red);font-size:28px;font-weight:700;letter-spacing:-2px}
.note{margin-top:16px;text-align:center;color:var(--dim);font-size:13px;line-height:1.45}
.steps{display:grid;gap:8px;margin-top:4px}
.step{display:grid;grid-template-columns:36px 1fr;gap:12px;align-items:center;background:var(--box);border:1px solid var(--line);border-radius:10px;padding:10px 14px}
.n{width:28px;height:28px;border-radius:50%;background:var(--red);color:#fff;display:grid;place-items:center;font-size:13px;font-weight:800}
.lock{font-size:22px}
.two{display:grid;grid-template-columns:1fr auto 1fr;gap:14px;align-items:center}
.split{display:grid;grid-template-columns:1fr 1fr;gap:20px}
hr.soft{border:0;border-top:1px dashed var(--line);margin:14px 0}
"""

def page(title, body, h=520):
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS}body,.wrap{{height:{h}px}}</style></head>
<body><div class="wrap"><h1>{title}</h1>{body}</div></body></html>"""

pages = {}

pages["01-where.html"] = page("Where Burp sits", """
<div class="row">
  <div class="box"><b>Your browser</b><small>Chrome, Firefox,<br>or Burp’s own browser</small></div>
  <div class="arrow">→</div>
  <div class="box red"><b>Burp Proxy</b><small>127.0.0.1:8080<br>reads and can edit traffic</small></div>
  <div class="arrow">→</div>
  <div class="box"><b>The website</b><small>example.com<br>thinks Burp is the client</small></div>
</div>
<p class="note">Every click goes Browser → Burp → Server. The reply comes back Server → Burp → Browser.<br>Burp is in the middle on purpose. That is the whole tool.</p>
""", 420)

pages["02-http-https.html"] = page("Plain HTTP vs HTTPS", """
<div class="split">
  <div class="box">
    <b>HTTP — port 80</b>
    <small>The request is just text on the wire.<br><br>
    GET /login HTTP/1.1<br>
    Host: shop.test<br><br>
    Anyone on the path can read it.<br>Burp can read it with no extra work.</small>
  </div>
  <div class="box red">
    <b>HTTPS — port 443</b>
    <small>TLS wraps that same HTTP in a lock.<br><br>
    Browser and server share keys.<br>
    Outsiders see only ciphertext.<br><br>
    Burp must break TLS, read the HTTP,<br>then lock it again toward the server.</small>
  </div>
</div>
<p class="note">HTTPS does not change the HTTP message. It only hides it. Burp’s job is to unhide it for you, then hide it again.</p>
""", 420)

pages["03-connect.html"] = page("Step 1 — the CONNECT request", """
<div class="steps">
  <div class="step"><div class="n">1</div><div>Browser wants https://shop.test. It does <b>not</b> speak TLS to Burp yet. It first asks Burp to open a pipe.</div></div>
  <div class="step"><div class="n">2</div><div><code>CONNECT shop.test:443 HTTP/1.1</code> — “please open a tunnel to that host.”</div></div>
  <div class="step"><div class="n">3</div><div>Burp answers <code>HTTP/1.1 200 Connection Established</code>.</div></div>
  <div class="step"><div class="n">4</div><div>Now the browser starts TLS. From its point of view the other end of that pipe is “the server”. In reality it is Burp.</div></div>
</div>
<p class="note">No CONNECT is needed for plain HTTP. The browser just sends GET /… to 127.0.0.1:8080 and Burp forwards it.</p>
""", 480)

pages["04-two-tls.html"] = page("Two separate TLS sessions — this is the trick", """
<div class="two">
  <div class="box red"><b>Lock A</b><small>Browser ↔ Burp<br>keys Burp invented<br>cert Burp signed</small></div>
  <div class="col">
    <div class="box" style="min-width:220px"><b>Burp (plain HTTP here)</b><small>decrypt with lock A<br>you can read / edit it<br>encrypt with lock B</small></div>
  </div>
  <div class="box ok"><b>Lock B</b><small>Burp ↔ real server<br>real cert from the site<br>normal HTTPS</small></div>
</div>
<p class="note">The browser never shares keys with the website. Burp holds one conversation with you, and a second conversation with the server.<br>Inside Burp the message is just HTTP, so Intercept and Repeater can show it as text.</p>
""", 400)

pages["05-certs.html"] = page("Two certificates Burp holds", """
<div class="split">
  <div class="box red">
    <b>Burp CA (root)</b>
    <small>Made once, stored on disk.<br>Self-signed: CA signs itself.<br><br>
    Public key = “this is Burp CA”<br>
    Private key = the stamp<br>that signs every host cert.</small>
  </div>
  <div class="box">
    <b>Host cert (per site)</b>
    <small>Made on the fly for shop.test.<br>Name in the cert = shop.test.<br><br>
    New key pair for that host.<br>
    Signed by Burp CA private key.<br>
    Not self-signed — CA-signed.</small>
  </div>
</div>
<p class="note">The CA is self-signed. The shop.test cert is not. It is a child cert. The browser trusts the child only because it already trusts the parent CA.</p>
""", 400)

pages["09-keys.html"] = page("The keys, not the UI", """
<div class="row">
  <div class="box"><b>CA key pair</b><small>long-term<br>signs host certs</small></div>
  <div class="box red"><b>Host key pair</b><small>per site, on the fly<br>proves “I am shop.test”<br>to the browser</small></div>
  <div class="box"><b>Session key A</b><small>this TLS only<br>encrypts Browser ↔ Burp</small></div>
  <div class="box ok"><b>Session key B</b><small>this TLS only<br>encrypts Burp ↔ server</small></div>
</div>
<p class="note">Certificates carry public keys. Encryption of the actual HTTP uses the short-lived session keys from each handshake. Different lock, different key. Burp is the only place that has both session keys.</p>
""", 360)

pages["10-sign.html"] = page("How Burp signs a new host cert", """
<div class="steps">
  <div class="step"><div class="n">1</div><div>Need a cert for <b>shop.test</b>. Generate a fresh public/private key pair. The private key never leaves Burp.</div></div>
  <div class="step"><div class="n">2</div><div>Fill the cert: Common Name / SAN = shop.test, plus dates, serial, public key.</div></div>
  <div class="step"><div class="n">3</div><div>Hash that cert body. Sign the hash with the <b>Burp CA private key</b>. Stick the signature on the cert.</div></div>
  <div class="step"><div class="n">4</div><div>Hand the cert to the browser during TLS. Browser hashes the body, checks the signature with the <b>CA public key</b> it already trusts.</div></div>
  <div class="step"><div class="n">5</div><div>Match. Browser believes this cert is shop.test. Handshake continues. Session key A is born.</div></div>
</div>
<p class="note">Self-signed would mean the host cert signed itself. Burp does not do that by default. The host cert is signed by Burp’s CA. That is why one trusted CA covers every site you visit.</p>
""", 500)

pages["11-crypto.html"] = page("One request — decrypt, then encrypt again", """
<div class="steps">
  <div class="step"><div class="n">A</div><div>Browser encrypts <code>GET /login</code> with <b>session key A</b>. Wire Browser→Burp is ciphertext.</div></div>
  <div class="step"><div class="n">A→</div><div>Burp decrypts with session key A. Inside Burp the bytes are normal HTTP. This is what you see.</div></div>
  <div class="step"><div class="n">B</div><div>Burp encrypts that same HTTP with <b>session key B</b>. Wire Burp→server is ciphertext again.</div></div>
  <div class="step"><div class="n">B→</div><div>Server decrypts with session key B. It never had key A. Reply does the same in reverse.</div></div>
</div>
<p class="note">AES (or whatever the handshake picked) is not “broken”. Burp is a valid endpoint of both handshakes, so it is allowed to decrypt. Two rooms, two keys, Burp has a door into both.</p>
""", 430)

pages["06-full-flow.html"] = page("Backend path of one HTTPS request", """
<div class="steps">
  <div class="step"><div class="n">1</div><div><code>CONNECT shop.test:443</code> — not TLS yet. Burp learns the hostname.</div></div>
  <div class="step"><div class="n">2</div><div>Browser ClientHello (SNI=shop.test). Burp mints host cert + host key, signs with CA key.</div></div>
  <div class="step"><div class="n">3</div><div>TLS handshake Browser↔Burp finishes. <b>Session key A</b> exists only on those two sides.</div></div>
  <div class="step"><div class="n">4</div><div>Burp ClientHello to the real server. Real cert. Handshake finishes. <b>Session key B</b>.</div></div>
  <div class="step"><div class="n">5</div><div>HTTP arrives encrypted with A. Burp decrypts with A. Plaintext sitting in memory.</div></div>
  <div class="step"><div class="n">6</div><div>Optional: mutate the plaintext (intercept). Then encrypt with B and send.</div></div>
  <div class="step"><div class="n">7</div><div>Response: decrypt with B, encrypt with A. Two rooms, two keys, same HTTP in the lobby.</div></div>
</div>
""", 500)

pages["07-intercept.html"] = page("What “Intercept” actually does", """
<div class="row">
  <div class="box"><b>Off</b><small>Traffic still goes through Burp.<br>You still get HTTP history.<br>Nothing waits for you.</small></div>
  <div class="arrow">→</div>
  <div class="box red"><b>On</b><small>Matching requests (and optionally<br>responses) freeze in the Intercept tab.<br>Edit, then Forward or Drop.</small></div>
</div>
<p class="note">Intercept is a pause button, not the proxy itself. If the page “hangs”, you probably left Intercept on.<br>Turn it off when you only want to watch. Turn it on when you want to change one request by hand.</p>
""", 360)

pages["08-passthrough.html"] = page("When Burp does not decrypt — TLS pass through", """
<div class="row">
  <div class="box"><b>Browser</b><small>still talks to 8080</small></div>
  <div class="arrow">→</div>
  <div class="box"><b>Burp</b><small>forwards the TLS bytes<br>without opening them</small></div>
  <div class="arrow">→</div>
  <div class="box"><b>Server</b><small>sees the browser’s real<br>TLS fingerprint</small></div>
</div>
<p class="note">Use this when a host pins certificates (common on mobile apps) or when you do not need to read that host.<br>You will not see the HTTP in history. The pipe is still there — it is just opaque.</p>
""", 360)

pages["cover.html"] = page("Burp Proxy — encrypt, read, encrypt again", """
<div class="row">
  <div class="box"><span class="lock">🔓</span><b>Browser</b><small>thinks it is talking<br>to the website</small></div>
  <div class="arrow">→</div>
  <div class="box red"><span class="lock">👁</span><b>Burp</b><small>decrypt · read · maybe edit<br>then encrypt again</small></div>
  <div class="arrow">→</div>
  <div class="box ok"><span class="lock">🔒</span><b>Server</b><small>thinks it is talking<br>to the browser</small></div>
</div>
<p class="note">Two TLS sessions. One clear HTTP copy in the middle. That is how Burp “breaks” HTTPS without stealing the website’s private key.</p>
""", 400)

for name, html in pages.items():
    (HERE / name).write_text(html)
print("wrote", len(pages), "html diagrams")
