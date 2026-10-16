(() => {
  const root = document.documentElement;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const GLYPHS = "!<>-_\\/[]{}=+*^?#$%&01ABCDEFabcdef";
  const randomGlyph = () => GLYPHS[Math.floor(Math.random() * GLYPHS.length)];
  const pad = (n) => String(n).padStart(2, "0");

  const istTime = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Kolkata",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });

  /* Intro: plays on refresh or first arrival, then hands over to the hero */
  const splash = document.querySelector(".splash");
  let introDone = Promise.resolve();

  if (splash && root.classList.contains("intro")) {
    introDone = new Promise((resolve) => {
      let closed = false;
      const close = () => {
        if (closed) return;
        closed = true;
        splash.classList.add("is-out");
        setTimeout(() => {
          root.classList.remove("hero-wait");
          resolve();
        }, 450);
        setTimeout(() => {
          root.classList.remove("intro");
          splash.remove();
        }, 950);
      };
      setTimeout(close, 2500);
      splash.addEventListener("click", close);
    });
  } else {
    splash?.remove();
    root.classList.remove("hero-wait");
  }

  /* Hero name: wrap letters for the rise animation; one copy stays in HTML */
  document.querySelectorAll("[data-split]").forEach((el) => {
    const text = el.textContent.trim();
    el.setAttribute("aria-label", text);
    const wrap = document.createElement("span");
    wrap.className = "hero-name";
    wrap.setAttribute("aria-hidden", "true");
    [...text].forEach((c, i) => {
      const s = document.createElement("span");
      s.className = "ch";
      s.style.setProperty("--i", String(i));
      s.textContent = c;
      wrap.append(s);
    });
    el.replaceChildren(wrap);
  });

  /* Nav: white over the banner, faded solid backing after ---------------- */
  const nav = document.querySelector(".site-nav");
  const hero = document.querySelector(".hero");

  if (nav && hero && "IntersectionObserver" in window) {
    new IntersectionObserver(
      ([entry]) => nav.classList.toggle("on-hero", entry.isIntersecting),
      { rootMargin: `-${nav.offsetHeight}px 0px 0px 0px` }
    ).observe(hero);
  } else if (nav) {
    nav.classList.remove("on-hero");
  }

  /* Scroll: banner parallax + reading progress --------------------------- */
  let ticking = false;
  const onScroll = () => {
    const max = document.documentElement.scrollHeight - window.innerHeight;
    root.style.setProperty("--progress", max > 0 ? Math.min(1, window.scrollY / max) : 0);
    if (hero && !reduceMotion) {
      root.style.setProperty("--scroll", Math.min(window.scrollY, window.innerHeight));
    }
    ticking = false;
  };
  window.addEventListener("scroll", () => {
    if (!ticking) { ticking = true; requestAnimationFrame(onScroll); }
  }, { passive: true });
  onScroll();

  /* Nav links: quick scramble on hover ----------------------------------- */
  if (!reduceMotion) {
    document.querySelectorAll(".nav-label").forEach((label) => {
      const text = label.textContent;
      let timer = null;
      label.style.minWidth = `${label.offsetWidth}px`;
      label.closest("a").addEventListener("mouseenter", () => {
        clearInterval(timer);
        let frame = 0;
        timer = setInterval(() => {
          frame++;
          label.textContent = [...text]
            .map((c, i) => (i < frame / 2 ? c : randomGlyph()))
            .join("");
          if (frame / 2 >= text.length) {
            clearInterval(timer);
            label.textContent = text;
          }
        }, 35);
      });
    });
  }

  /* Live clocks + footer counters ---------------------------------------- */
  const clockEls = document.querySelectorAll("[data-clock]");
  const uptimeEl = document.querySelector("[data-uptime]");
  const sessionEl = document.querySelector("[data-session]");
  const moonEl = document.querySelector("[data-moon]");
  const moonIco = document.querySelector("[data-moon-ico]");
  const SYNODIC = 29.530588853;
  const NEW_MOON = Date.UTC(2000, 0, 6, 18, 14);
  const MOON_NAMES = ["New moon", "Waxing crescent", "First quarter", "Waxing gibbous", "Full moon", "Waning gibbous", "Last quarter", "Waning crescent"];
  const uptimeStart = uptimeEl ? new Date(uptimeEl.dataset.uptime).getTime() : 0;

  let sessionStart = Date.now();
  try {
    sessionStart = Number(sessionStorage.getItem("session-start")) || sessionStart;
    sessionStorage.setItem("session-start", sessionStart);
  } catch {}

  const tickClocks = () => {
    const now = Date.now();
    const time = istTime.format(now);
    clockEls.forEach((el) => { el.textContent = time; });

    if (uptimeEl) {
      const s = Math.max(0, Math.floor((now - uptimeStart) / 1000));
      const d = Math.floor(s / 86400);
      uptimeEl.textContent = `${d}d ${pad(Math.floor(s / 3600) % 24)}:${pad(Math.floor(s / 60) % 60)}:${pad(s % 60)}`;
    }
    if (moonEl) {
      const age = (((now - NEW_MOON) / 864e5) % SYNODIC + SYNODIC) % SYNODIC;
      const lit = (1 - Math.cos((2 * Math.PI * age) / SYNODIC)) / 2;
      const name = MOON_NAMES[Math.floor((age / SYNODIC) * 8 + 0.5) % 8];
      moonEl.textContent = `${name} · ${Math.round(lit * 100)}%`;
      if (moonIco) {
        moonIco.style.setProperty("--lit", lit.toFixed(2));
        moonIco.style.setProperty("--dir", age < SYNODIC / 2 ? 1 : -1);
      }
    }
    if (sessionEl) {
      const s = Math.floor((now - sessionStart) / 1000);
      sessionEl.textContent = `${pad(Math.floor(s / 3600))}:${pad(Math.floor(s / 60) % 60)}:${pad(s % 60)}`;
    }
  };
  tickClocks();
  setInterval(tickClocks, 1000);

  document.querySelector(".to-top")?.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: reduceMotion ? "auto" : "smooth" });
  });

  /* Soft night rain ------------------------------------------------------ */
  const canvas = document.querySelector(".embers");
  if (canvas && !reduceMotion) {
    const ctx = canvas.getContext("2d");
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const WIND = -0.16;
    let w = 0, h = 0, drops = [];

    const spawn = (anywhere) => {
      const depth = Math.random() ** 1.6;
      return {
        x: Math.random() * (w + 120),
        y: anywhere ? Math.random() * h : -40 - Math.random() * h * 0.5,
        len: 10 + depth * 26,
        speed: 3.2 + depth * 7.5,
        alpha: 0.06 + depth * 0.26,
        width: 0.6 + depth * 0.9,
      };
    };

    const resize = () => {
      w = window.innerWidth;
      h = window.innerHeight;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const count = Math.round(Math.max(40, Math.min(150, (w * h) / 11000)));
      drops = Array.from({ length: count }, () => spawn(true));
    };

    const draw = () => {
      ctx.clearRect(0, 0, w, h);
      ctx.lineCap = "round";
      for (const d of drops) {
        d.y += d.speed;
        d.x += d.speed * WIND;
        if (d.y - d.len > h || d.x < -40) Object.assign(d, spawn(false));

        const grad = ctx.createLinearGradient(d.x, d.y - d.len, d.x, d.y);
        grad.addColorStop(0, "rgba(255, 190, 198, 0)");
        grad.addColorStop(1, `rgba(255, 205, 210, ${d.alpha})`);
        ctx.strokeStyle = grad;
        ctx.lineWidth = d.width;
        ctx.beginPath();
        ctx.moveTo(d.x - d.len * WIND, d.y - d.len);
        ctx.lineTo(d.x, d.y);
        ctx.stroke();
      }
      requestAnimationFrame(draw);
    };

    resize();
    window.addEventListener("resize", resize);
    requestAnimationFrame(draw);
  }

  /* Typing tagline, once the name has risen ------------------------------- */
  introDone.then(() => {
    const typed = document.querySelector(".typed");
    if (!typed || reduceMotion) return;
    const text = typed.textContent.trim();
    let char = 0;
    typed.textContent = "";
    const tick = () => {
      typed.textContent = text.slice(0, ++char);
      if (char < text.length) setTimeout(tick, 70);
    };
    setTimeout(tick, 1300);
  });

  /* Tags page: filter by chip + grep ------------------------------------- */
  const cloud = document.querySelector(".tag-cloud");
  if (cloud) {
    const chips = [...cloud.querySelectorAll(".tag-chip")];
    const rows = [...document.querySelectorAll(".tag-row")];
    const search = document.querySelector("#tag-search");
    const countEl = document.querySelector("#result-count");
    const labelEl = document.querySelector("#result-label");
    const empty = document.querySelector(".no-results");
    let active = "all";

    const apply = () => {
      const q = (search?.value || "").trim().toLowerCase();

      chips.forEach((chip) => {
        const on = chip.dataset.tag === active;
        chip.classList.toggle("is-active", on);
        chip.setAttribute("aria-pressed", on);
        chip.hidden = chip.dataset.tag !== "all" && !!q && !chip.textContent.toLowerCase().includes(q);
      });

      let shown = 0;
      rows.forEach((row) => {
        const tags = row.dataset.tags.split(" ");
        const match = (active === "all" || tags.includes(active)) &&
          (!q || row.textContent.toLowerCase().includes(q));
        row.hidden = !match;
        if (match) shown++;
        row.querySelectorAll(".row-tags li").forEach((li) => {
          li.classList.toggle("is-match", li.dataset.tag === active);
        });
      });

      countEl.textContent = shown;
      labelEl.textContent = active === "all" ? "all tags" : `#${active.replace(/-/g, " ")}`;
      empty.hidden = shown > 0;
    };

    const select = (tag) => {
      active = chips.some((c) => c.dataset.tag === tag) ? tag : "all";
      history.replaceState(null, "", active === "all" ? location.pathname : `#${active}`);
      apply();
    };

    chips.forEach((chip) => chip.addEventListener("click", () => select(chip.dataset.tag)));
    search?.addEventListener("input", apply);
    document.querySelector("#reset-filter")?.addEventListener("click", () => {
      if (search) search.value = "";
      select("all");
    });

    select(decodeURIComponent(location.hash.slice(1)) || "all");
  }

  /* Contact: typed terminal, copy buttons, mailto composer ---------------- */
  const term = document.querySelector(".term");
  if (term && !reduceMotion) {
    const lines = [...term.querySelectorAll(".term-body > *")];
    term.classList.add("is-typing");

    const show = (i) => {
      if (i >= lines.length) return term.classList.remove("is-typing");
      const line = lines[i];
      const target = line.querySelector(".c");
      line.classList.add("is-shown");
      if (!target) return setTimeout(() => show(i + 1), 160);

      const text = target.textContent;
      let n = 0;
      target.textContent = "";
      const type = () => {
        target.textContent = text.slice(0, ++n);
        if (n < text.length) setTimeout(type, 42);
        else setTimeout(() => show(i + 1), 260);
      };
      setTimeout(type, 200);
    };
    introDone.then(() => show(0));
  }

  document.querySelectorAll("[data-copy]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(btn.dataset.copy);
        btn.textContent = "copied ✓";
      } catch {
        btn.textContent = "copy failed";
      }
      setTimeout(() => { btn.textContent = "copy"; }, 1600);
    });
  });

  /* Contact form: sanitise input, refuse risky links, defang the rest ----- */
  const INVISIBLE = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F-\u009F\u00AD\u061C\u180E\u200B-\u200F\u202A-\u202E\u2060-\u2069\uFEFF]/g;
  const LINK = /\b(?:[a-z][a-z0-9+.-]*:\/\/|www\.)[^\s]+|\b(?:[a-z0-9-]+\.)+[a-z]{2,}(?:\/[^\s]*)?/gi;
  const SHORTENER = /^(?:[a-z]+:\/\/)?(?:www\.)?(?:bit\.ly|tinyurl\.com|t\.co|goo\.gl|is\.gd|cutt\.ly|rb\.gy|ow\.ly|tiny\.cc|shorturl\.at|rebrand\.ly|buff\.ly|t\.ly|s\.id|v\.gd|qr\.co|lnkd\.in)\b/i;
  const RISKY_FILE = /\.(?:exe|scr|msi|bat|cmd|ps1|vbs|js|jse|wsf|jar|apk|hta|lnk|iso|img|dmg|zip|rar|7z|docm|xlsm)$/i;
  const TOPICS = ["Collaboration", "Disclosure", "Question", "Just saying hi"];
  const LIMITS = { name: 60, email: 120, subject: 120, message: 4000 };

  const clean = (v, max, multiline = false) => {
    let s = String(v ?? "").normalize("NFKC").replace(INVISIBLE, "");
    s = s.replace(/<[^>]*>/g, "").replace(/[<>]/g, "");
    s = multiline ? s.replace(/\r\n?/g, "\n").replace(/[ \t]+\n/g, "\n").replace(/\n{3,}/g, "\n\n") : s.replace(/\s+/g, " ");
    return s.trim().slice(0, max);
  };
  const links = (s) => s.match(LINK) || [];
  const defang = (s) => s.replace(LINK, (m) =>
    m.replace(/^h(tt)(ps?)/i, "hxx$2").replace(/:\/\//, "[://]").replace(/\./g, "[.]"));

  const checkLinks = (text) => {
    if (/\b(?:javascript|vbscript|data|file|blob)\s*:/i.test(text)) return "script or data: links aren't allowed.";
    if (/\bxn--/i.test(text)) return "look-alike (punycode) domains aren't allowed.";
    const found = links(text);
    if (found.length > 3) return "please keep it to 3 links or fewer.";
    for (const url of found) {
      if (SHORTENER.test(url)) return "link shorteners aren't allowed — paste the full link.";
      if (/^(?:[a-z]+:\/\/)?[^\/\s]*@/i.test(url)) return "links with credentials or '@' tricks aren't allowed.";
      if (/^(?:[a-z]+:\/\/)?(?:\d{1,3}\.){3}\d{1,3}/.test(url)) return "raw IP links aren't allowed — defang IOCs like 10[.]0[.]0[.]1.";
      if (RISKY_FILE.test(url.split(/[?#]/)[0])) return "links to executables or archives aren't allowed.";
    }
    return "";
  };

  const validate = (raw) => {
    const v = {
      name: clean(raw.get("name"), LIMITS.name),
      email: clean(raw.get("email"), LIMITS.email).toLowerCase(),
      topic: TOPICS.includes(raw.get("topic")) ? raw.get("topic") : TOPICS[0],
      subject: clean(raw.get("subject"), LIMITS.subject),
      message: clean(raw.get("message"), LIMITS.message, true),
    };
    if (!/^[\p{L}\p{M}\p{N}' ._-]{2,60}$/u.test(v.name) || links(v.name).length) return { field: "name", error: "use letters, numbers, spaces, . _ - or ' in your name." };
    if (!/^[^\s@<>()[\]\\,;:"']{1,64}@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,24}$/i.test(v.email) || /xn--/i.test(v.email))
      return { field: "email", error: "that return address doesn't look valid." };
    if (links(v.subject).length || /:\/\//.test(v.subject)) return { field: "subject", error: "links aren't allowed in the subject." };
    if (v.message.length < 10) return { field: "message", error: "the message is a little too short." };
    const linkErr = checkLinks(v.message);
    if (linkErr) return { field: "message", error: linkErr };
    v.message = defang(v.message);
    return { v };
  };

  const form = document.querySelector("#transmit");
  const openedAt = Date.now();
  form?.addEventListener("input", (e) => e.target.removeAttribute("aria-invalid"));
  form?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const raw = new FormData(form);
    const btn = form.querySelector(".send");
    const status = form.querySelector(".fine");
    const set = (state, text) => { form.dataset.state = state; status.textContent = text; };

    if (raw.get("_honey") || Date.now() - openedAt < 3000) {
      form.reset();
      return set("sent", "// transmission received ✓ — I'll get back to you soon.");
    }

    const { v, field, error } = validate(raw);
    if (error) {
      const el = form.elements[field];
      el.setAttribute("aria-invalid", "true");
      el.focus();
      return set("error", `// rejected: ${error}`);
    }

    const last = Number(localStorage.getItem("tx-last") || 0);
    const wait = Math.ceil((60000 - (Date.now() - last)) / 1000);
    if (wait > 0) return set("error", `// cooling down — try again in ${wait}s.`);
    const fingerprint = `${v.email}|${v.message}`.slice(0, 500);
    if (localStorage.getItem("tx-sig") === fingerprint) return set("error", "// this exact message was already sent.");

    const subject = `[${v.topic}] ${v.subject || "Hello"} — from ${v.name}`;
    btn.disabled = true;
    set("sending", "// transmitting…");
    try {
      const res = await fetch(`https://formsubmit.co/ajax/${form.dataset.key || form.dataset.to}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({
          name: v.name,
          email: v.email,
          channel: v.topic,
          subject: v.subject,
          message: v.message,
          _subject: `0xAbhiram Blog · ${subject}`,
          _replyto: v.email,
          _template: "table",
          _captcha: "false",
          _blacklist: "seed phrase, wallet recovery, crypto investment, casino, viagra, loan offer, verify your account, password reset",
        }),
      });
      const out = await res.json().catch(() => ({}));
      if (!res.ok || String(out.success) === "false") throw new Error(out.message || res.status);
      localStorage.setItem("tx-last", String(Date.now()));
      localStorage.setItem("tx-sig", fingerprint);
      form.reset();
      set("sent", "// transmission received ✓ — I'll get back to you soon.");
    } catch {
      set("error", "// relay failed — opening your mail app instead…");
      const body = `${v.message}\n\n— ${v.name} <${v.email}>`;
      window.location.href =
        `mailto:${form.dataset.to}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    } finally {
      btn.disabled = false;
    }
  });
})();
