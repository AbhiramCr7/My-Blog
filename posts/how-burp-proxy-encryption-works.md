---
title: "How Burp Suite Intercepts HTTPS: TLS, CA Certificates, On-the-Fly Certificates and Two TLS Sessions"
date: 2026-10-16 23:50:00 +0530
author: 0xAbhiram
tags:
  - Burp Suite
  - HTTPS
  - TLS
  - Proxy
  - Product Security
  - Web Security
  - HTTP/2
  - Certificate Pinning
categories:
  - Security Engineering
description: "Deep technical explanation of how Burp Suite intercepts HTTPS: CONNECT, TLS termination, Burp CA, per-host certificates, SNI, ALPN, HTTP/2, pinning, passthrough, invisible proxying and mTLS."
---

Your browser normally establishes TLS **directly** with the origin. The two TLS endpoints are the browser and `shop.test`. Ciphertext on that path is only useful to those two parties.

If Burp wants HTTP-level visibility, it cannot sit inside that existing session. It is not an endpoint of it. Encrypted records between two other endpoints stay encrypted.

So Burp becomes an endpoint.

<aside class="call-box"><p><strong>Central fact.</strong> Burp terminates the TLS session from the client and establishes a <em>separate</em> TLS session with the destination server. It does not decrypt “Yahoo’s TLS connection.” There is no single Browser → origin TLS session once termination is in play.</p></aside>

![Normal HTTPS versus Burp: one TLS hop versus two](assets/burp/d-normal-vs-burp.svg)

## 1. The two sessions

**Normal**

```
Browser  ──── TLS ────  shop.test
```

**With Burp as an intercepting proxy**

```
Browser  ──── TLS session A ────  Burp  ──── TLS session B ────  shop.test
                      HTTP plaintext only here
```

![Two independent TLS sessions with plaintext only inside Burp](assets/burp/d-two-tls.svg)

| Hop | Endpoints | Certificate the “server” shows | Who holds the session keys |
| --- | --- | --- | --- |
| **A** | Browser ↔ Burp | Burp-generated **per-host** certificate for `shop.test`, issuer = Burp CA | Browser and Burp |
| **B** | Burp ↔ origin | The **real** `shop.test` certificate | Burp and origin |

The origin never sees the per-host certificate. The browser never sees the origin private key. Burp does not need the origin private key, because it is not a party to an end-to-end session that uses that key.

![Master architecture](assets/burp/d-master.svg)

## 2. Before TLS: listener, CONNECT, SNI

The browser is pointed at the **proxy listener** (default `127.0.0.1:8080`). That is an HTTP proxy, not a transparent bump-in-the-wire by default.

For HTTPS, a **proxy-aware** browser does **not** start TLS first. It sends an HTTP request to the proxy:

```
CONNECT shop.test:443 HTTP/1.1
Host: shop.test:443
```

Meaning: open a TCP tunnel to that host:port. Burp replies:

```
HTTP/1.1 200 Connection Established
```

TLS then runs **on that same TCP connection** to Burp. From the browser’s point of view the TLS peer is “the server.” The peer is Burp.

<aside class="note-box"><p>Burp does <strong>not</strong> mint a host certificate before it knows the destination. On this path, <code>CONNECT</code> already named <code>shop.test:443</code>. The TLS <code>ClientHello</code> typically also carries <strong>SNI</strong> = <code>shop.test</code>. CONNECT is the proxy-layer name. SNI is the TLS-layer name. Both usually agree.</p></aside>

![CONNECT, then ClientHello, then per-host certificate](assets/burp/d-connect.svg)

Plain HTTP never sends CONNECT. The browser sends `GET http://shop.test/…` (absolute-form) to `:8080` and Burp forwards it. This article is about the HTTPS path.

## 3. Burp CA

On first run, an installation of Burp generates **one** CA certificate and key, stored locally, reused across hosts and sessions until you regenerate or import another.

```
Burp CA  (self-signed, once per installation)
   ├── signs certificate for shop.test
   ├── signs certificate for api.shop.test
   └── signs certificate for auth.shop.test
```

![One CA, many host certificates](assets/burp/d-ca-tree.svg)

- **CA** = trusted signer. Public key in the testing browser/device trust store. **Private key** signs child certificates. That private key is the dangerous object (see §23).
- **Per-host certificate** = not the CA. It is a leaf that *names* `shop.test` (SAN/CN) and is *issued by* the Burp CA.

Burp does **not** create a new CA per site. Default listener mode: **Generate CA-signed per-host certificates**.

The testing browser trusts the Burp CA (Burp’s own browser ships that way; an external browser only intercepts cleanly after that CA is a trusted root). Trusting a CA means: “I will accept leaves this CA signs, if the rest of validation passes.”

## 4. On-the-fly per-host certificate

