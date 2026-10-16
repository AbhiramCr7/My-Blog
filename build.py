#!/usr/bin/env python3
"""Builds every page of the journal.

Posts are Markdown files in `posts/`, rendered with `marked`, and the
generated pages are written into `public/` next to the CSS, JS and assets.
Add or edit a post, run `npm run build`, and commit `public/`.
"""
import json, os, re, subprocess
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))

# Public address of the deployed site, e.g. "https://0xabhiram.dev".
# Canonical links, social previews and sitemap.xml are only emitted once set.
SITE_URL = "https://my-blog-beta-rosy.vercel.app"

SITE_NAME = "0xAbhiram Blog"
AUTHOR = {
    "@type": "Person",
    "name": "Abhiram SS",
    "alternateName": "0xAbhiram",
    "sameAs": ["https://github.com/0xabhiram", "https://x.com/0xabhiram"],
}
POSTS_DIR = os.path.join(HERE, "posts")
OUT = os.path.join(HERE, "public")

POSTS = [
    dict(md="grc-blog-post.md", page="post-grc.html", path="~/blog/grc-automation",
         img="post-grc.jpg", log="03", card_title="How My Team Uses Claude to Automate GRC Work",
         card_tags=["GRC", "TPRM", "Security Automation"],
         alt="A night desk where a glowing red AI streams a tall stack of vendor questionnaires into a laptop and out as neatly checked forms"),
    dict(md="Understanding-Active-Directory-from-the-Ground-Up.md", page="post-active-directory.html", path="~/blog/active-directory",
         img="post-ad.jpg", log="02", card_title=None,
         card_tags=["Active Directory", "Kerberos"],
         alt="A glowing domain controller tower branching into domains, organizational units and users, with a key and ticket floating beside it"),
    dict(md="cybersecurity-101.md", page="post-trust.html", path="~/blog/hacking-trust",
         img="post-trust.jpg", log="01", card_title=None,
         card_tags=["Red Team", "Trust Boundaries"],
         alt="A handshake hiding a lockpick in front of a glowing chain with one cracked link"),
]

RENDER_JS = r"""
const fs = require("fs");
const yaml = require("js-yaml");
const { marked } = require("marked");
marked.setOptions({ gfm: true });
const out = {};
for (const file of JSON.parse(process.argv[1])) {
  const raw = fs.readFileSync(process.argv[2] + "/" + file, "utf8");
  const m = raw.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);
  const front = yaml.load(m[1]);
  out[file] = { front: JSON.parse(JSON.stringify(front)), html: marked.parse(m[2]), words: m[2].split(/\s+/).length };
}
process.stdout.write(JSON.stringify(out));
"""

rendered = json.loads(subprocess.run(
    ["node", "-e", RENDER_JS, json.dumps([p["md"] for p in POSTS]), POSTS_DIR],
    cwd=HERE, capture_output=True, text=True, check=True).stdout)
os.chdir(OUT)

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

for p in POSTS:
    r = rendered[p["md"]]
    f = r["front"]
    p["title"] = f["title"]
    p["card_title"] = p["card_title"] or f["title"]
    p["desc"] = f.get("description") or f.get("summary", "")
    p["tags"] = f.get("tags", [])
    d = datetime.fromisoformat(str(f["date"]).replace(" +0530", "+05:30"))
    p["date"] = d.strftime("%Y-%m-%d")
    p["date_long"] = d.strftime("%B %-d, %Y")
    p["mins"] = max(1, round(r["words"] / 220))
    html = r["html"]
    html = re.sub(r'<pre><code class="language-([\w-]+)">', r'<pre data-lang="\1"><code class="language-\1">', html)
    html = re.sub(r"<h1[^>]*>.*?</h1>\s*", "", html, count=1, flags=re.S) if html.lstrip().startswith("<h1") else html
    html = html.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
    p["html"] = html

POSTS.sort(key=lambda p: p["date"], reverse=True)
slug = lambda t: re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")

