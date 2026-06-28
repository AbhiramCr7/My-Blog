---
title: "How My Team Uses Claude to Automate GRC Work — TPRM Sheets, Security Questionnaires, and Shared AI Workflows"
date: 2026-06-28 09:00:00 +0530
author: 0xAbhiram
risk: MEDIUM
thumbnail: /img/cyber-bg.jpg
summary: How we use Claude Cowork to automate TPRM questionnaire responses — cutting completion time from 4 hours to 30 minutes with policy-grounded, consistent answers.
vectors:
  - GRC Automation
  - AI-Assisted Workflows
  - TPRM
  - Security Questionnaires
tags:
  - GRC
  - TPRM
  - Claude
  - AI
  - Security Automation
  - Cowork
  - AppSec
categories:
  - Security Engineering
description: How we use Claude Cowork to automate TPRM questionnaire responses — cutting completion time from 4 hours to 30 minutes with policy-grounded, consistent answers.
---

# How My Team Uses Claude to Automate GRC Work — TPRM Sheets, Security Questionnaires, and Shared AI Workflows

GRC work is repetitive by design. Every enterprise customer asks roughly the same 150 questions in a slightly different spreadsheet. Every TPRM assessment wants the same information — your ISO/SOC2 status, your data retention policy, your incident response SLA, your encryption standards — just formatted differently, with different column names, sometimes in Excel, sometimes in a web portal, sometimes in a PDF form.

For a long time, filling these was pure manual labor. Someone on the security team would open the spreadsheet, read each question, pull up our policy documents, write a response, move to the next row, repeat. A single TPRM sheet could take half a day.

Then we started using Claude. Specifically, Claude via **Cowork** — Anthropic's desktop tool that gives Claude direct file access and lets you work with documents, spreadsheets, and context that lives on your machine. This post is about what that changed, how we set it up, and how we scaled it across the team.

---

## The Problem with TPRM Sheets at Scale

A Third-Party Risk Management (TPRM) questionnaire is a document an enterprise sends to vendors asking them to prove they're secure. Banks, large enterprises, and regulated industries all have them. If you're a B2B SaaS company selling into these sectors, you fill a lot of them.

The typical sheet has sections like:

- **Information Security**: Encryption, access control, vulnerability management
- **Data Privacy**: Data residency, retention, deletion, DPDP/GDPR compliance
- **Business Continuity**: RTO/RPO, DR testing, incident response
- **Third-Party Risk**: Your own vendor management, sub-processors
- **Compliance**: ISO 27001, SOC 2, certifications in scope

Each question has a Yes/No/Partial answer column, a Comments/Evidence column, and sometimes a Document Reference column. There can be anywhere from 80 to 400 rows.

The answers don't change much between customers — your encryption standard doesn't change because a different bank is asking. But extracting the right answer from your policy documents, framing it correctly for the question, and doing that 200 times in a row is exhausting and error-prone.

---

## Where Claude Comes In

Claude, when given your security policies and a TPRM sheet, can read both and fill the questionnaire — accurately, consistently, and in minutes instead of hours.

Here's the exact workflow we use with **Claude Cowork**:

### Step 1: Build Your Context Library

Before anything else, gather your organization's core security documents into a folder:

- Information Security Policy
- Data Classification Policy
- Incident Response Plan
- Business Continuity / DR Plan
- Access Control Policy
- Vendor Management Policy
- Any current certifications (ISO 27001 scope, SOC 2 report summary)
- A "standard answers" document — a running list of approved responses to common questions

You upload these to Claude Cowork once. Claude reads them and holds that context throughout your session. Every answer it gives is grounded in your actual policies, not hallucinated.

### Step 2: Upload the TPRM Sheet

Drop the customer's TPRM spreadsheet into Cowork. Claude reads the structure — columns, sections, row-by-row questions — and understands what kind of answer goes where.

A simple prompt gets you started:

```
Here is our TPRM questionnaire from [customer].
Fill in every row using our security policies I've shared.
For each row:
- Column B: Yes / No / Partial / N/A
- Column C: A 1-3 sentence explanation based on our actual policies
- Column D: Reference the specific policy document by name
Flag any question where you're unsure — don't guess.
```

Claude works through the sheet section by section. Where it's confident (encryption standards, access control, certifications), it fills in complete answers. Where a question is ambiguous or the answer requires a judgment call, it flags the row and explains why.

### Step 3: Review the Flags

This is the most important part of the workflow. You don't review every row — you review only what Claude flagged. In practice, out of a 200-row sheet, Claude will flag 10-20 rows that genuinely need a human decision. The other 180 are done.

Those 10-20 flags are often the most important questions anyway — compensating controls, exceptions, questions about subprocessors in specific jurisdictions, questions where your answer might differ by product line.

You handle those, Claude fills the rest. What used to take 4 hours now takes 30-40 minutes.

---

## Collaboration: Sharing Claude Sessions with the Team

This is where things get interesting.

In Cowork, you can share a session — the full conversation, context, and uploaded documents — with other team members. This means the context you've built (policies uploaded, answers refined, flags resolved) doesn't have to be rebuilt by the next person who opens a TPRM sheet.

### How We Use Shared Sessions

**1. A single trained session per document set**

One team member sets up the "GRC context" session — uploads all policy documents, adds the standard answers file, and does a few test runs to tune Claude's response style (tone, length, format of answers). That session is then shared with the rest of the team.

