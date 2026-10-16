---
title: "Burp Under the Hood"
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
description: "How Burp terminates TLS, rebuilds trust, and intercepts encrypted traffic"
---

## The HTTPS Illusion

HTTPS looks like one encrypted pipe from the browser to the destination. That is the illusion. The lock in the address bar means the browser completed TLS with *someone it trusts*. It does not mean that peer is the origin you named in the URL.

**Normal HTTPS**

```
Browser  ───────── TLS ─────────>  Server
```

The two TLS endpoints are the browser and `example.com`. Ciphertext on that path is only useful to those two parties. A device that is not an endpoint of that connection cannot read HTTP, no matter how close it sits on the network.

**With Burp as an intercepting proxy**

```
Browser  ─── TLS A ───>  Burp  ─── TLS B ───>  Server
```

The key idea is not that encryption is broken. Burp becomes a TLS endpoint for the browser, then separately becomes a TLS client to the server. Those are two independent TLS connections. HTTP is visible only inside Burp, after the browser-side connection has been terminated.

Burp does not obtain the destination server's private key. It can inspect HTTP because it is the TLS peer the browser actually completed a handshake with.

<aside class="call-box"><p><strong>Burp does not decrypt the original browser-to-server TLS session. It terminates one TLS connection and establishes another.</strong></p></aside>

That sentence is the whole article. Confidentiality on the wire is real. The identity of the TLS peer is a trust-store decision. Change the trust store, and the same TLS machinery will protect a different endpoint.

![Normal HTTPS versus Burp: one TLS hop versus two](assets/burp/d-normal-vs-burp.svg)

## Before TLS: CONNECT

When a browser is configured to use an **explicit HTTP proxy**, an HTTPS request commonly begins with `CONNECT` before the TLS handshake.

```
CONNECT example.com:443 HTTP/1.1
Host: example.com:443
```

Burp replies:

```
HTTP/1.1 200 Connection Established
```

`CONNECT` is an HTTP proxy mechanism. It asks the proxy to open a TCP tunnel toward that host and port. It is not part of TLS, and it is not sent to `example.com`. Clients that are not using an explicit HTTP proxy never send it.

After `200 Connection Established`, the browser begins TLS through that tunnel. The first TLS record is typically a `ClientHello`. From the browser's TLS perspective, Burp is the TLS endpoint for this connection, so Burp must present a certificate the browser will accept for the requested hostname.

Distinguish the layers:

- **CONNECT** is the proxy layer. It names where the tunnel should go.
- **TLS** is the encryption and authentication layer. It starts after the tunnel exists.

## SNI: How the Hostname Fits In

The TLS `ClientHello` can contain the Server Name Indication (SNI) extension. When present, SNI normally carries the hostname the client intends to reach.

SNI is not a certificate. It is not how the browser validates identity. It is a TLS-layer hint that can tell a server, or an intercepting proxy, which name this handshake is for.

It is not guaranteed. Older stacks, some privacy modes, and some non-browser clients omit it. Burp does not always depend on it.

On the explicit-proxy path, `CONNECT` already named `example.com:443`. When SNI is present, it usually agrees. Treat them as two different signals:

```
CONNECT     →  proxy-layer destination
SNI         →  TLS-layer hostname indication, when present
Certificate →  cryptographic identity binding
```

Burp needs a hostname before it can generate the right leaf for the browser-side connection. `CONNECT` is enough on the normal proxy path. When `CONNECT` never happens, SNI can help if it is there. If neither is available in time, Burp cannot know which name to put on the leaf.

## Burp Creates Its Own Trust

The browser will not complete TLS with a random certificate. It accepts a leaf only if it can build a chain to a trust anchor already in its store.

```
Browser
   │
   │ trusts
   ▼
Burp CA
   │
   │ signs
   ▼
certificate for example.com
```

On first run, an installation of Burp generates **one** CA certificate and key. You install that CA as a trust anchor in the testing browser or device. After that, Burp can generate a CA-signed certificate for each destination host. The browser validates that leaf through its normal chain checks because the Burp CA is trusted.

![One CA, many host certificates](assets/burp/d-ca-tree.svg)