def abs_url(rel):
    return f"{SITE_URL.rstrip('/')}/{rel}" if SITE_URL else ""

def seo(title, desc, url, image, kind, jsonld):
    lines = [
        f'  <meta name="author" content="Abhiram SS (0xAbhiram)">',
        '  <meta name="robots" content="index, follow, max-image-preview:large">',
        '  <link rel="icon" href="favicon.svg" type="image/svg+xml">',
        f'  <meta property="og:site_name" content="{SITE_NAME}">',
        f'  <meta property="og:type" content="{kind}">',
        f'  <meta property="og:title" content="{title}">',
        f'  <meta property="og:description" content="{desc}">',
        '  <meta name="twitter:card" content="summary_large_image">',
        '  <meta name="twitter:creator" content="@0xabhiram">',
    ]
    if SITE_URL:
        lines += [
            f'  <link rel="canonical" href="{abs_url(url)}">',
            f'  <meta property="og:url" content="{abs_url(url)}">',
            f'  <meta property="og:image" content="{abs_url(image)}">',
        ]
    if jsonld:
        lines.append(f'  <script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>')
    return "\n".join(lines)

def head(title, desc, preload=False, url="", image="assets/banner-desk.jpg", kind="website", jsonld=None):
    pre='  <link rel="preload" as="image" href="assets/banner-desk.jpg">\n' if preload else ''
    return f'''<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <meta name="description" content="{desc}">
{seo(title, desc, url, image, kind, jsonld)}
  <meta name="color-scheme" content="dark">
  <meta name="theme-color" content="#0c0507">
  <script>(function(){{if(matchMedia("(prefers-reduced-motion: reduce)").matches)return;var n=performance.getEntriesByType&&performance.getEntriesByType("navigation")[0],t=n?n.type:"navigate",inside=false;try{{inside=!!document.referrer&&new URL(document.referrer).origin===location.origin}}catch(e){{}}if(t==="reload"||(t==="navigate"&&!inside))document.documentElement.classList.add("intro","hero-wait")}})()</script>
{pre}  <link rel="stylesheet" href="styles.css">
  <script src="main.js" defer></script>
</head>'''

SPLASH='''  <div class="splash" aria-hidden="true">
    <div class="sp-glow"></div>
    <div class="sp-content">
      <svg class="sp-sign" viewBox="0 0 1000 220">
        <defs>
          <linearGradient id="sp-fill" x1="0" x2="1" y1="0" y2="0">
            <stop offset="0" stop-color="#ffd9dd"/>
            <stop offset="0.5" stop-color="#ffffff"/>
            <stop offset="1" stop-color="#ff9aa5"/>
          </linearGradient>
          <linearGradient id="sp-shine" gradientUnits="userSpaceOnUse" x1="-400" x2="-100" y1="0" y2="0">
            <stop offset="0" stop-color="#ff5468" stop-opacity="0"/>
            <stop offset="0.5" stop-color="#ff5468" stop-opacity="0.95"/>
            <stop offset="1" stop-color="#ff5468" stop-opacity="0"/>
            <animate attributeName="x1" from="-400" to="1000" dur="0.8s" begin="1.55s" fill="freeze"/>
            <animate attributeName="x2" from="-100" to="1300" dur="0.8s" begin="1.55s" fill="freeze"/>
          </linearGradient>
        </defs>
        <text class="sp-stroke" x="500" y="120" text-anchor="middle" dominant-baseline="middle">0xAbhiram</text>
        <text class="sp-shine" x="500" y="120" text-anchor="middle" dominant-baseline="middle">0xAbhiram</text>
      </svg>
      <p class="sp-tag">Security Engineer Journal</p>
    </div>
    <div class="sp-foot">
      <span>settling in for the night shift</span>
      <div class="sp-bar"><i></i></div>
    </div>
  </div>
  <div class="ambient" aria-hidden="true"><span></span><span></span><span></span></div>'''