Visit `https://shop.test/account`. After CONNECT / SNI identify `shop.test`, Burp generates (or reuses a cached) certificate:

| Field | Value |
| --- | --- |
| Subject / SAN | `shop.test` |
| Issuer | Burp CA |
| Public key | key pair **Burp generated** for this host |
| Signature | over the leaf, using **Burp CA private key** |

This is **not** “Burp signs Yahoo’s real certificate.” The origin leaf is never in this chain. Burp generates a certificate **representing** `shop.test` and signs **that** certificate with Burp CA.

```
Real world:     shop.test leaf  ←  public CA  ←  browser trust store
Interception:   Burp leaf for shop.test  ←  Burp CA  ←  browser trust store
```

The browser accepts the Burp leaf because it can **build a chain to a trust anchor it has**, the name matches, dates/signatures work. It is not verifying “this is the same leaf DigiCert issued for shop.test.”

People call it a “fake certificate” as shorthand. Accurate name: **Burp-generated per-host certificate**. It is a real X.509 object. It is not the origin’s certificate.

If the client never sent CONNECT (invisible proxy, §18), Burp may still take the name from **SNI**. If SNI is absent, default per-host generation cannot know the name in time; PortSwigger documents falling back to a static self-signed cert, or configuring a **CA-signed certificate with a specific hostname** on that listener.

## 5. What the browser actually checks

```
leaf for shop.test
        │  signed by
        ▼
     Burp CA
        │  present in
        ▼
  browser trust store
```

Validation (simplified, still the right model):

- hostname vs SAN/CN  
- not-before / not-after  
- signature over the leaf using the issuer public key  
- chain to a **trusted** anchor  
- basic constraints / key usage as implemented by the stack  

It is **not** checking “byte-for-byte identical to the origin cert.”

## 6. Which keys are involved

Do not conflate these.

![Four different key classes](assets/burp/d-keys.svg)

**A. Burp CA private key**  
Signs dynamically generated host certificates. Long-lived, on disk, unique per install unless imported.

**B. Per-host key pair**  
Burp uses this as the **TLS server** toward the browser (session A). Generated for the host (implementation may cache).

**C. TLS record / session keys**  
Negotiated **per session** (TLS 1.2 vs 1.3 differ in handshake shape; both end with keys that protect records). **Session A keys** ≠ **session B keys**.

**D. Origin server private key**  
Stays on `shop.test`. **Burp does not need it**, because Burp is not decrypting a session that was terminated with that key. Burp created **session A** with its own host key, and **session B** as a client to the origin.

## 7. Request timeline (`https://shop.test/account`)

![Request lifecycle](assets/burp/d-request.svg)

1. Browser TCP-connects to the proxy listener.  
2. `CONNECT shop.test:443`.  
3. `200 Connection Established`.  
4. `ClientHello` (SNI=`shop.test`; ALPN may list `h2`, `http/1.1`).  
5. Burp presents the per-host leaf (issuer Burp CA).  
6. Browser validates the chain; handshake completes; **session A** exists.  
7. Browser sends HTTP **encrypted under A**.  
8. Burp decrypts because **Burp is the TLS server for A**.  
9. HTTP is in process memory:

```
GET /account HTTP/1.1
Host: shop.test
Cookie: session=abc123
Authorization: Bearer eyJ…
```

10. Inspect / modify / Intercept pause.  
11. Burp completes (or reuses) **session B** to the origin; origin shows its **real** cert; Burp validates it per TLS settings.  
12. Burp sends the (possibly edited) HTTP **encrypted under B**.  
13. Origin handles it as a normal TLS client request.

![Packet flow 1–12](assets/burp/d-packet.svg)

## 8. Intercept ON vs OFF

<aside class="call-box"><p><strong>Interview callout.</strong> Intercept OFF does <em>not</em> mean Burp stopped proxying or stopped terminating TLS. Both sessions still exist. History still fills. Messages are simply not paused for a human.</p></aside>

**ON:** decrypt A → **pause** in Intercept → optional edit → encrypt B.  
**OFF:** decrypt A → automatic forward → encrypt B.

Repeater / Intruder / Logger consume the same plaintext after step 8. They are not extra TLS tunnels.

## 9. What can be modified, and why

Because the object in memory is HTTP (or Burp’s HTTP/2 representation), you can change method, path, query, headers, cookies, body, `Authorization`, and Burp can rewrite `Content-Length` after body edits. That is possible **only after session A is terminated**. You cannot do it on passthrough (§17).

## 10. Response path

![Response: decrypt B, plaintext, encrypt A](assets/burp/d-response.svg)

```
shop.test  --B-->  Burp  [HTTP]  --A-->  Browser
```

Example after decrypt B:

```
HTTP/1.1 200 OK
Content-Type: application/json

{"username":"abhiram","role":"user"}
```

