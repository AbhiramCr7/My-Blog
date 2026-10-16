---
title: "The HTTPS Illusion"
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

HTTPS looks like one encrypted pipe from the browser to the destination. That is the illusion. The lock in the address bar means the browser completed TLS with *someone it trusts*. It does not mean the TLS peer is the origin you had in mind.

**Normally**

```
Browser  ───────── TLS ─────────>  Server
```

The two TLS endpoints are the browser and `example.com`. Ciphertext on that path is only useful to those two parties. A proxy that is not an endpoint of that connection cannot read HTTP.

**With Burp as an explicit intercepting proxy**

```
Browser  ─── TLS A ───>  Burp  ─── TLS B ───>  Server
```

Burp terminates the browser-side TLS connection, then establishes a separate TLS connection to the destination. Those are two independent TLS connections. HTTP is visible only inside Burp, after the client-side connection has been terminated.

Burp does not obtain the real server's private key. It can inspect HTTP because it is the TLS endpoint the browser actually talked to.

That is the Product Security point. Confidentiality on the wire is real. The identity of the peer is a trust-store decision. Change the trust store, and the same TLS machinery will happily protect a different endpoint.

![Normal HTTPS versus Burp: one TLS hop versus two](assets/burp/d-normal-vs-burp.svg)

## Before TLS: CONNECT

When a browser is configured to use Burp as an **explicit HTTP proxy** and wants HTTPS, it commonly sends an HTTP `CONNECT` request to the proxy *before* TLS begins.

```
CONNECT example.com:443 HTTP/1.1
Host: example.com:443
```

Burp replies:

```
HTTP/1.1 200 Connection Established
```

`CONNECT` is an HTTP proxy mechanism. It asks the proxy to open a TCP tunnel toward that host and port. It is not part of TLS, and it is not sent to `example.com`. HTTPS does not always start with `CONNECT`. Invisible proxying and other non-proxy-aware clients never send it.

After `200 Connection Established`, the browser begins the TLS handshake through that tunnel. The first TLS record is typically a `ClientHello`. From the browser's TLS perspective, Burp is the TLS endpoint for this connection, so Burp presents a certificate valid for the hostname the browser requested.

SNI is a TLS extension that can provide the intended hostname when present. It is not a required field of every `ClientHello`, and Burp does not always depend on it. On the explicit-proxy path, `CONNECT` already named the destination. When SNI is present, it usually agrees with that name. CONNECT is the proxy-layer name. SNI is the TLS-layer name, if sent.

## Burp Creates Its Own Trust

The browser will not complete TLS with a random certificate. It accepts a leaf only if it can build a chain to a trust anchor it already has.

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

On first run, Burp generates **one** CA certificate and key for that installation. You install that CA as a trust anchor in the testing browser or device. Burp then generates a CA-signed certificate for the destination host (`example.com`), with a SAN/CN that matches the name the client requested.

The browser is not checking "is this the same leaf DigiCert issued for example.com?" It checks hostname against SAN/CN, validity window, signature, and whether the chain reaches a **trusted** anchor. Once the Burp CA is that anchor, a Burp-generated host certificate can pass the same checks a public CA leaf would.

![One CA, many host certificates](assets/burp/d-ca-tree.svg)

Three private keys, three different jobs:

| Key | Who holds it | What it does |
| --- | --- | --- |
| Burp CA private key | Burp | Signs interception certificates |
| Generated host certificate private key | Burp | Proves "I am example.com" to the browser on TLS Connection A |
| Real destination server private key | `example.com` | Proves the origin on TLS Connection B. **Burp does not need it.** |

Burp does not mint a new CA per site. One CA, many per-host leaves. Trusting that CA is a lab decision: you changed the browser's trust boundary. An attacker CA that is *not* in the trust store never gets this far.

## The TLS Split

This is the whole architecture.

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

![Two independent TLS connections with plaintext only inside Burp](assets/burp/d-two-tls.svg)

**Browser → Burp (TLS Connection A).** Burp presents a certificate for the destination hostname, signed by the Burp CA. The browser trusts that CA, so the handshake completes. Burp is the TLS server on this hop. The origin never sees this leaf.

**Burp → Server (TLS Connection B).** Burp establishes a separate TLS connection to the real server. It receives the actual server certificate and validates it according to its TLS configuration (trust, hostname, validity). Burp is the TLS client on this hop. Custom or enterprise CAs can be added in Burp's TLS settings. Failure here is an upstream problem: Connection A may already be up, so the browser sees an error *from Burp*, not a rejection of the origin leaf.

| | TLS Connection A | TLS Connection B |
| --- | --- | --- |
| Endpoints | Browser ↔ Burp | Burp ↔ Server |
| Certificate the TLS client sees | Burp-generated host cert, issuer = Burp CA | The real `example.com` certificate |
| Who is TLS server | Burp | The origin |

<aside class="call-box"><p><strong>Burp does not decrypt the original browser-to-server TLS session. It terminates one TLS connection and establishes another.</strong></p></aside>

There is no original end-to-end TLS session on this path for Burp to "break." Connection A and Connection B never share cryptographic state.

