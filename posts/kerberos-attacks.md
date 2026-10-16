---
title: "Kerberos Attacks: How Identity Tickets Become Paths Through Active Directory"
date: 2026-10-16 21:00:00 +0530
author: 0xAbhiram
risk: HIGH
thumbnail: /img/cyber-bg.jpg
summary: "A follow-up to Active Directory fundamentals — how Kerberos tickets, service accounts and trust in the KDC turn into Kerberoasting, AS-REP roasting and golden tickets, and what actually stops them."
vectors:
  - Kerberoasting
  - AS-REP Roasting
  - Ticket Forgery
  - Service Account Abuse
tags:
  - Kerberos
  - Active Directory
  - Red Team
  - Identity Security
  - AD Security
  - Enterprise Security
  - Trust Boundaries
categories:
  - Security Engineering
description: "A red-team mental model of Kerberos: how TGTs and service tickets work, why Kerberoasting and AS-REP roasting exist by design, and the controls that actually reduce the blast radius."
---

## Why this article exists

The previous log walked through Active Directory as an identity system: forests, domains, OUs, domain controllers, and trust as a graph. It ended by pointing here, because **Kerberos is the protocol that makes that graph move**.

If AD is the map of who is trusted, Kerberos is the paperwork that proves it. Most “AD attacks” that look like magic tricks are just people collecting, requesting, or forging that paperwork.

This is not a command list. It is the same kind of mental model as the last post: how the protocol is supposed to work, where the design leaves room for abuse, and what a Product Security Engineer should actually change.

---

## Kerberos in one picture

Kerberos is a ticket system. A client never sends a password to every server it talks to. It proves itself once to a trusted third party — the **Key Distribution Center (KDC)**, which in a domain lives on the Domain Controller — and then carries tickets.

Three exchanges matter:

1. **AS (Authentication Service)** — “I am who I say I am.” The client walks away with a **Ticket-Granting Ticket (TGT)**.
2. **TGS (Ticket-Granting Service)** — “I need to talk to this service.” The client walks away with a **service ticket**.
3. **AP (Application)** — the client shows that service ticket to the actual server (file share, SQL, HTTP, whatever).

The KDC is trusted because it knows the long-term keys of users and services. Tickets are blobs encrypted with those keys. If you understand *who can decrypt what*, the attacks stop being mysterious.

| Blob | Encrypted with | Who can read it |
| --- | --- | --- |
| TGT | KRBTGT account key | Only the KDC |
| Service ticket | Target service account key | That service, and anyone who has the service’s long-term key |
| Session keys inside | Derived from the user’s key or prior session | The two parties in that hop |

That middle row is the whole of Kerberoasting. The last row, plus KRBTGT, is the whole of golden tickets. Nothing here is a memory-corruption bug. It is the protocol doing what it was designed to do, in an environment it was not designed to survive: a domain full of guessable service passwords and over-trusted accounts.

---

## The TGT is a session, not a password

When a user logs on, the AS exchange proves they know their password **to the KDC**, not to every resource. The KDC returns a TGT, valid for hours by default.

From that moment, the user’s password is not on the wire for ordinary resource access. The TGT is. Steal a live TGT (or the session it represents) and you inherit the user’s access until it expires — without ever learning the password.

That is why credential theft in AD so often targets:

- the **ticket cache** on a workstation (what the user is currently allowed to be);
- the **KRBTGT key** on the KDC (what every TGT is sealed with);
- **service account keys** (what service tickets are sealed with).

Pass-the-ticket is not a clever exploit. It is using a valid ticket from the wrong chair.

---

## Kerberoasting: asking the KDC for ciphertext you can take home

Service Principal Names (SPNs) advertise “this account runs this service.” Any authenticated domain user can ask the TGS for a ticket to an SPN.

The TGS does not ask the service first. It encrypts a ticket with **that service account’s long-term key** and hands it to the requester. The requester cannot read the ticket. They can **take it offline** and try to recover the key — which, for a user-style service account, *is* the password.

That is Kerberoasting:

- The request looks like normal Kerberos traffic.
- The crack happens off the network, so lockouts and live detections on the DC do not fire the way they would for a password-guess against LDAP.
- Success depends on the service password being weak, reused, or never rotated — which is still common because “the app will break if we change it.”

Kerberoasting exists because Kerberos assumes the service’s long-term key is a **high-entropy secret**, not `Spring2020!` on an account that also happens to be in Domain Admins.

### What actually reduces it

- **Group Managed Service Accounts (gMSA)** or equivalent: the platform generates and rotates a 120+ character secret. There is no human-chosen password to roast.
- If a user account must have an SPN, treat its password like a cryptographic key: long, random, rotated, stored in a vault, never in a wiki.
- **AES** instead of RC4 for ticket encryption, so the offline work is against a stronger wrapping.
- **Least privilege on the account.** Roasting a service account that can only run one IIS pool is an incident. Roasting one in Domain Admins is a domain takeover.
- Hunt for **unusual TGS requests** (one user asking for many SPNs, especially from a workstation that does not use those services). The request is the tell; the crack is invisible.