def nav(path, current, on_hero=False):
    links=[("index.html","01","Blog","blog"),("tags.html","02","Tags","tags"),("contact.html","03","Contact","contact")]
    li="\n".join(
        f'      <li><a href="{h}"{" aria-current=\"page\"" if k==current else ""}><span class="nav-num">{n}</span><span class="nav-label">{l}</span></a></li>'
        for h,n,l,k in links)
    return f'''<nav class="site-nav{' on-hero' if on_hero else ''}" aria-label="Primary">
    <a class="brand" href="index.html" aria-label="0xAbhiram journal, home">
      <span class="prompt-user">abhiram</span><span class="prompt-at">@</span><span class="prompt-host">journal</span><span class="prompt-sep">:</span><span class="prompt-path">{path}</span><span class="prompt-dollar">$</span><span class="cursor" aria-hidden="true">_</span>
    </a>
    <ul class="nav-links">
{li}
    </ul>
    <div class="nav-clock" aria-label="Local time in India">
      <span class="live-dot" aria-hidden="true"></span><span class="clock-zone">IST</span><time data-clock>--:--:--</time>
    </div>
    <div class="nav-progress" aria-hidden="true"></div>
  </nav>'''

FOOTER='''<footer class="site-footer">
    <div class="footer-inner">
      <section class="footer-cta">
        <h2>Got a story about <em>trust</em> gone wrong?</h2>
        <a class="cta-btn" href="contact.html">Open a channel <span aria-hidden="true">→</span></a>
      </section>

      <div class="footer-grid">
        <div class="footer-brand">
          <a class="footer-logo" href="index.html"><span>&gt;_</span> 0xAbhiram</a>
          <p>Notes on red teaming and product security.</p>
        </div>
        <nav class="footer-col" aria-label="Footer">
          <h2>Navigate</h2>
          <ul>
            <li><a href="index.html">Blog</a></li>
            <li><a href="tags.html">Tags</a></li>
            <li><a href="contact.html">Contact</a></li>
          </ul>
        </nav>
        <div class="footer-col">
          <h2>Connect</h2>
          <ul>
            <li><a href="https://github.com/0xabhiram" rel="me">GitHub ↗</a></li>
            <li><a href="https://x.com/0xabhiram" rel="me">X ↗</a></li>
            <li><a href="mailto:abhiram6542@gmail.com">Email</a></li>
          </ul>
        </div>
      </div>

      <dl class="footer-stats">
        <div class="stat"><dt class="stat-label">Uptime</dt><dd class="stat-value" data-uptime="2024-12-24T15:30:00+05:30">—</dd></div>
        <div class="stat"><dt class="stat-label">Your session</dt><dd class="stat-value" data-session>00:00:00</dd></div>
        <div class="stat"><dt class="stat-label">Local time · IST</dt><dd class="stat-value" data-clock>--:--:--</dd></div>
        <div class="stat"><dt class="stat-label">Moon tonight</dt><dd class="stat-value"><span class="moon-ico" data-moon-ico aria-hidden="true"></span><span data-moon>—</span></dd></div>
      </dl>

      <div class="footer-bottom">
        <span>© 2026 Abhiram SS</span>
        <button class="to-top" type="button">cd ~ ↑</button>
      </div>
    </div>
  </footer>
  <canvas class="embers" aria-hidden="true"></canvas>'''

def page(title, desc, path, current, body, on_hero=False, preload=False, **meta):
    return f'''<!DOCTYPE html>
<html lang="en">
{head(title, desc, preload, **meta)}
<body>
  <a class="skip-link" href="#main">Skip to content</a>
{SPLASH}

  {nav(path, current, on_hero)}

{body}

  {FOOTER}
</body>
</html>
'''