The browser is not asking "is this the same leaf a public CA issued for example.com?" It checks hostname against SAN/CN, validity window, signature, and whether the chain reaches a **trusted** anchor. Once the Burp CA is that anchor, a Burp-generated CA-signed certificate can pass the same checks a public CA leaf would.

Three private keys, three jobs:

| Key | Who holds it | What it does |
| --- | --- | --- |
| Burp CA private key | Burp | Signs interception certificates. One CA per installation, not per site. |
| Generated host certificate private key | Burp | Proves "I am example.com" to the browser on the browser-side TLS connection. |
| Destination server private key | `example.com` | Authenticates the origin on the upstream TLS connection. **Burp does not need it.** |

An attacker can generate a CA and sign a leaf for `example.com`. That has the same *shape* as Burp. It fails in a normal browser because the attacker CA is not in the trust store. Burp works in a lab because **you explicitly trusted Burp's CA**. The browser does not trust Burp because the certificate "looks legitimate." It trusts Burp because the Burp CA was added as a trust anchor.

That is also why the Burp CA private key is the dangerous lab object. Anyone who has it, plus a victim that trusts that CA, can mint host certificates and run the same two-connection intercept.

## The On-the-Fly Certificate

Visit `https://example.com/account`. Burp has to put a certificate in front of the browser before TLS Connection A can complete.

1. The browser requests `example.com`.
2. Burp determines the destination hostname (`CONNECT` on an explicit proxy; SNI when that extension is present).
3. Burp generates, or reuses a cached, certificate for `example.com`.
4. That certificate is signed by the Burp CA. SAN/CN names `example.com`. The public key belongs to a key pair Burp generated for this host.
5. The browser validates the chain against its trusted CA store.
6. TLS is established between the browser and Burp.

The certificate shown to the browser is **not** the real server's certificate. Burp does **not** send that generated certificate to `example.com`. It exists only for the browser-side TLS connection.

```
Public web:     example.com leaf  ←  public CA  ←  browser trust store
Interception:   Burp leaf for example.com  ←  Burp CA  ←  browser trust store
```

People call it a "fake certificate" as shorthand. The accurate name is a **Burp-generated CA-signed certificate**. It is a real X.509 object. It is not the origin's certificate, and it is not a new CA.

If the client never sent `CONNECT` and SNI is absent, default per-host generation may not know the name in time. PortSwigger documents a static self-signed fallback, or configuring the listener with a CA-signed certificate for a specific hostname. That is an edge of invisible proxying, not the normal browser-proxy path.

## The TLS Split

This is the architecture.

```
                    TLS Connection A
Browser ─────────────────────────────> Burp
                                         │
                                         │ TLS Connection B
                                         ▼
                                      Server
```

![Two independent TLS connections with plaintext only inside Burp](assets/burp/d-two-tls.svg)

**TLS Connection A ≠ TLS Connection B.** They do not share a session. They do not share traffic-protection secrets. The origin never sees the Burp-generated leaf. The browser never holds the origin private key.

**Browser → Burp (browser-side TLS connection).** Burp presents a Burp-generated CA-signed certificate for the destination hostname. The browser trusts the Burp CA, so the handshake completes. Burp is the TLS *server* on this hop.

**Burp → Server (upstream TLS connection).** Burp establishes a separate TLS connection to the real server. The server presents its real certificate. Burp validates that certificate according to its configured TLS verification. Burp is the TLS *client* on this hop.

| | TLS Connection A | TLS Connection B |
| --- | --- | --- |
| Endpoints | Browser ↔ Burp | Burp ↔ Server |
| Certificate the TLS client sees | Burp-generated CA-signed host cert | The real `example.com` certificate |
| Who is TLS server | Burp | The origin |
| Cryptographic state | Independent | Independent |

There is no original end-to-end TLS session on this path for Burp to unwrap. Burp terminates one TLS connection and establishes another.

## What Happens to the Keys?

TLS derives traffic-protection keys independently for each connection. Long-term private keys authenticate the handshake. Per-connection secrets protect the records. Those are not the same objects.

```
Browser ↔ Burp     own TLS cryptographic state
Burp ↔ Server      separate TLS cryptographic state
```

