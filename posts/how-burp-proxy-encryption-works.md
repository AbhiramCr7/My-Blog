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

HTTPS is HTTP carried over TLS. TLS provides confidentiality and integrity for the connection, and certificate-based authentication helps the client verify the identity of the intended server.

**Normal HTTPS**

```
Browser
   |
   | TLS connection
   v
Target Server
```

The two TLS endpoints are the browser and `shop.test`. Ciphertext on that path is only useful to those two parties. If Burp wants HTTP-level visibility, it cannot sit inside that existing connection. Encrypted records between two other endpoints stay encrypted.

**Burp interception**

```
Browser
   |
   | TLS Connection A
   | Burp-generated certificate
   v
Burp
   |
   | HTTP plaintext exists inside Burp
   |
   | TLS Connection B
   | Real target certificate
   v
Target Server
```

<aside class="call-box"><p><strong>Central fact.</strong> Burp does not decrypt the original browser-to-server TLS connection using the server's private key. Burp terminates the client-side TLS connection and establishes a separate TLS connection to the destination. Connection A and Connection B have independent TLS state and independently derived traffic-protection keys.</p></aside>

![Normal HTTPS versus Burp: one TLS hop versus two](assets/burp/d-normal-vs-burp.svg)

## 1. The two TLS connections

**Normal**

```
Browser  ──── TLS ────  shop.test
```

**With Burp as an intercepting proxy**

```
Browser  ──── TLS connection A ────  Burp  ──── TLS connection B ────  shop.test
                      HTTP plaintext only here
```

![Two independent TLS connections with plaintext only inside Burp](assets/burp/d-two-tls.svg)

| Hop | Endpoints | Certificate presented to the TLS client | Cryptographic state |
| --- | --- | --- | --- |
| **A** | Browser ↔ Burp | Burp-generated **per-host** certificate for `shop.test`, issuer = Burp CA | Independent handshake; traffic secrets derived for this connection only |
| **B** | Burp ↔ origin | The **real** `shop.test` certificate | A second, independent handshake; different traffic secrets |

The origin never sees the per-host certificate. The browser never holds the origin private key. **Burp does not obtain the target server’s private key** and does **not** decrypt the original browser-to-server TLS connection using that key. Burp terminates the client-side TLS connection and establishes a separate TLS connection to the destination.

Connection A and Connection B have independent TLS state and independently derived traffic-protection keys. The TLS handshake **establishes shared cryptographic secrets from which traffic-protection keys are derived**. Diagrams label the hops **A** and **B**. Those labels are not a single AES key shipped across the wire.

![Master architecture](assets/burp/d-master.svg)

## 2. Before TLS: listener, CONNECT, SNI

This section describes the **explicit HTTP proxy** flow used when a browser is configured to use Burp as its proxy (default listener `127.0.0.1:8080`). That is not TLS itself, and not every HTTPS architecture uses it.

**CONNECT is an HTTP proxy method.** It is sent to the proxy to establish a tunnel through an explicit HTTP proxy. It is **not** part of TLS and it is **not** sent to `shop.test`. HTTPS does not always begin with CONNECT.

With an explicit HTTP proxy, the browser first sends an HTTP CONNECT request to the proxy:

```
Browser
  |
  |  HTTP CONNECT shop.test:443     ← to Burp, not to the origin
  v
Burp
  |
  |  200 Connection Established
  |
  |  TLS ClientHello                ← TLS starts here
  v
Burp (TLS endpoint for this hop)
```

```
CONNECT shop.test:443 HTTP/1.1
Host: shop.test:443
```

Meaning: “proxy, open a TCP tunnel toward that host:port.” Burp responds with `200 Connection Established`. The browser can then begin the TLS handshake through the established proxy connection:

```
HTTP/1.1 200 Connection Established
```

From the browser’s TLS perspective, Burp is the **TLS endpoint** for this connection. Burp therefore presents a certificate valid for the hostname the browser requested.

Browser requests `https://shop.test`. Burp generates/presents a certificate for `shop.test`, signed by the **Burp CA**. The browser accepts it because **Burp CA is trusted in the browser’s trust store**, and the rest of validation (hostname, dates, signatures, chain) passes. It does not accept the certificate merely because Burp answered the TCP connection.