---

## AS-REP roasting: tickets with no pre-authentication

Normally the AS exchange requires **pre-authentication**: the client proves it already knows the password before the KDC returns useful ciphertext.

Some accounts have “Do not require Kerberos preauthentication” set. For those, an attacker who only knows the **account name** can request an AS-REP and take that ciphertext offline, same idea as roasting a service ticket.

This is rarer than Kerberoasting and easier to eliminate: it is a flag on the account, not a protocol requirement. Inventory it. Turn it off unless a specific ancient client still needs it. If something still needs it, that thing is the risk, not the flag.

---

## Delegation: tickets that act for someone else

Kerberos delegation exists so a frontend can call a backend **as the user**. That is a real product requirement (the web server should not connect to the database as itself for every user). It is also how a single compromised service becomes every user who visited it.

Three shapes, getting more dangerous as they get more convenient:

- **Unconstrained delegation** — the service receives a copy of the user’s TGT. Anyone who controls that service can impersonate the user *anywhere in the domain*. This should not exist on modern estates.
- **Constrained delegation** — the service may impersonate the user only toward named backends. Better, still a path in the identity graph.
- **Resource-based constrained delegation (RBCD)** — the *target* decides who may delegate to it. Convenient for cloud-era joins; abusable if the attacker can write that attribute on a computer or service object.

The AD fundamentals post treated permissions as graph edges. Delegation is an edge that says “this node may become those users.” BloodHound-style tools light up because this edge is easy to miss in a GUI and devastating in a path.

---

## Golden and silver tickets: forging the paperwork

If you have the **KRBTGT** key, you can mint TGTs that the KDC will treat as its own. That is a **golden ticket**: a session that never had to log on, for any user, often with a lifetime you choose.

If you have a **service account** key, you can mint service tickets for *that* service. That is a **silver ticket**: the KDC may never see the request. The service itself is convinced.

These are not “first access” attacks. They are **persistence and impersonation after** someone already reached the key. The product-security question is not “how do I forge a ticket in a lab.” It is:

- How hard is KRBTGT to steal (DC security, backup hygiene, who can DCSync)?
- How often is KRBTGT rotated (twice, in sequence, or the old key still validates)?
- Do services **validate PAC and ticket fields** strictly, or accept whatever decrypts?
- Would anyone notice a TGT that never came from an AS-REQ?

Rotation without a second rotation leaves the old KRBTGT valid. A golden ticket minted yesterday still works until both keys have been replaced and the old one dropped. That operational detail is where most “we rotated KRBTGT” stories fail.

---

## How this sits on the identity graph

Put the last article and this one on the same whiteboard:

1. Compromise a low-privilege user (phish, token, local admin on a workstation).
2. Read the graph: groups, ACLs, SPNs, delegation, trusts.
3. Request service tickets for roastable SPNs, or find an account that skips pre-auth.
4. Recover a service password that is also over-privileged.
5. Walk edges (ACL, GPO, delegation, trust) until a path reaches a DC or KRBTGT.
6. Persist with tickets that no longer depend on the original user.

None of those steps require a CVE. They require **identity objects behaving as designed** plus passwords and ACLs that nobody treated as part of the product.

That is why this belongs next to product security, not only “red team lore.” If your product joins a domain, runs under a service account, exposes an SPN, or accepts Kerberos on a backend, **you shipped a Kerberos principal**. Its password policy, group membership, and delegation flags are product decisions.

---

## What a Product Security Engineer should ask

When a service is going into a domain — yours or a customer’s — these questions beat a pile of scanner findings:

- Is this a gMSA (or cloud equivalent), or a user account with an SPN and a human password?
- What groups is it in? Could roasting it become Domain Admin?
- Does it have unconstrained delegation? Could anyone write RBCD on it?
- Does the app need unconstrained anything, or can the backend take a protocol transition to a named SPN?
- Are TGS requests for this SPN logged and alertable when they come from unusual users or hosts?
- If this account is compromised, how do we rotate it without an incident call at 2 a.m.?

Kerberos will not get simpler. The estate can still get boring: managed secrets, thin privileges, no unconstrained delegation, KRBTGT treated like a root CA, and tickets monitored as first-class credentials.

---

## Closing

Kerberoasting, AS-REP roasting, delegation abuse, and golden tickets are not four unrelated tricks. They are four ways to interact with the same objects: **keys the KDC trusts**, and **tickets those keys seal**.

Active Directory made the graph. Kerberos made the tickets. Attackers follow both.

The next time someone says “we should Kerberoast the domain,” translate it: *we should ask whether any service principal is still using a password a person typed.* That is a design review question. It is also a preventable class of incident.