Do not picture a literal encryption key being shipped from the server to Burp. Burp does not "get the server's session key." Burp establishes a separate TLS connection to the server and derives its own traffic-protection secrets for that connection.

Stealing the origin private key later does not unwind Connection A. Possessing Connection A's secrets does not let you read Connection B. They were never the same handshake.

**Burp does not need** the destination server private key, the destination's public CA private key, or the traffic secrets of an original browser-to-server TLS session. That original session is not the path.

**Burp does control** its own CA, the private key for the generated host certificate, and its own upstream TLS connection. That is enough to terminate A, read HTTP, and speak TLS on B.

<aside class="note-box"><p>The exact handshake and key schedule differ between TLS versions, but the interception architecture remains the same: browser↔Burp and Burp↔server are separate TLS connections.</p></aside>

## Request Flow: What Burp Actually Sees

`GET /account` to `https://example.com/account`, browser pointed at Burp.

```
Browser
   │
   │ encrypted TLS A
   ▼
 Burp
   │
   │ HTTP available after TLS termination
   │ inspect / modify / drop / Repeater
   ▼
 Server
```

Because Burp terminated the browser-side TLS connection, the HTTP message is available at the proxy layer:

```
GET /account HTTP/1.1
Host: example.com
Cookie: sid=abc123
Authorization: Bearer eyJ…
```

That is why Intercept, Logger, Repeater, and match-and-replace exist. They operate on HTTP after Connection A is terminated, not on TLS records. You can change method, path, headers, cookies, body, or `Authorization`, then let Burp send the result on Connection B. You cannot do that until A is terminated.

The response is the same split in reverse. Burp terminates the upstream TLS connection, processes HTTP, then protects the (possibly edited) response with Connection A's traffic-protection keys.

```
Server
   │
   │ TLS B
   ▼
 Burp
   │
   │ TLS termination / HTTP processing
   ▼
 Browser
   (TLS A)
```

![Request lifecycle](assets/burp/d-request.svg)

A network observer between browser and Burp still sees TLS records. A network observer between Burp and the server still sees TLS records. HTTP exists in Burp's process, not as plaintext on either wire.

## Why the Browser Still Shows HTTPS

If Burp sees plaintext, why does Chrome still show HTTPS?

The browser's connection to Burp is still TLS. The lock is honest about *that* hop. The plaintext exists inside Burp after TLS termination, not on the Browser ↔ Burp wire as HTTP.

```
Browser
   │ encrypted
   ▼
Burp
   │
   │ plaintext available internally after termination
   ▼
Burp
   │ encrypted
   ▼
Server
```

Burp is not turning HTTPS into plain HTTP across the network. It is TLS termination, then HTTP processing, then a new TLS connection.

## Intercept ON vs OFF

This is easy to mix up with the TLS architecture. They are not the same switch.

**Intercept ON.** Burp pauses the already-terminated HTTP request or response so a human can inspect or edit it.

**Intercept OFF.** Burp still terminates the browser-side TLS connection and still speaks TLS to the destination, according to the configured interception architecture. History still fills. Repeater still has the message. There is simply no pause.

```
TLS interception  ≠  manual interception pause
```

Turning Intercept off does not mean Burp stopped being a TLS endpoint. It means the HTTP is forwarded automatically after Burp has already terminated Connection A.

## Upstream TLS Validation

Two different TLS clients, two different trust decisions.

**The browser** validates the Burp-generated CA-signed certificate. The chain it cares about is leaf → Burp CA → its trust store.

**Burp** validates the real destination certificate according to its configured TLS verification: typically chain/trust, hostname, and validity. Custom or enterprise CAs can be added in Burp TLS settings. Burp does not blindly accept every upstream certificate.

Failure on Connection B is an upstream problem. Connection A may already be up, so the browser sees an error *from Burp*, not a rejection of the origin leaf by the browser's own TLS stack. That distinction matters when you debug "Chrome says the site is broken" while the actual failure is Burp refusing the origin cert.

## When HTTPS Interception Breaks

Trusting the Burp CA is necessary for intercept in a normal browser TLS stack. It is not sufficient for every client.