The TLS ClientHello **can** contain the Server Name Indication (SNI) extension. When present, it normally carries the hostname the client intends to reach, such as `shop.test`.

SNI is a TLS extension. It is **not** a certificate, **not** a private key, **not** the certificate itself, and **not** guaranteed to be present in every TLS connection.

When SNI is present, the hostname can help an interception proxy identify the intended destination and generate the appropriate interception certificate. Burp does **not** always rely on SNI.

<aside class="note-box"><p>Burp does <strong>not</strong> mint a host certificate before it knows the destination. On the explicit-proxy path, <code>CONNECT</code> already named <code>shop.test:443</code>. When SNI is present, it usually agrees. CONNECT = proxy-layer name. SNI = TLS-layer name, <em>if sent</em>.</p></aside>

![CONNECT, then ClientHello, then per-host certificate](assets/burp/d-connect.svg)

Plain HTTP on an explicit proxy never sends CONNECT. The browser sends `GET http://shop.test/…` (absolute-form) to `:8080` and Burp forwards it. The HTTPS intercept path below still assumes an explicit HTTP proxy unless a later section says otherwise.

## 3. Burp CA

On first run, an installation of Burp generates **one** CA certificate and key, stored locally, reused across hosts and sessions until you regenerate or import another.

```
Burp CA  (self-signed, once per installation)
   ├── signs certificate for shop.test
   ├── signs certificate for api.shop.test
   └── signs certificate for auth.shop.test
```

![One CA, many host certificates](assets/burp/d-ca-tree.svg)

- **CA** = trusted signer. Public key in the testing browser/device trust store. **Private key** signs child certificates. That private key is the dangerous object (see the CA-key section later).
- **Per-host certificate** = not the CA. It is a leaf that *names* `shop.test` (SAN/CN) and is *issued by* the Burp CA.

Burp does **not** create a new CA per site. Default listener mode: **Generate CA-signed per-host certificates**.

The browser must **explicitly trust Burp's CA certificate**. Once the Burp CA is trusted, certificates generated by Burp for intercepted hosts can validate successfully.

```
Browser trust store
       ↓
Burp CA
       ↓
Burp-generated shop.test certificate
```

Burp uses its CA to sign dynamically generated certificates for intercepted hosts. It does **not** create a new CA for every website.

The Burp CA private key is not the same thing as a per-host private key. The per-host private key is not the target server's private key. Burp does not possess the target server's private key.

## 4. On-the-fly per-host certificate

Visit `https://shop.test/account`. On the explicit-proxy path, CONNECT already named `shop.test:443`. For TLS connections where SNI is present, that hostname can also identify the destination. Burp then generates (or reuses a cached) certificate:

| Field | Value |
| --- | --- |
| Subject / SAN | `shop.test` |
| Issuer | Burp CA |
| Public key | key pair **Burp generated** for this host |
| Signature | over the leaf, using **Burp CA private key** |

This is **not** “Burp signs the origin’s real certificate.” The origin leaf is never in this chain. Burp generates a certificate **representing** `shop.test` and signs **that** certificate with Burp CA.

```
Real world:     shop.test leaf  ←  public CA  ←  browser trust store
Interception:   Burp leaf for shop.test  ←  Burp CA  ←  browser trust store
```

The browser accepts the Burp leaf because it can **build a chain to a trust anchor it has**, the name matches, dates/signatures work. It is not verifying “this is the same leaf DigiCert issued for shop.test.”

Accurate name: **Burp-generated interception certificate** (a locally generated certificate for the requested hostname). It is a real X.509 object. It is **not** the target server's genuine certificate. It is generated by Burp and signed by the Burp CA.

If the client never sent CONNECT (invisible proxy), Burp may still take the name from **SNI when that extension is present**. If SNI is absent, default per-host generation cannot know the name in time; PortSwigger documents falling back to a static self-signed cert, or configuring a **CA-signed certificate with a specific hostname** on that listener.

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