Every new TPRM sheet goes into this session. Claude already knows your policies. You just upload the new sheet and run.

**2. Collaborative review in the same chat**

When a sheet has complex flags, two people can work in the same shared session simultaneously — one reviewing Claude's draft answers, the other providing policy context through the chat. Claude sees both inputs and refines accordingly. This is faster than a review meeting.

**3. Knowledge transfer for new team members**

When someone new joins the security team, they don't start from zero. They read the shared Claude session — the conversation history shows not just the outputs but the reasoning, the edge cases that came up, the answers we debated. It's a live documentation of how GRC decisions are made at the company.

---

## What Claude Actually Does Well in GRC Context

After using this workflow across many different questionnaire formats, here's an honest breakdown:

### Excellent

- Mapping a question to the right section of a policy document
- Writing consistent, professional responses at the right level of detail
- Spotting when the same question is asked twice in different phrasing
- Formatting answers to match the required column structure
- Translating dense policy language into clear questionnaire responses

### Good with Guidance

- Answering questions about certifications in scope (tell Claude your exact scope)
- Questions about sub-processors and data flows (give Claude your current sub-processor list)
- Questions requiring a "Yes" with caveats — Claude will draft the caveat, you review it

### Needs Human Judgment

- Questions where your answer is "Partial" and the customer might push back
- Questions that require interpreting a regulatory requirement (DPDP, SEBI CSCRF) against your current posture
- Questions where the honest answer is "No, but here's our compensating control"

The last category is exactly what you want humans reviewing. The 80% that Claude handles confidently is precisely the work that was draining the team before.

---

## Practical Setup: Getting Claude Cowork Ready for GRC

If you want to replicate this, here's a concrete starting point.

**Folder structure on your machine:**

```
/grc-context/
  policies/
    information-security-policy.pdf
    access-control-policy.pdf
    incident-response-plan.pdf
    bcp-dr-plan.pdf
    data-classification-policy.pdf
  certifications/
    iso27001-scope.pdf
    soc2-summary.md
  standard-answers/
    standard-answers.md   ← your running approved-answers document
```

**The `standard-answers.md` file** is worth building carefully. It's a markdown file with sections like:

```markdown
## Encryption
We use AES-256 for data at rest and TLS 1.2/1.3 for data in transit across all services.
Key management is handled via [KMS solution].

## Penetration Testing
We conduct annual third-party VAPT and internal vulnerability scans on a quarterly basis.

## Incident Response SLA
Critical incidents: 1-hour detection, 4-hour containment target.
Customer notification: within 72 hours of confirmed breach.

## Data Residency
Customer data is stored in [region(s)]. Cross-region replication is [enabled/disabled] by default.
```

Claude references this file first before going to longer policy documents, which speeds up responses and keeps answers consistent.

**Starting prompt for a new sheet:**

```
I'm going to give you a TPRM questionnaire. You have access to:
- Our security policies (in /grc-context/policies/)
- Our certifications (in /grc-context/certifications/)
- Our standard approved answers (standard-answers.md)

Rules:
1. Prioritize standard-answers.md — use those exact phrasings where they apply.
2. When pulling from a policy document, cite the document name in Column D.
3. If a question is ambiguous or you're less than 80% confident, write [FLAG: <reason>] in Column C.
4. Don't invent capabilities we don't have. When in doubt, flag.

Here is the questionnaire: [attach file]
```

---

## The Broader Shift: AI as a GRC Team Member

What this workflow represents isn't just automation — it's a fundamentally different way of staffing GRC work.

**Before:** one senior security person reads 200 questions, applies policy knowledge, writes responses, gets reviewed.

**After:** Claude reads 200 questions, applies policy knowledge, writes responses, flags 15 for senior review. Senior person reviews 15 items. Team ships the questionnaire.

The senior security person's judgment is still in the loop — just on the questions that actually need it. The rest of their time goes to the work that can't be automated: understanding what a customer actually cares about, negotiating on compensating controls, deciding whether an exception is acceptable.

The shared session model also creates something valuable that's hard to quantify: **institutional memory that's searchable**. When a new kind of question comes up — say, a customer asks about DPDP compliance for the first time — the session captures how we answered it. The next person who gets the same question finds it in the conversation history. Claude already knows the approved answer.

---

## What's Next

We're still building this out. A few directions we're exploring:

- **A persistent "GRC brain"** — a single long-running Cowork session that accumulates answers over time, so each new questionnaire benefits from all previous ones.
- **Automatic flagging by question type** — training Claude to recognize categories of questions (regulatory, technical, process) and apply different confidence thresholds for each.
- **Draft-to-Jira loop** — once Claude fills a sheet, auto-create a review task in Jira with the flagged rows attached, so the human review step has a trackable ticket.

---

## Summary

GRC questionnaires are a tax on security teams at B2B SaaS companies. The questions are largely the same. The answers are largely the same. The work is largely repetitive.

Claude, given your actual policy documents and a shared working session, turns that work from a half-day task into a 30-minute review. The workflow is:

1. Build a policy context library once.
2. Upload any TPRM sheet and ask Claude to fill it.
3. Review only the flagged rows — the genuinely hard questions.
4. Share the session with your team so the context transfers.

The output is consistent, policy-grounded, and faster than anything we were doing before. And unlike a script or a template, it actually understands the question being asked.