Same rules: Intercept can pause responses; match-and-replace can rewrite them; the browser only ever sees records protected by **A**.

## 11. Upstream TLS is a second validation relationship

![Browser validates Burp leaf; Burp validates origin leaf](assets/burp/d-trust.svg)

- **Browser** validates the Burp-generated per-host certificate (trust anchor = Burp CA).  
- **Burp** validates the origin certificate (public CAs, or custom/enterprise CAs you add in Burp TLS settings).

Two chains. Two verifiers. Failure of B (expired origin cert, name mismatch, unknown issuer) is an **upstream** problem: session A might already be up, the browser may see a Burp error page, but that is not “the browser rejected Yahoo.”

## 12. SNI

`ClientHello` extension `server_name` = `shop.test`.

Proxy-aware path: you already had CONNECT. SNI still matters for: choosing which **leaf** to present, HTTP/2 / virtual-hosting on the origin side of B, and **invisible** mode where CONNECT never happened.

## 13. ALPN and HTTP/2

ALPN in `ClientHello` advertises protocols, e.g. `h2`, `http/1.1`. The server (for session A, that server is Burp; for session B, the origin) selects one.

PortSwigger: by default Burp speaks **HTTP/2 to servers that advertise it via ALPN**. That is the **Burp → origin** hop (`Settings → Network → HTTP` → “Default to HTTP/2 if the server supports it”). Independently, each **proxy listener** can allow or deny HTTP/2 on the **client → Burp** hop. Those are not the same toggle.

Burp does not implement every HTTP/2 feature (e.g. server push is documented as unsupported). It can show HTTP/2 in a readable view while the wire hop is still HTTP/2.

Why Product Security cares: pseudo-headers, multiplexing, translation between h1 and h2, and classes of desync that only exist when the two hops disagree. That is not a smuggling tutorial; it is why protocol identity is part of interception, not an afterthought.

![HTTP/1.1 vs HTTP/2](assets/burp/d-h2.svg)

```
HTTP/1.1                          HTTP/2 (conceptual)
GET /account HTTP/1.1             :method   = GET
Host: shop.test                   :path     = /account
                                  :scheme   = https
                                  :authority= shop.test
```

HTTP/2 is not “the same bytes with a different name.”

## 14. Certificate pinning

Trusted-CA path: leaf chained to a trust anchor → accept.

Pinning adds a **second** check: does this leaf (or SPKI) match a **baked-in** expected value?

```
Burp CA is trusted
+ pin expects origin SPKI
= mismatch → abort
```

Installing Burp CA is necessary for normal intercept; it is **not sufficient** against an app that pins. High-level options testers actually use: disable pin in a **debug build**, use a pin-bypass in a jailbroken/rooted lab, or **TLS passthrough** that host and test elsewhere. Do not confuse “browser trusts Burp CA” with “this binary will accept a Burp leaf.”

![Pinning versus CA trust](assets/burp/d-pinning.svg)

## 15. TLS passthrough

Opposite of termination.

```
Normal intercept:   Browser --enc A--> Burp [HTTP] --enc B--> origin
Passthrough:        Browser --enc-----> Burp --enc----------> origin
```

![Passthrough](assets/burp/d-passthrough.svg)

No HTTP history of that hop, no Intercept, no modification. Use it for pinned hosts, fingerprint-sensitive origins (upstream sees the **browser’s** TLS fingerprint, not Burp’s), or performance. PortSwigger: can add hosts manually, or apply passthrough to out-of-scope items.

## 16. Invisible proxying

Proxy-aware client: `CONNECT`, then TLS.

Non-proxy-aware client (thick client, some plugins): it thinks it is talking to `shop.test:443`. You redirect with DNS/`hosts` to a Burp listener in **invisible** mode. There is **no CONNECT**. The first bytes may already be TLS.

Burp then: tolerate direct TLS; take hostname from **SNI** if present; after decrypt, from **`Host`** for forwarding. Outbound must not resolve back to the same listener (infinite loop)—redirect that listener’s outbound to the real IP, or override Burp hostname resolution.

If SNI is missing, configure a **specific hostname** on the CA-signed cert for that listener.

![Invisible proxying](assets/burp/d-invisible.svg)

## 17. WebSockets

TLS (A) carries HTTP; then:

```
GET /ws HTTP/1.1
Upgrade: websocket
Connection: Upgrade
```

`101` then frames, not a new CONNECT. Burp can hold client→server and server→client messages (scope rules apply). Product Security cares because authz, tampering, and business logic often live **only** on the socket after the HTTP handshake looked boring.

## 18. mTLS

Server cert: origin proves itself to the client (on hop B, “client” is Burp).

**mTLS:** origin also **requests a client certificate**. The browser’s client cert is on hop A; it does **not** automatically appear on hop B.