**BURP CA KEY PAIR**  
Long-lived. Used to sign interception certificates. The Burp CA private key is not the same thing as a per-host private key.

**PER-HOST KEY PAIR**  
Generated for an intercepted hostname (example: `shop.test`). Burp controls the private key corresponding to the Burp-generated interception certificate on the client side. The per-host private key is not the target server's private key.

**TLS CONNECTION A**  
Browser ↔ Burp. The browser establishes TLS with Burp and derives traffic-protection keys for the browser-to-Burp connection. Independent TLS cryptographic state.

**TLS CONNECTION B**  
Burp ↔ target. Burp establishes a separate TLS connection to the target server, producing independent cryptographic state and traffic-protection keys for that connection.

**TARGET SERVER PRIVATE KEY**  
Stays on `shop.test`. Burp does not possess the target server's private key. Burp participates in both TLS connections, each with its own cryptographic state.

## 6b. TLS 1.2 vs TLS 1.3

**TLS 1.2** supports several handshake/key-exchange mechanisms. Older configurations could use RSA key transport, while modern secure configurations commonly use ephemeral Diffie-Hellman key exchange.

**TLS 1.3** uses ephemeral key agreement and derives handshake/application traffic secrets.

Modern TLS should therefore **not** be described as simply “the server sends a session key.” The handshake establishes shared secrets from which traffic-protection keys are derived.

Burp, as a TLS endpoint on A and as a TLS client on B, participates in whatever handshake the peer negotiates (within the protocols the listener / Java TLS settings allow). That is still termination of one connection and establishment of another.

## 6c. Conceptual TLS handshake - simplified

Browser requested `shop.test`. Burp terminates that TLS connection and presents a Burp-generated certificate for `shop.test`, signed by the trusted Burp CA. The browser validates **chain + hostname + time + signatures** against its trust store.

```
Browser                              Burp
   |                                   |
   |------ ClientHello --------------->|   SNI=shop.test (if present)
   |      ALPN=h2, http/1.1 (typical)  |
   |                                   |
   |<----- ServerHello ----------------|
   |<----- Certificate ----------------|   per-host leaf, issuer = Burp CA
   |<----- key-exchange data ----------|   conceptual (1.2 vs 1.3 differ)
   |------ Finished ------------------>|
   |======= encrypted HTTP ===========>|
```

This is **only** Browser ↔ Burp (connection A). Burp then performs a **separate** TLS handshake with the destination (connection B). The message list above is a **conceptual flow**, not an exact packet capture, and TLS versions do not all use this packet ordering.

![Conceptual TLS handshake - simplified](assets/burp/d-handshake.svg)

## 7. Request timeline (`https://shop.test/account`)

Conceptual lifecycle (explicit HTTP proxy):

1. Browser creates an HTTP request.  
2. Browser sends the request over **TLS Connection A**.  
3. Burp **terminates** TLS Connection A.  
4. Burp now has the HTTP message in plaintext in its process memory.  
5. Intercept may pause that HTTP message.  
6. Burp can inspect or modify it.  
7. Burp sends the resulting HTTP message through **TLS Connection B**.  
8. The target server receives Connection B.

```
GET /account HTTP/1.1
Host: shop.test
Cookie: session=abc123
Authorization: Bearer eyJ…
```

![Request lifecycle](assets/burp/d-request.svg)

On the explicit-proxy path, CONNECT and `200 Connection Established` happen **before** TLS Connection A. `ClientHello` may include SNI and ALPN **if present**. Burp presents the Burp-generated interception certificate; the browser validates it against the trusted Burp CA.

![Packet flow 1-12](assets/burp/d-packet.svg)

## 8. Intercept ON vs OFF

Burp terminates the client-side TLS connection **regardless of whether Intercept is enabled**. Intercept controls whether Burp pauses the HTTP message before forwarding it. Intercept is not a third protocol and does not itself decrypt TLS. It is a control point where Burp can pause and modify the already-terminated HTTP message.

**ON:** the HTTP request is paused before forwarding.  
**OFF:** the HTTP request continues automatically.

Repeater / Intruder / Logger consume the same plaintext after Connection A is terminated. They are not extra TLS tunnels.