def card(p, featured):
    tags = "\n".join(f'                <li><a href="tags.html#{slug(t)}">{t}</a></li>' for t in p["card_tags"])
    return f'''        <li class="post-card{' post-card--featured' if featured else ''}">
          <figure class="post-cover">
            <img src="assets/{p['img']}?v=2" alt="{esc(p['alt'])}" width="1000" height="562" loading="lazy">
            <span class="post-index">LOG {p['log']}</span>
          </figure>
          <div class="post-body">
            <p class="post-log"><time datetime="{p['date']}">{p['date']}</time> · {p['mins']} min read</p>
            <h3><a href="{p['page']}">{esc(p['card_title'])}</a></h3>
            <p>{esc(p['desc'])}</p>
            <div class="post-foot">
              <ul class="tags" aria-label="Tags">
{tags}
              </ul>
              <span class="read-more" aria-hidden="true">read <span>→</span></span>
            </div>
          </div>
        </li>'''

cards = '      <ol class="post-grid" reversed>\n' + "\n\n".join(card(p, i == 0) for i, p in enumerate(POSTS)) + "\n      </ol>"

letters="".join(f'<span class="ch" style="--i:{i}">{c}</span>' for i,c in enumerate("0xAbhiram"))
index_body=f'''  <header class="hero">
    <div class="hero-glow" aria-hidden="true"></div>
    <div class="hero-content">
      <h1 class="hero-title">
        <span class="sr-only">0xAbhiram</span>
        <span class="hero-name" aria-hidden="true">{letters}</span>
      </h1>
      <div class="hero-rule" aria-hidden="true"></div>
      <p class="hero-tagline">
        <span class="sr-only">Security Engineer Journal</span>
        <span class="typed" aria-hidden="true">Security Engineer Journal</span>
      </p>
    </div>
    <a class="scroll-cue" href="#articles" aria-label="Scroll to articles">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M6 9l6 6 6-6"/>
      </svg>
    </a>
  </header>

  <main id="main">
    <section id="articles" class="container container--grid" aria-labelledby="articles-heading">
      <div class="section-head">
        <h2 id="articles-heading" class="section-label">Latest writing</h2>
        <span class="section-count">{len(POSTS)} entries</span>
      </div>

{cards}
    </section>
  </main>'''
home_desc = "0xAbhiram Blog — red teaming, Active Directory, product security and GRC automation notes by Abhiram SS (0xAbhiram)."
home_ld = {
    "@context": "https://schema.org",
    "@graph": [
        {"@type": "WebSite", "name": SITE_NAME, "alternateName": ["0xAbhiram", "0xAbhiram Blogs"], "description": home_desc,
         **({"url": abs_url("")} if SITE_URL else {}), "author": AUTHOR},
        {**AUTHOR, "jobTitle": "Security Engineer", "knowsAbout": ["Red Teaming", "VAPT", "Penetration Testing", "Product Security", "Cloud Security", "Active Directory"]},
        {"@type": "Blog", "name": SITE_NAME, "author": AUTHOR,
         "blogPost": [{"@type": "BlogPosting", "headline": p["title"], "datePublished": p["date"],
                       **({"url": abs_url(p["page"])} if SITE_URL else {})} for p in POSTS]},
    ],
}
open("index.html","w").write(page("0xAbhiram Blog — Red Teaming &amp; Product Security by Abhiram SS", home_desc,
    "~/blog", "blog", index_body, True, True, url="", jsonld=home_ld))

for p in POSTS:
    tag_links = "".join(f'<li><a href="tags.html#{slug(t)}">{t}</a></li>' for t in p["tags"])
    body = f'''  <main id="main" class="container container--panel page-offset">
    <article class="prose panel glass">
      <figure class="post-hero-image">
        <img src="assets/{p['img']}?v=2" alt="{esc(p['alt'])}" width="1000" height="562">
      </figure>
      <header class="post-header">
        <p class="post-meta">
          <time datetime="{p['date']}">{p['date_long']}</time> · {p['mins']} min read
        </p>
        <h1>{esc(p['title'])}</h1>
        <p class="lede">{esc(p['desc'])}</p>
      </header>

{p['html']}
      <hr>
      <footer class="post-end">
        <ul class="tags" aria-label="Tags">{tag_links}</ul>
        <a href="index.html">← Back to all posts</a>
      </footer>
    </article>
  </main>'''
    ld = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": p["title"],
        "description": p["desc"],
        "datePublished": p["date"],
        "dateModified": p["date"],
        "author": AUTHOR,
        "publisher": AUTHOR,
        "keywords": ", ".join(p["tags"]),
        "image": abs_url("assets/" + p["img"]) or "assets/" + p["img"],
        **({"url": abs_url(p["page"]), "mainEntityOfPage": abs_url(p["page"])} if SITE_URL else {}),
    }
    open(p["page"], "w").write(page(f"{esc(p['title'])} | {SITE_NAME}", esc(p["desc"]), p["path"], "blog", body,
        url=p["page"], image="assets/" + p["img"], kind="article", jsonld=ld))