### Certificate pinning

Some applications enforce a specific certificate or public-key identity rather than relying only on the platform CA store. Mobile apps do this so a user-installed CA cannot silently become `api.example.com`.

The Burp-generated host certificate will not match the pin, so the app aborts TLS even though the Burp CA is trusted. Pinning is an extra identity check, not "the CA isn't trusted." Lab options stay at that layer: a debug build with the pin off, an instrumented client, or TLS passthrough for that host.

### TLS passthrough

Burp can forward TLS without terminating it.

```
Browser ───── encrypted TLS ─────> Server
                     │
                    Burp
                 forwarding only
```

![Passthrough forwards TLS records without terminating them](assets/burp/d-passthrough.svg)

If Burp does not terminate TLS, it cannot inspect HTTP contents, cannot modify headers or parameters, and cannot use normal HTTP-level Intercept. Use passthrough for pinned hosts, or when the origin is sensitive to Burp's TLS fingerprint rather than the browser's.

TLS passthrough is the opposite of the architecture this article is about.

### ALPN / HTTP/2

ALPN lets each TLS connection negotiate the application protocol (`h2` or `http/1.1`). Because browser→Burp and Burp→server are separate TLS connections, that negotiation happens independently on each hop. Do not assume the browser and the origin agreed on the same protocol "through" Burp.

### Invisible proxying

Invisible proxying is for clients that are not configured to use an explicit HTTP proxy. Traffic is redirected at the network layer to a Burp listener. There is no `CONNECT`. When available, TLS information such as SNI can help identify the intended hostname. SNI is not guaranteed, and invisible proxying does not always depend on it.

### mTLS

Mutual TLS adds client-certificate authentication, creating an additional trust relationship that a proxy must handle. The browser's client certificate lives on Connection A. It does not automatically appear on Connection B.

## Common Misconceptions

<aside class="call-box"><p><strong>Remember these distinctions.</strong></p>
<p>CONNECT ≠ TLS</p>
<p>SNI ≠ certificate</p>
<p>Burp CA ≠ destination CA</p>
<p>Generated host certificate ≠ destination certificate</p>
<p>TLS Connection A ≠ TLS Connection B</p>
<p>TLS termination ≠ TLS passthrough</p>
<p>Intercept ON/OFF ≠ whether TLS interception exists</p>
</aside>

If a sentence in a write-up or an interview answer collapses any of those pairs, the architecture is already wrong.

## Worked Example

The user opens `https://example.com/account`. Explicit HTTP proxy at `127.0.0.1:8080`. Burp CA trusted. Intercept off. No pin.

1. Browser sends `CONNECT example.com:443` to Burp.
2. Burp establishes the proxy tunnel and returns `200 Connection Established`.
3. TLS begins. `ClientHello` may include SNI=`example.com` if present.
4. Burp presents a Burp-generated CA-signed certificate for `example.com`.
5. The browser validates it because the Burp CA is in its trust store.
6. Browser and Burp establish TLS Connection A.
7. Browser sends `GET /account` protected by Connection A's traffic-protection keys.
8. Burp terminates A, so the HTTP is available. It can inspect or modify; with Intercept off it forwards.
9. Burp establishes or reuses TLS Connection B to `example.com`.
10. The server sees a normal TLS client. It presents its real certificate. Burp validates it.
11. The server responds on Connection B.
12. Burp receives and processes the response.
13. Burp sends the response back over TLS Connection A.

The server never saw the Burp-generated leaf. The browser never held the origin private key. HTTP was visible only inside Burp, between two TLS connections.

Turn Intercept ON at step 8 and the same bytes wait for Forward. The TLS architecture did not change. The pause did.

## The Mental Model

```
Browser
   │
   │ TLS Connection A
   ▼
 Burp
   │
   │ TLS Connection B
   ▼
Server
```

One browser request. Two TLS connections.

Burp is trusted by the browser through its CA.

Burp generates a certificate for the destination.

Burp terminates the browser-side TLS connection.

Burp can inspect and modify the HTTP message.

Burp establishes a separate TLS connection to the real server.

That's how Burp can inspect HTTPS without possessing the server's private key.