## 9. What can be modified, and why

Because the object in memory is HTTP (or Burp’s HTTP/2 representation), you can change method, path, query, headers, cookies, body, `Authorization`, and Burp can rewrite `Content-Length` after body edits. That is possible **only after connection A is terminated**. You cannot do it on TLS passthrough.

## 10. Response path

![Response: terminate B, plaintext, protect on A](assets/burp/d-response.svg)

```
Target
 ↓
TLS Connection B
 ↓
Burp
 ↓
HTTP plaintext in Burp
 ↓
TLS Connection A
 ↓
Browser
```

Example after Burp terminates connection B:

```
HTTP/1.1 200 OK
Content-Type: application/json

{"username":"abhiram","role":"user"}
```

Same rules: Intercept can pause responses; match-and-replace can rewrite them; the browser only ever sees records protected by connection A’s derived traffic keys.

## 11. How Burp verifies the real server

```
Browser
   |
   |  validates Burp-generated per-host certificate
   |  (hostname, chain, signature, trust anchor = Burp CA)
   v
 Burp
   |
   |  validates the origin’s real certificate
   |  (chain/trust, hostname, validity  - per Burp TLS settings)
   v
shop.test
```

![Browser validates Burp leaf; Burp validates origin leaf](assets/burp/d-trust.svg)

**Browser → Burp (connection A):** the browser requested `shop.test`. It validates a Burp-generated certificate **for that hostname**, with a chain that terminates at the **Burp CA in its trust store**.

**Burp → origin (connection B):** Burp then establishes a **separate** TLS connection to the real server. It validates the server certificate according to its configured TLS verification behaviour, including checks such as certificate trust, validity and hostname verification. Custom/enterprise CAs can be added in Burp TLS settings.

**Burp does not need the target server’s private key** to establish this second TLS connection. It is a TLS *client* on that hop.

Failure of B (expired origin cert, name mismatch, unknown issuer) is an **upstream** problem. Connection A might already be up; what the browser sees is a failure **from Burp**, not “the browser rejected the origin’s leaf.”

## 11b. Why anyone cannot simply MITM HTTPS

An attacker can generate an attacker CA and sign a leaf for `shop.test`. That is the same *shape* as Burp. It fails in a normal browser because **the attacker CA is not in the trust store**.

Burp works in a controlled testing environment because the **Burp CA has been explicitly installed as trusted**. Installing Burp’s CA changes the browser’s trust boundary; it does not weaken TLS cryptography itself.

```
Burp CA trusted                         Attacker CA not trusted
   |                                           |
   +-- signs --> shop.test leaf                +-- signs --> shop.test leaf
                     |                                      |
                     v                                      X
              browser accepts                      certificate validation failure
```

![Without a trusted CA, interception fails](assets/burp/d-untrusted.svg)

## 12. SNI (TLS extension, not always present)

The TLS `ClientHello` **can** contain the **SNI** extension (`server_name`). When present, it normally carries the hostname the client intends to reach, such as `shop.test`. It is not a required field of every ClientHello.

On an explicit-proxy path you already had CONNECT. For TLS connections where SNI is present, that hostname can help Burp choose which **leaf** to present, and it still matters for origin virtual-hosting on connection B and for **invisible** mode where CONNECT never happened. If SNI is **absent**, Burp cannot take the name from TLS and must use CONNECT (explicit proxy), `Host` after the HTTP is visible, a listener configured with a **specific hostname** cert, or a fallback self-signed leaf. See invisible proxying.

## 13. ALPN: Negotiating HTTP/1.1 vs HTTP/2

**ALPN** (Application-Layer Protocol Negotiation) lets the TLS endpoints negotiate the application protocol carried inside the TLS connection. Typical offers: `h2` (HTTP/2), `http/1.1`. The TLS server on that hop selects one. Protocol negotiation is **part of the TLS handshake**, not a later HTTP trick.

```
TLS ClientHello
       |
       +-- ALPN: h2         → HTTP/2
       |
       +-- ALPN: http/1.1   → HTTP/1.1
```