# --- Tags ---
posts=[dict(img=p["img"], date=p["date"], url=p["page"], title=esc(p["card_title"]), tags=p["tags"]) for p in POSTS]
slug=lambda t: re.sub(r'[^a-z0-9]+','-',t.lower()).strip('-')
counts={}
for p in posts:
    for t in p["tags"]: counts[t]=counts.get(t,0)+1
order=sorted(counts, key=lambda t:(-counts[t], t.lower()))
chips=['          <button class="tag-chip" type="button" data-tag="all" aria-pressed="true">all <span class="tag-count">3</span></button>']
chips+=[f'          <button class="tag-chip" type="button" data-tag="{slug(t)}" aria-pressed="false" style="--w:{2 if counts[t]>1 else 1}">{t} <span class="tag-count">{counts[t]}</span></button>' for t in order]
rows=[]
for p in posts:
    tl="".join(f'<li data-tag="{slug(t)}">{t}</li>' for t in p["tags"])
    rows.append(f'''        <li class="tag-row" data-tags="{' '.join(slug(t) for t in p['tags'])}">
          <a href="{p['url']}">
            <img src="assets/{p['img']}?v=2" alt="" width="1000" height="562" loading="lazy">
            <div>
              <p class="post-log"><time datetime="{p['date']}">{p['date']}</time></p>
              <h2>{p['title']}</h2>
              <ul class="row-tags">{tl}</ul>
            </div>
            <span class="row-arrow" aria-hidden="true">→</span>
          </a>
        </li>''')
nl="\n"
tags_body=f'''  <main id="main" class="page-offset">
    <div class="container container--grid">
      <header class="page-head">
        <p class="page-cmd">ls ~/tags --sort=count</p>
        <h1 class="page-title">Tags</h1>
        <p class="page-sub">{len(order)} tags across {len(POSTS)} logs. Pick a tag or grep for a topic to filter the archive.</p>
      </header>

      <section class="tag-console" aria-label="Filter posts">
        <label class="grep">
          <span>$ grep -i</span>
          <input id="tag-search" type="search" placeholder="kerberos, red team, trust…" autocomplete="off" aria-label="Search tags and posts">
        </label>
        <div class="tag-cloud" role="group" aria-label="Tags">
{nl.join(chips)}
        </div>
      </section>

      <p class="result-line" aria-live="polite">&gt; <b id="result-count">3</b> match(es) for <b id="result-label">all tags</b></p>

      <ul class="tag-results">
{nl.join(rows)}
      </ul>
      <p class="no-results" hidden>grep: no matches found. <button class="link-btn" id="reset-filter" type="button">reset filter</button></p>
    </div>
  </main>'''
open("tags.html","w").write(page(f"Tags | {SITE_NAME}", "Browse 0xAbhiram's security writing by topic: red team, Active Directory, Kerberos, trust boundaries, GRC and more.",
    "~/tags", "tags", tags_body, url="tags.html"))

