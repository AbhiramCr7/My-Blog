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
description: "How Burp Suite lets you inspect encrypted web traffic"
---

## What this article covers

This article answers one question: if HTTPS encrypts web traffic, how can [Burp Suite](https://portswigger.net/burp) still show you the request?

We will cover, in this order:

1. The puzzle: a login that HTTPS should hide, but Burp can still display.
2. How your browser first talks to Burp (a proxy, not the website).
3. Why the browser trusts Burp (Burp's own certificate authority).
4. The certificate Burp creates for the site you visited.
5. The two separate secure connections: browser to Burp, then Burp to the website.
6. Why Burp does not need the website's private key.
7. One full request, step by step.
8. What can stop Burp from reading HTTPS.

You do not need to have used Burp before. You do not need to already know TLS. Each idea is explained in ordinary English first, then with the correct technical words.

**By the end you will be able to explain:**

- why Burp can read HTTPS requests
- why the browser trusts Burp
- why two separate encrypted connections exist
- why Burp does not need the website's private key
- the difference between intercepting TLS and only forwarding it

## How Can Burp Read HTTPS?

Imagine you log in to a website. You type a username and a password. Your browser sends that login to the site, and HTTPS is supposed to protect it while it travels across the internet. Anyone sitting on the network should see scrambled data, not your password.

Now open Burp Suite, a tool security testers use to inspect how a web application behaves. Point your browser at Burp and log in again. In Burp you can read the same request. You can see the path, the headers, even the password field. You can change a value and send it on.

That should feel wrong.

If HTTPS encrypts the information, how can Burp read it? Does Burp know the website's secret key? Does it somehow break HTTPS?

Neither explanation is correct.

The interesting part is not a magical decryptor. It is what happens *between* your browser and the website. Let's follow one request and see what Burp actually does.

A useful picture is a locked box.

You want to send a box of papers to a company. You lock it so a stranger on the road cannot read the papers. Now imagine you first hand the box to a trusted inspection desk. The desk can open *its* lock, look at the papers, then put them into a new locked box and send that box to the company.

Burp is that desk. It does not steal the company's lock. It does not pick the original lock on a box that was meant to go straight to the company. Your browser locks the box for Burp. Burp opens that box, inspects the papers, then locks a new box for the website.

The analogy stops here. Real HTTPS uses cryptography and certificates, not physical locks. The rest of this article is about the software.

**Normally**, your browser and the website set up one secure connection. The information is protected while it travels between them.

```
Browser  →  encrypted connection  →  Website
```

**With Burp**, your browser makes a secure connection to Burp. Burp can read the request because it is the other end of that connection. Burp then sends the request to the website through a *second* secure connection.

```
Browser  →  secure connection  →  Burp  →  secure connection  →  Website
```

That is the whole trick, in ordinary language. Your browser is no longer talking directly to the website. It is talking to Burp. Burp talks to the website.

![Normal HTTPS versus Burp: one secure hop versus two](assets/burp/d-normal-vs-burp.svg)

A **proxy** is a program that sits in the middle of traffic. You configure the browser to send requests to Burp instead of sending them straight to websites. Burp Suite's Proxy tool is that middle program.

A **secure connection** here means TLS. TLS is the protocol that HTTPS uses to encrypt data and to check who is on the other end. HTTPS is ordinary HTTP (the language of web requests) carried inside TLS.

We will call the two connections **TLS connection A** (browser to Burp) and **TLS connection B** (Burp to website). Keep those labels. Everything else in the article hangs on them.

## First, Your Browser Connects to Burp

Before the browser starts the secure connection, it needs to tell Burp which website it wants to reach.

This is the usual flow when a browser is set to use Burp as an **explicit HTTP proxy**. "Explicit" means you configured the browser (or the system) to use Burp on purpose, typically at `127.0.0.1` port `8080`. A **port** is a numbered door on a computer. `443` is the usual door for HTTPS. `8080` is the door Burp listens on by default.

The browser often sends this HTTP message *to Burp*, not to the website:

```
CONNECT example.com:443 HTTP/1.1
Host: example.com:443
```

Read it in plain English:

- `CONNECT` asks the proxy to set up a path to a destination.
- `example.com` is the website hostname, the name you typed or clicked.
- `443` is the usual HTTPS port on that website.

Burp replies:

```
HTTP/1.1 200 Connection Established
```

That means Burp has agreed to open a **tunnel**: a TCP path through the proxy toward `example.com:443`. TCP is the basic reliable pipe the internet uses. After this reply, the browser can start TLS through that tunnel.

`CONNECT` is a **proxy** mechanism. It is not part of TLS. It is not sent to `example.com`. Not every HTTPS connection begins with `CONNECT`. Apps that are not set up to use an HTTP proxy never send it. This section is about the common browser-plus-Burp setup.

After `200 Connection Established`, the browser starts the TLS handshake with whoever is at the other end of the tunnel. From the browser's point of view, that someone is Burp. So Burp must present a certificate the browser will accept for `example.com`. That is the next question.

## Why Does the Browser Trust Burp?

If Burp presents a certificate that says "I am example.com", why doesn't the browser immediately reject it?

Your browser keeps a list of **certificate authorities** it trusts. A certificate authority (CA) is an organisation or system that can issue certificates browsers may accept. A **certificate** is a signed statement that binds a name, like `example.com`, to a public key. It is not itself a secret. It is a claim the browser can check.

A website normally presents a certificate issued by a public CA (the kind already in your browser). The browser checks the name, the dates, the signature, and whether the chain of signatures leads back to a CA it already trusts.

Burp has its own CA, called the **Burp CA**. On first run, Burp creates one CA for that installation. You can install that CA in your testing browser or device so the browser treats it as trusted.

Once the Burp CA is trusted, Burp can create a certificate for the hostname you requested and **sign** it with the Burp CA. Signing, in simple English: the CA uses its private key to create a digital signature. The browser verifies that signature with the CA's public key. If the signature checks out, and the other certificate checks pass, the browser can accept the certificate.

```
Browser trusts Burp CA
          |
          v
Burp CA signs a certificate for example.com
          |
          v
Burp presents that certificate to the browser
```

![One Burp CA, many host certificates](assets/burp/d-ca-tree.svg)

This generated certificate is for the **browser-to-Burp** connection. Burp does not send it to the real website as that website's identity. The real website still has its own certificate.

An attacker can create a CA and sign a certificate for `example.com` too. A normal browser still rejects it, because that attacker CA is not in the trust list. Burp works in a lab because **you** installed the Burp CA. The browser is not being fooled by a "legitimate-looking" certificate. You changed who it is allowed to trust.

## The Certificate Burp Creates

The certificate Burp shows the browser is created **on the fly**. That means it is generated or reused when the connection needs it, for the hostname being requested.

The sequence:

1. You visit `https://example.com`.
2. Your browser connects through Burp.
3. Burp prepares a certificate for `example.com`.
4. That certificate is signed by the Burp CA.
5. Your browser checks the certificate and whether it traces back to a CA it trusts. It also checks other details, such as the name and the dates.
6. The browser and Burp establish their secure connection.

Three different keys, three jobs:

| What | Who has it | What it is for |
| --- | --- | --- |
| Burp CA private key | Burp | Signs the certificates Burp creates for hostnames |
| Generated host certificate private key | Burp | Used on the browser-to-Burp connection, for the identity of that generated certificate |
| Website's private key | The real website | Used on the website's own TLS connection. **Burp does not need it.** |

Burp does not create a new CA for every website. One CA, many host certificates.

We are not going into the full X.509 certificate format here. The architecture point is enough: the leaf the browser sees is a **Burp-generated, CA-signed certificate** for the name you requested. It is not the real website's certificate.

How does Burp know the name to put on that certificate? On the explicit-proxy path, `CONNECT` already said `example.com:443`. TLS can also include **SNI** (Server Name Indication), an optional extension in the first TLS message that can carry the hostname. SNI is not a certificate. SNI is not always present. When it is present, it usually matches the name from `CONNECT`.

## The Two Secure Connections

Your browser is not talking directly to the website anymore. It is securely connected to Burp. Burp reads the request and creates another secure connection to the website. These are two separate connections.

```
Browser
   |
   | Secure connection A  (TLS)
   v
 Burp
   |
   | Secure connection B  (TLS)
   v
Website
```

![Two independent TLS connections, with the HTTP message visible only inside Burp](assets/burp/d-two-tls.svg)

**Connection A: browser to Burp.** The browser trusts the Burp-generated certificate because the Burp CA is trusted. The browser and Burp establish TLS. Encrypted data still travels on the wire between them. Once that data reaches Burp, Burp can read the HTTP request, because Burp is the other end of the browser's secure connection.

**Connection B: Burp to website.** Burp opens a separate TLS connection to the real website. The website presents its real certificate. Burp checks that certificate according to its TLS settings (whether it trusts the issuer, whether the name matches, whether the certificate is still valid). The two sides then protect that hop with their own encryption keys. Burp does not blindly accept every server certificate.

**TLS termination** means one end of a TLS connection is reached, and the data is decrypted there so the program can work with it. Burp terminates connection A. That is why the Proxy tab can show `GET /account` instead of TLS records.

Burp does not break the original HTTPS encryption. It creates two separate secure connections, with Burp sitting between them. There is no single browser-to-server TLS connection that Burp decrypts.

## Does Burp Know the Website's Private Key?

No. Burp does not need the real website's private key.

Each connection has its own encryption keys. The keys protecting the browser-to-Burp hop are different from the keys protecting the Burp-to-website hop. In technical terms, TLS derives **traffic-protection keys** independently for each connection. Those keys are established during each handshake. They are not a single secret copied off the website, and they are not simply posted across the network as "the session key."

Remember the three keys from earlier:

- The **Burp CA private key** signs generated certificates. It does not encrypt your HTTP request.
- The **generated host certificate's private key** belongs to the certificate Burp showed the browser. TLS versions differ in how they use long-term keys during the handshake. The useful fact for this article is that this key is Burp's, for connection A, not the website's.
- The **website's private key** stays on the website. Burp does not need it to open connection B. On that hop Burp is just a TLS client, the same role your browser usually plays.

If someone later stole the website's private key, that would not automatically unwind connection A. If someone had connection A's keys, that would not automatically let them read connection B. The two handshakes were never the same handshake.

That is also why the Burp CA private key is the sensitive lab object. Anyone who has it, and a browser that trusts that CA, can mint host certificates and sit in the same position Burp sits in.

## Follow a Real Request

You open `https://example.com/account`. The browser is using Burp as its proxy.

```
GET /account HTTP/1.1
Host: example.com
Cookie: session=...
```

That is a simplified illustration of what Burp can display. A person watching the network between the browser and Burp still sees TLS records, not this HTTP. Burp sees the HTTP because Burp is the TLS endpoint for the browser-side connection. An **endpoint** is one of the two programs that actually speak TLS with each other.

Timeline:

1. The browser asks Burp to connect to `example.com` (`CONNECT`, on an explicit HTTP proxy).
2. Burp and the browser establish TLS connection A. Burp presents the generated certificate for `example.com`.
3. The browser sends `GET /account` protected by connection A.
4. Burp processes the HTTP request and can show it in the Proxy tab.
5. If Intercept is on, Burp can pause the message so you can inspect or edit it.
6. Burp forwards the request through TLS connection B to the website.
7. The website responds to Burp.
8. Burp processes the response and sends it to the browser through connection A.

![One request through Burp](assets/burp/d-request.svg)

**Intercept ON** pauses messages for you to click Forward (or drop, or edit). **Intercept OFF** still lets Burp sit in the middle and terminate TLS. History still fills. You can still send the message to Repeater. There is just no pause. Turning Intercept off does not mean TLS proxying is off.

## What Can Stop Burp From Reading HTTPS?

Trusting the Burp CA is enough for a normal browser. It is not enough for every app.

**Certificate pinning.** Some apps do not stop at "is this signed by a CA I trust?" They also require a specific certificate or public key, often baked into the app. That extra check is **pinning**. The Burp-generated certificate will not match, so the app refuses the connection even though the Burp CA is trusted. Pinning is not the same as "the CA isn't trusted."

**TLS passthrough.** Burp can be told to forward encrypted TLS without ending the connection. Then Burp is not an endpoint. It cannot read or change the HTTP inside that traffic. Use this when you *don't* want to intercept a host.

```
Browser  →  encrypted TLS  →  Website
                (Burp only forwards)
```

TLS passthrough is the opposite of the architecture in this article.

**Mutual TLS (mTLS).** Some servers also require the *client* to prove its identity with a certificate. That is a second authentication step. The certificate your browser might use on connection A does not automatically appear on connection B. The proxy has to present a client certificate upstream if the server asks for one.

**ALPN and HTTP/2.** During TLS, the two sides can agree which HTTP version to use. That agreement is **ALPN** (Application-Layer Protocol Negotiation). Typical choices are HTTP/1.1 and HTTP/2. Because connection A and connection B are separate, each hop can pick its own version.

**Invisible proxying and SNI.** Some clients are not configured to use an HTTP proxy, so they never send `CONNECT`. **Invisible proxying** is a way to send that traffic to Burp by routing, not by browser proxy settings. When available, TLS information such as SNI can help identify the hostname. SNI is not guaranteed.

These topics can be their own articles. Here they only answer "when does the two-connection picture fail?"

## Put It All Together

Back to the login.

The browser encrypts its request for the connection it has with Burp. Burp is trusted to handle that connection, so it can read the request, including a password field. Burp then sends the request to the real website over a separate encrypted connection. The website talks to Burp. Burp passes the response back to the browser.

```
Browser
   |
   | TLS connection A
   v
 Burp
   |
   | TLS connection B
   v
Website
```

Keep these distinctions straight:

- `CONNECT` is a proxy mechanism, not TLS.
- SNI can indicate a hostname. It is not a certificate.
- The Burp CA is different from the website's certificate authority.
- The certificate Burp presents to the browser is different from the real website's certificate.
- Connection A is different from connection B.
- TLS interception (Burp ends the browser's TLS) is different from TLS passthrough (Burp only forwards).
- Intercept ON/OFF controls the manual pause, not simply whether TLS is proxied.

Burp does not need to break HTTPS. It becomes the browser's trusted secure endpoint, reads the request, and sends it onward through a second secure connection.
