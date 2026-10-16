---
title: "Behind the scenes: how Burp Suite actually reads HTTPS"
date: 2026-10-16 23:45:00 +0530
author: 0xAbhiram
tags:
  - Burp Suite
  - HTTPS
  - Proxy
  - Product Security
  - Web Security
categories:
  - Security Engineering
description: "Everyone knows how to hit Intercept. This is the backend: two HTTPS conversations, a stamp Burp made on your machine, and the plaintext sitting between them."
---

Everyone in this field has turned Intercept on. The request freezes. You change a cookie. You hit Forward. The page loads.

Almost nobody can say what Burp did to *open* that request. HTTPS was supposed to stop a middle box from reading it. So how is the body sitting there in plain text?

This is that story. No download steps. No “click this menu.” Just the machine.

## What people think is happening

It feels like Burp sits on the wire and “unlocks” HTTPS.

That is not what happens. Burp cannot unlock a conversation it is not part of. If the browser really spoke HTTPS only to `shop.test`, Burp would see noise.

So Burp does something ruder, and more honest: **it becomes the website toward your browser, and it becomes the browser toward the website.** Two talks. Two locks. Burp is in both rooms.

![Where Burp sits](assets/burp/01-where.png)

## Start from zero: what HTTPS even is

An HTTP request is just text:

```
GET /login HTTP/1.1
Host: shop.test
Cookie: session=abc
```

On plain HTTP that text travels as-is. Anyone in the path can read the cookie. Burp can too, with no extra work.

HTTPS is the same text, wrapped in TLS. TLS does two jobs:

1. Mix the bytes so a stranger on the path cannot read them.
2. Prove the other end is really `shop.test`, using a signed identity (a certificate).

![HTTP versus HTTPS](assets/burp/02-http-https.png)

If there is only one wrap, from browser to real server, Burp is the stranger. It sees noise. To see text, Burp has to be an *end* of the wrap, not a spectator.

## The architecture, in one picture

Inside Burp, for one HTTPS tab, you roughly have:

1. **A listener** — a local proxy socket (usually `127.0.0.1:8080`). The browser sends work here on purpose.
2. **A name peek** — for HTTPS the first bytes are not TLS yet. They are `CONNECT shop.test:443`. That is how Burp learns the hostname.
3. **A fake shop.test** — Burp plays TLS *server* toward the browser, using an identity it invented for that name.
4. **A real client** — Burp plays TLS *client* toward the real `shop.test`, like any other program on your laptop.
5. **A lobby** — after decrypting the browser side, the HTTP sits in memory as text. History, Intercept, Repeater all look at this lobby.
6. **A send** — the (maybe edited) text is wrapped again for the real server.

![Two separate locks](assets/burp/04-two-tls.png)

Call the browser wrap **lock A**. Call the server wrap **lock B**. Different keys. Burp holds both. The browser never gets B. The server never gets A.

That is the whole product, minus the UI.

## How the name arrives: CONNECT

The browser does not start TLS at random. It asks the proxy to open a pipe:

```
CONNECT shop.test:443 HTTP/1.1
```

Burp says `200 Connection Established`. Then the browser starts TLS on that same socket. As far as Chrome is concerned, “the server” is whoever answered. That whoever is Burp.

In the first TLS message (ClientHello) there is a field called **SNI**. It is just the hostname: `shop.test`. Burp copies that string onto the identity it is about to hand back.

![CONNECT then TLS](assets/burp/03-connect.png)

No CONNECT (some mobile apps, some thick clients) and Burp cannot see the name before TLS starts. That is why “invisible proxy” feels cursed. The rest of this post assumes a normal browser proxy, which always sends CONNECT first.

## How Burp invents a website identity

TLS will not finish unless the “server” shows a signed identity for `shop.test`. Burp does not have the real site’s private key. It will never have it. So it makes its own.

Two pieces, easy to mix up:

**The stamp (made once).** The first time Burp runs, it creates a long-term stamp on disk — its own little certificate authority. That stamp is self-signed. “I vouch for myself.” Public half is what a browser can learn to trust. Private half never leaves the machine. That private half is the pen.

**The shop.test paper (made per site).** When SNI says shop.test, Burp:

1. Makes a fresh key pair for this host. The private half stays in Burp. This is what Burp will use as the TLS server toward the browser.
2. Writes a paper: name = shop.test, plus dates, plus that new public key, issuer = Burp’s stamp.
3. Hashes the paper. Signs the hash with the **stamp’s private key**.
4. Sends that paper to the browser in the handshake.

![Stamp versus per-site paper](assets/burp/05-certs.png)

![How the signature is made](assets/burp/10-sign.png)

The browser already has the stamp in its trust pile (Burp’s own browser ships that way; an external browser only works if that stamp was added). It checks:

- does this paper say shop.test?
- did the stamp I trust actually sign it?
- are the dates sane?

If yes, it agrees to share **session key A** with whoever holds the shop.test private key. That is Burp. Lock A is live.

Notice: the per-site paper is **not** self-signed. Only the stamp is. One trusted stamp covers every hostname Burp prints. That is why you do not get a new scary warning per site once the stamp is trusted.

On lock B, Burp is a normal client. It talks to the real server, checks the *real* paper the usual way, and gets **session key B**.

![The keys](assets/burp/09-keys.png)

- Stamp keys — long term, sign papers.
- Host keys — per site, prove “I am shop.test” to the browser.
- Session key A — this visit, browser ↔ Burp, encrypts the actual HTTP.
- Session key B — this visit, Burp ↔ server, encrypts the actual HTTP.

The papers are for trust. The session keys are for hiding the body. Mixing those two is how people start saying “Burp broke AES.” It did not. It was invited into both handshakes.

## How intercept actually reads a request

This is the part everyone uses and almost nobody can draw.

![One request: open A, copy, lock B](assets/burp/11-crypto.png)

1. Browser takes `GET /login …` and encrypts it with session key A. On the wire to `127.0.0.1:8080` it is ciphertext.
2. Burp’s TLS server for lock A decrypts with A. The bytes in RAM are now ordinary HTTP.
3. **That RAM copy is Intercept.** Not a third protocol. A pause on a buffer. If Intercept is off, the buffer still exists — History just logs it and the code keeps walking. If Intercept is on, the thread waits until you Forward, Drop, or edit.
4. Burp’s TLS client for lock B encrypts that buffer (or your edit) with session key B and sends it to the real IP.
5. The real server decrypts with B. It never saw A. As far as it is concerned a client on your laptop spoke HTTPS. That client was Burp.

The response is the same movie backwards: decrypt B, maybe pause again, encrypt A, browser renders.

Edit a header in Intercept and you are not “hacking TLS.” You are changing the lobby copy before it gets wrapped for lock B. Burp will often fix `Content-Length` for you because you just changed the body size.

![The path, end to end](assets/burp/06-full-flow.png)

## What Intercept is not

The proxy is the path. Intercept is a brake on that path.

With Intercept off, every HTTPS request still does decrypt-A / encrypt-B. You still get HTTP history. You just do not wait.

With Intercept on, matching messages stick in the lobby. That is why a page “hangs.” Something is sitting in the tab.

Repeater, Intruder, Logger all eat the same lobby copy. They are not separate magic tunnels. They are other windows onto step 3.

## When Burp refuses to open it

Sometimes lock A never comes up.

**Certificate pinning.** The app does not care that a trusted stamp signed the paper. It wants *this exact* public key, or *this exact* real stamp. Burp’s shop.test paper fails. The client drops the handshake. That is the app doing its job.

**Pass through.** You tell Burp not to play TLS server for that host. It forwards the TLS records as blobs. No session key A. No lobby. History cannot show HTTP. The server sees the browser’s real TLS fingerprint, which some bot checks want.

![Pass through leaves the lock closed](assets/burp/08-passthrough.png)

## From zero, one more time

- HTTPS is HTTP plus a lock plus a name check.
- A lock only opens for an endpoint of the handshake.
- Burp becomes that endpoint toward you, and a separate endpoint toward the site.
- CONNECT + SNI tell it which name to put on the fake paper.
- A stamp made once signs every fake paper.
- Session key A unwraps the browser. Session key B wraps the server.
- Intercept is a pause on the unwrapped HTTP, not the lock itself.

You already knew the click. That is the machinery behind it.