Burp can present client certs **upstream** (`Settings → Network → TLS → Client TLS certificates`, PKCS#12 `.p12` or PKCS#11, host wildcards). First matching rule wins. Internal APIs fail handshake if Burp has no client cert to offer.

![mTLS](assets/burp/d-mtls.svg)

## 19. Failure modes

| Problem | What you see | Why |
| --- | --- | --- |
| Burp CA not in trust store | Browser warning / fail | Chain does not reach a trust anchor |
| Certificate pinning | App aborts TLS | Extra SPKI/cert check failed |
| Upstream cert invalid | Burp cannot complete B | Burp’s validation of origin failed |
| TLS version/cipher mismatch | Handshake fail on A or B | Listener TLS protocols vs peer |
| Client is not proxy-aware | CONNECT never arrives | Need invisible mode + DNS |
| No CONNECT, no SNI | Wrong or self-signed leaf | Name unknown before ServerHello |
| HTTP/2 mismatch | Odd failures / need to pin protocol | Listener h2 ≠ origin h2, or broken h2 impl |
| mTLS | Upstream handshake fail | Origin asked for a client cert Burp didn’t send |
| Passthrough host | Empty HTTP view | By design: no termination |

## 20. Things people get wrong

| Wrong | Correct |
| --- | --- |
| “Burp decrypts shop.test’s TLS connection.” | Burp **terminates session A** and **creates session B**. |
| “Burp sends its per-host cert to the origin.” | That leaf is presented to the **browser**. Origin sees Burp as a TLS **client**. |
| “Burp creates a new CA per site.” | One CA; many **per-host** leaves. |
| “Trusting Burp CA gives Burp the origin private key.” | It does not. Different key, different session. |
| “Intercept OFF means not proxying.” | TLS A/B still run; no pause. |
| “TLS is broken.” | TLS is **terminated and re-established** at the proxy. |
| “SNI is how the proxy is selected.” | The proxy is selected by browser proxy config. SNI names the **TLS** host. |
| “HTTP/2 is only a UI setting.” | ALPN on **each hop** independently. |

## 21. Security implication of the CA private key

Anyone who has the Burp CA **private key**, plus a victim that **trusts that CA**, can mint leaves for arbitrary names and run the same two-session attack without your consent. PortSwigger: do not disclose that key; a holder may intercept HTTPS even when you are not running Burp.

Treat the CA material as a lab root. Don’t copy it to shared disks. Rotate (`Regenerate CA certificate`) if it leaked. This is the same class of risk as any corporate SSL-inspection root—narrower, because the trust anchor is usually only on **your** test browser.

## 22. Worked example

`https://shop.test/account`, proxy `127.0.0.1:8080`, Intercept off, Burp CA trusted, no pin.

1. `CONNECT shop.test:443` → `200`.  
2. `ClientHello` SNI=`shop.test`.  
3. Leaf `SAN=shop.test`, issuer Burp CA, presented on A.  
4. Browser chains leaf → Burp CA → trust store. Session A up.  
5. `GET /account` arrives encrypted on A; Burp decrypts; Cookie visible.  
6. Session B: origin leaf from the public CA; Burp validates; `GET /account` sent on B.  
7. JSON response on B; Burp decrypts; re-encrypts on A; browser renders.

Change Intercept ON at step 5 and the same bytes wait for Forward. TLS did not change. The pause did.

## How I would explain this in sixty seconds

Burp is an intercepting HTTP proxy. With the browser using the listener, HTTPS hits Burp first. A proxy-aware browser sends **CONNECT** to open a tunnel to the destination. Burp then **terminates** the client TLS connection and presents a **per-host certificate signed by Burp’s installation CA**, which the browser trusts because that CA is in its trust store. That is **session A**. Burp opens a **separate** TLS connection to the origin—**session B**—and validates the **real** server certificate. HTTP exists as plaintext only **between** those two sessions, which is how inspect/modify/Intercept work. Burp re-encrypts on each hop. It does not decrypt the origin’s original end-to-end session; it never had that session, and it does not have the origin private key.

Primary references (paraphrased, not copied): [Burp Proxy](https://portswigger.net/burp/documentation/desktop/tools/proxy), [proxy settings](https://portswigger.net/burp/documentation/desktop/settings/tools/proxy) (CA-signed per-host certs, passthrough, listener HTTP/2), [managing CA certificates](https://portswigger.net/burp/documentation/desktop/tools/proxy/manage-certificates), [invisible proxying](https://portswigger.net/burp/documentation/desktop/tools/proxy/invisible), [HTTP/2](https://portswigger.net/burp/documentation/desktop/http2), [TLS / client certificates](https://portswigger.net/burp/documentation/desktop/settings/network/tls).