Burp terminates the browser's TLS connection and establishes a separate upstream TLS connection. Therefore, the protocol negotiated on the client-to-Burp connection and the protocol negotiated on the Burp-to-server connection are **logically independent**. Do **not** assume both sides negotiated the same protocol.

PortSwigger: by default Burp speaks **HTTP/2 to servers that advertise it via ALPN** on the **Burp → origin** hop (`Settings → Network → HTTP` → “Default to HTTP/2 if the server supports it”). Independently, each **proxy listener** can allow or deny HTTP/2 on **client → Burp**. Those are not the same toggle.

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

**Normal browser trust** (what installing Burp CA buys you):

```
Browser → platform trust store → Burp CA is a trust anchor
        → Burp-generated leaf for shop.test chains to that CA
        → hostname matches → accept
```

Certificate pinning is an additional **application-level verification mechanism**. Depending on the implementation, an application may require a specific certificate or public-key/SPKI identity rather than relying only on the platform trust store. Do not claim every app implements pinning the same way.

```
Application
  → expected cert or public key (baked in)
  → Burp leaf / SPKI does not match
  → connection rejected
```

Trusting Burp CA is **necessary** for intercept in a normal browser TLS stack and **not sufficient** when the app pins. High-level lab options: debug build with pin off, instrumented/jailbroken client, or **TLS passthrough** for that host. Pinning is not the same statement as “the CA isn’t trusted.”

![Pinning versus CA trust](assets/burp/d-pinning.svg)

## 15. TLS passthrough

Opposite of **termination**.

**Interception**

```
Browser -- encrypted TLS A --> Burp  [HTTP plaintext]  -- encrypted TLS B --> origin
```

Burp is a TLS endpoint on A, so it can inspect/modify HTTP, then wrap a **new** TLS connection B.

**Passthrough**

```
Browser -- encrypted TLS --> Burp/network layer -- same encrypted TLS stream --> origin
```

In TLS passthrough, Burp does **not** terminate the client's TLS connection. Therefore it cannot inspect or modify the HTTP plaintext inside that connection. Burp does not establish a separate intercepted client-side TLS endpoint for that traffic. No Burp-generated interception certificate for that hop, no HTTP history of bodies, no Intercept.

![Passthrough](assets/burp/d-passthrough.svg)

Use it for pinned hosts, fingerprint-sensitive origins (upstream can see the **browser’s** TLS fingerprint rather than Burp’s), or performance. PortSwigger: add hosts, or apply passthrough to out-of-scope items.

## 16. Invisible proxying

**Explicit HTTP proxy** (normal browser config):

```
Browser -- CONNECT --> Burp -- TLS A / HTTP / TLS B --> origin
```

CONNECT is how the client names the destination **before** TLS.

With invisible proxying, the client may not be configured to use an HTTP proxy. Traffic is redirected at the **network layer** to the interception proxy. That is not simply another browser proxy setting. There is **no CONNECT**. The client is not using an HTTP proxy, so the first application data on that TCP connection may already be TLS.

The proxy can use information available from the connection to determine the intended destination: destination address of the redirected TCP; for TLS connections, **SNI may provide the hostname when it is present**; after the HTTP is visible, the **`Host`** header. SNI is not guaranteed. Invisible proxying does **not** always depend on SNI.

If the name is unknown before `ServerHello`, PortSwigger documents a static self-signed fallback, or configure the listener to generate a **CA-signed certificate with a specific hostname**. Outbound must not resolve back to the same listener (loop) - force outbound to the real IP, or override Burp hostname resolution.

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
| “Burp decrypts shop.test’s TLS connection.” | Burp **terminates connection A** and **creates connection B**. |
| “Burp sends its per-host cert to the origin.” | That leaf is presented to the **browser**. Origin sees Burp as a TLS **client**. |
| “Burp creates a new CA per site.” | One CA; many **per-host** leaves. |
| “Trusting Burp CA gives Burp the origin private key.” | It does not. Different key, different TLS connection. |
| “Intercept OFF means not proxying.” | TLS A/B still run; no pause. |
| “TLS is broken.” | TLS is **terminated and re-established** at the proxy. |
| “SNI is how the proxy is selected.” | Explicit proxy is selected by browser proxy config. SNI, **when present**, names the **TLS** host. |
| “SNI is always in ClientHello.” | SNI is an **optional** TLS extension. |
| “CONNECT is part of TLS.” | CONNECT is an **HTTP proxy** method. TLS starts after `200`. |
| “Burp gets the server’s session key.” | The two TLS connections have **separate** cryptographic state and traffic-protection keys. |
| “The browser trusts Burp because the cert looks legitimate.” | The **Burp CA is in the trust store**. |
| “Pinning means the browser doesn’t trust the CA.” | Pinning is usually an **app-level** extra identity check. |
| “HTTP/2 is only a UI setting.” | ALPN on **each hop** independently. |