<aside class="note-box"><p><strong>TLS 1.2 and TLS 1.3</strong> differ in handshake design and cryptographic details, but the key point for Burp interception remains the same: browser→Burp and Burp→server are separate TLS connections with independently established cryptographic state.</p></aside>

## What Happens to the Keys?

TLS derives traffic-protection keys/secrets independently for each connection. Do not picture a literal encryption key being shipped from the server to Burp. Long-term private keys authenticate the handshake. Traffic-protection secrets are established per connection, and they are not the same object as the CA key or the origin key.

**Browser ↔ Burp** has its own TLS cryptographic state.

**Burp ↔ Server** has its own TLS cryptographic state.

Stealing the origin private key later does not unwind Connection A, and possessing Connection A's secrets does not let you read Connection B. They were never the same handshake.

Burp does **not** need Google's private key, Cloudflare's private key, or the destination server's private key.

Burp **does** have its own CA private key, the private key for the generated host certificate, and its own TLS connection to the destination. That is enough to terminate A, read HTTP, and speak TLS on B. That is also why the Burp CA private key is the dangerous lab object: anyone who has it, plus a victim that trusts that CA, can mint host certificates and run the same two-connection intercept.

## Request → Burp → Server

Take `GET /account` to `https://example.com/account`, with the browser pointed at Burp.

```
Browser
   │
   │ GET /account
   │ (protected by TLS Connection A)
   ▼
 Burp
   │
   │ HTTP visible to Burp
   │ inspect / modify / drop / Repeater
   ▼
 Server
   (protected by TLS Connection B)
```

Because Burp terminated the browser-side TLS connection, the HTTP message is available at the proxy layer:

```
GET /account HTTP/1.1
Host: example.com
Cookie: sid=abc123
```

That is why Intercept, Logger, Repeater, and match-and-replace exist. They operate on HTTP after Connection A is terminated, not on TLS records. You can change method, path, headers, cookies, body, or `Authorization`, then let Burp send the result on Connection B. You cannot do that until A is terminated. Passthrough never gets here.

The response is the same split in reverse:

```
Server
   │
   │ TLS B
   ▼
 Burp
   │
   │ inspect / modify
   │
   │ TLS A
   ▼
 Browser
```

![Request lifecycle](assets/burp/d-request.svg)

Intercept ON vs OFF does not change the TLS architecture. Both connections still exist. Intercept only pauses the already-terminated HTTP message before Burp forwards it on Connection B.

## Why HTTPS Still Looks Normal

If Burp is reading plaintext, why does the browser still show HTTPS?

Because **Browser ↔ Burp is still TLS**. The lock is honest about that hop. The plaintext exists *inside Burp* after TLS termination, not on the Browser ↔ Burp wire as HTTP.

```
Browser
   │ encrypted (TLS A)
   ▼
 Burp
   │ plaintext inside proxy processing
   ▼
 Burp
   │ encrypted (TLS B)
   ▼
 Server
```

A network observer between browser and Burp still sees TLS records. A network observer between Burp and the server still sees TLS records. The HTTP exists only in Burp's process after it has become an endpoint of Connection A.

Burp is not converting HTTPS into HTTP between the browser and the server. It is terminating TLS on one side and creating another TLS connection on the other.

## When Interception Breaks

Trusting the Burp CA is necessary for intercept in a normal browser TLS stack. It is not sufficient in every client.

### Certificate pinning

Some applications do not rely only on the platform CA trust store. They require a specific certificate or public-key identity (often an SPKI pin). Mobile apps do this so a user-installed CA, or a corporate inspection root, cannot silently become `api.example.com`. The Burp-generated host certificate will not match, so the app aborts TLS even though the Burp CA is trusted. Pinning is an extra identity check, not "the CA isn't trusted." High-level lab options stay at that layer: a debug build with the pin off, an instrumented client, or TLS passthrough for that host.

### TLS passthrough

With TLS passthrough, Burp forwards encrypted TLS without terminating it. HTTP is not available to Burp. No Intercept, no body history, no Repeater from that hop. Use it for pinned hosts, or when the origin is sensitive to the TLS fingerprint of Burp's stack rather than the browser's.

```
Browser ───── encrypted TLS ─────> Server
                     │
                    Burp
                 forwarding
```

![Passthrough forwards TLS records without terminating them](assets/burp/d-passthrough.svg)

### HTTP/2 and ALPN

ALPN lets each TLS connection negotiate the application protocol (`h2`, `http/1.1`). Because browser→Burp and Burp→server are separate TLS connections, that negotiation happens independently on each hop. Do not assume the browser and the origin agreed on the same protocol "through" Burp.

### Invisible proxying

Invisible proxying is for clients that are not HTTP-proxy-aware. Traffic is redirected at the network layer to a Burp listener. There is no `CONNECT`. When available, information such as SNI can help identify the intended hostname. SNI is not always present, and invisible proxying does not always depend on it.

### Other reasons interception may fail

Mutual TLS adds client-certificate authentication, which introduces another trust relationship that a proxy must handle. Upstream certificate validation can also fail independently of Connection A: an expired or untrusted origin certificate is Burp's problem as a TLS client, not the browser rejecting the real leaf.

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