contact_body='''  <main id="main" class="page-offset">
    <div class="container container--grid">
      <header class="page-head">
        <p class="page-cmd">./contact --open</p>
        <h1 class="page-title">Open a channel</h1>
        <p class="page-sub">Research collab, a bug you found, or a question about a post — the line is open.</p>
      </header>

      <div class="contact-grid">
        <section class="term" aria-label="Contact channels">
          <div class="term-bar" aria-hidden="true">
            <span class="term-dot"></span><span class="term-dot"></span><span class="term-dot"></span>
            <span class="term-title">abhiram@journal: ~/contact</span>
          </div>
          <div class="term-body">
            <p class="cmd"><span class="ps">$</span><span class="c">whoami</span></p>
            <p class="out">Abhiram SS — product security &amp; red teaming</p>
            <p class="cmd"><span class="ps">$</span><span class="c">cat channels.txt</span></p>
            <ul class="channels">
              <li>
                <a href="mailto:abhiram6542@gmail.com"><span class="ch-key">email</span><span class="ch-val">abhiram6542@gmail.com</span></a>
                <button class="copy" type="button" data-copy="abhiram6542@gmail.com" aria-label="Copy email address">copy</button>
              </li>
              <li><a href="https://github.com/0xabhiram" rel="me"><span class="ch-key">github</span><span class="ch-val">github.com/0xabhiram</span><span class="ch-go" aria-hidden="true">↗</span></a></li>
              <li><a href="https://x.com/0xabhiram" rel="me"><span class="ch-key">x</span><span class="ch-val">x.com/0xabhiram</span><span class="ch-go" aria-hidden="true">↗</span></a></li>
            </ul>
            <p class="cmd"><span class="ps">$</span><span class="c">echo $OPEN_TO</span></p>
            <p class="out">research collaboration · responsible disclosure · product security</p>
            <p class="cmd"><span class="ps">$</span><span class="cursor" aria-hidden="true">_</span></p>
          </div>
        </section>

        <form class="transmit" id="transmit" data-to="abhiram6542@gmail.com">
          <h2>Compose transmission</h2>
          <p class="hint">Fill it in and it lands straight in my inbox. I usually reply within a day or two.</p>
          <label class="field"><span>Callsign</span><input name="name" required maxlength="60" autocomplete="name" placeholder="Your name"></label>
          <label class="field"><span>Return address</span><input name="email" type="email" required maxlength="120" autocomplete="email" placeholder="you@example.com"></label>
          <input class="trap" type="text" name="_honey" tabindex="-1" autocomplete="off" aria-hidden="true">
          <label class="field"><span>Channel</span>
            <select name="topic">
              <option>Collaboration</option>
              <option>Disclosure</option>
              <option>Question</option>
              <option>Just saying hi</option>
            </select>
          </label>
          <label class="field"><span>Subject</span><input name="subject" maxlength="120" placeholder="What's this about?"></label>
          <label class="field"><span>Payload</span><textarea name="message" required minlength="10" maxlength="4000" placeholder="Your message…"></textarea></label>
          <button class="send" type="submit">Send transmission <span aria-hidden="true">→</span></button>
          <p class="fine" role="status" aria-live="polite">// no trackers — straight to my inbox.</p>
        </form>
      </div>
    </div>
  </main>'''
open("contact.html","w").write(page(f"Contact | {SITE_NAME}", "Get in touch with Abhiram SS (0xAbhiram) for research collaboration, responsible disclosure or product security.",
    "~/contact", "contact", contact_body, url="contact.html"))

robots = "User-agent: *\nAllow: /\n"
if SITE_URL:
    urls = [("", "1.0")] + [(p["page"], "0.8") for p in POSTS] + [("tags.html", "0.5"), ("contact.html", "0.4")]
    newest = POSTS[0]["date"]
    entries = "\n".join(
        f"  <url><loc>{abs_url(u)}</loc><lastmod>{next((p['date'] for p in POSTS if p['page'] == u), newest)}</lastmod><priority>{pr}</priority></url>"
        for u, pr in urls)
    open("sitemap.xml", "w").write(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{entries}\n</urlset>\n')
    robots += f"\nSitemap: {abs_url('sitemap.xml')}\n"
open("robots.txt", "w").write(robots)

print("built", len(POSTS), "posts,", len(order), "tags")