## 21. Security implication of the CA private key

Anyone who has the Burp CA **private key**, plus a victim that **trusts that CA**, can mint leaves for arbitrary names and run the same interception without your consent. PortSwigger: do not disclose that key; a holder may intercept HTTPS even when you are not running Burp.

Treat the CA material as a lab root. Don’t copy it to shared disks. Rotate (`Regenerate CA certificate`) if it leaked. This is the same class of risk as any corporate SSL-inspection root - narrower, because the trust anchor is usually only on **your** test browser.

## 22. Worked example

Explicit HTTP proxy at `127.0.0.1:8080`, `https://shop.test/account`, Intercept off, Burp CA trusted, no pin.

1. `CONNECT shop.test:443` → `200`.  
2. `ClientHello` (SNI=`shop.test` if present).  
3. Leaf `SAN=shop.test`, issuer Burp CA, presented on A.  
4. Browser chains leaf → Burp CA → trust store. Connection A up.  
5. `GET /account` arrives protected on A; Burp terminated A, so Cookie is visible.  
6. Connection B: origin leaf from the public CA; Burp validates; `GET /account` sent on B.  
7. JSON response on B; Burp reads it after terminating B; protects it again on A; browser renders.

Change Intercept ON at step 5 and the same bytes wait for Forward. TLS did not change. The pause did.

## Mental model (keep this)

HTTPS is HTTP carried over TLS.

With Burp interception, the browser does not maintain one end-to-end TLS connection directly to the target server.

```
             EXPLICIT PROXY

Browser
   |
   | HTTP CONNECT
   | shop.test:443
   v
Burp
   |
   | TLS Connection A
   | Burp-generated certificate
   |
   | HTTP plaintext inside Burp
   |
   | TLS Connection B
   | Real server certificate
   v
Target Server

TLS Connection A ≠ TLS Connection B
CONNECT ≠ TLS
SNI ≠ certificate
Burp CA ≠ target server CA
```

The browser trusts Burp because the Burp CA has been explicitly trusted.

Burp does not possess the target server's private key.

The two TLS connections have independent cryptographic state.

Intercept is simply Burp pausing the HTTP message after it has terminated the client-side TLS connection and before it forwards the message through the upstream TLS connection.

## How I would explain this in sixty seconds

HTTPS is HTTP carried over TLS. With an explicit HTTP proxy, the browser sends CONNECT to Burp, then begins TLS. Burp terminates that client-side TLS connection (Connection A) with a Burp-generated interception certificate signed by the trusted Burp CA, reads the HTTP plaintext, and establishes a separate TLS connection to the destination (Connection B). Intercept only pauses that already-terminated HTTP message. Burp does not possess the target private key and does not decrypt an original end-to-end TLS connection.

Primary references (paraphrased, not copied): [Burp Proxy](https://portswigger.net/burp/documentation/desktop/tools/proxy), [proxy settings](https://portswigger.net/burp/documentation/desktop/settings/tools/proxy) (CA-signed per-host certs, passthrough, listener HTTP/2), [managing CA certificates](https://portswigger.net/burp/documentation/desktop/tools/proxy/manage-certificates), [invisible proxying](https://portswigger.net/burp/documentation/desktop/tools/proxy/invisible), [HTTP/2](https://portswigger.net/burp/documentation/desktop/http2), [TLS / client certificates](https://portswigger.net/burp/documentation/desktop/settings/network/tls).
