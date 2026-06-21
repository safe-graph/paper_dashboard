<script>
  import { onMount } from "svelte";
  import EChart from "./lib/EChart.svelte";
  import ScrollReveal from "./lib/ScrollReveal.svelte";
  import AnimatedNumber from "./lib/AnimatedNumber.svelte";
  import dataInline from "./data.json";
  import paperStats from "./paper_statistics.json";

  let data = dataInline;
  let error = "";
  let loading = false;

  /* ---------------------------------------------------------
     Theme management (light / dark with persistence)
     --------------------------------------------------------- */
  let theme = "dark";

  function applyTheme(t) {
    if (typeof document !== "undefined") {
      document.documentElement.setAttribute("data-theme", t);
    }
  }

  function toggleTheme() {
    theme = theme === "dark" ? "light" : "dark";
    applyTheme(theme);
    try {
      localStorage.setItem("dashboard-theme", theme);
    } catch (e) {
      /* ignore */
    }
  }

  /* Theme-aware chart colors. Reactive blocks below depend on `c`
     so every chart option recomputes (and re-renders) on toggle. */
  $: c = {
    text: theme === "light" ? "#1f2937" : "#e8eef5",
    muted: theme === "light" ? "#5b6675" : "#9aa8b8",
    axis: theme === "light" ? "#d3dae6" : "#36424f",
    split: theme === "light" ? "rgba(15,23,42,0.07)" : "rgba(255,255,255,0.06)",
    tooltipBg: theme === "light" ? "rgba(255,255,255,0.98)" : "rgba(17,24,33,0.96)",
    tooltipBorder: theme === "light" ? "rgba(99,102,241,0.35)" : "rgba(129,140,248,0.4)",
    pieBorder: theme === "light" ? "#ffffff" : "#141a23",
  };

  /* ---------------------------------------------------------
     Survey citation counts (runs client-side on GitHub Pages,
     where OpenAlex is reachable from the user's browser).
     --------------------------------------------------------- */
  let surveyCitations = {};
  let citationsLoading = true;

  onMount(async () => {
    // Initialise theme from saved preference or system setting.
    let saved = null;
    try {
      saved = localStorage.getItem("dashboard-theme");
    } catch (e) {
      /* ignore */
    }
    const prefersLight =
      typeof window !== "undefined" &&
      window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: light)").matches;
    theme = saved || (prefersLight ? "light" : "dark");
    applyTheme(theme);

    const surveys = (data?.resources || []).filter((r) => r.category === "Survey Paper");
    const results = {};
    for (const survey of surveys) {
      try {
        const q = encodeURIComponent(survey.title.replace(/[^\w\s]/g, " ").trim());
        const resp = await fetch(`https://api.openalex.org/works?search=${q}&per_page=1`);
        if (resp.ok) {
          const payload = await resp.json();
          if (payload.results?.length) {
            results[survey.title] = payload.results[0].cited_by_count || 0;
          }
        }
      } catch (e) {
        /* silently skip */
      }
    }
    surveyCitations = results;
    citationsLoading = false;
  });

  /* ---------------------------------------------------------
     Filters / table state
     --------------------------------------------------------- */
  let query = "";
  let category = "All";
  let domain = "All";
  let yearFilter = "All";
  let page = 1;
  const pageSize = 20;

  const langIcons = {
    Python: "🐍",
    "Jupyter Notebook": "📓",
    JavaScript: "🟨",
    TypeScript: "💠",
    "C++": "🧊",
    Rust: "🦀",
    Go: "🐹",
    Julia: "🔮",
    R: "📊",
    Java: "☕",
  };

  const venueIcons = {
    KDD: "🔷",
    NeurIPS: "🧠",
    ICLR: "🌄",
    ICML: "📈",
    AAAI: "🤖",
    IJCAI: "🌐",
    WWW: "🕸️",
    TheWebConf: "🕸️",
    CIKM: "📚",
    WSDM: "🔍",
    SDM: "🧭",
    SIGIR: "🔎",
    ACL: "💬",
    EMNLP: "🗣️",
    TKDE: "📘",
    TNNLS: "🧠",
    TIFS: "🛡️",
  };

  const makeChip = (label, icon) =>
    `<span class="chip"><span class="icon">${icon || "★"}</span>${label}</span>`;

  const fmt = (n) => (n || n === 0 ? n.toLocaleString("en-US") : "–");

  // Shared categorical palette (works in both themes).
  const palette = {
    blue: "#6366f1",
    teal: "#14b8a6",
    coral: "#f97362",
    lavender: "#a78bfa",
    gold: "#f59e0b",
    slate: "#3b82f6",
  };

  $: papers = data?.papers || [];
  $: stats = data?.stats || {};
  $: resources = data?.resources || [];

  $: repoStarsMap = (stats.code_repos || []).reduce((acc, repo) => {
    acc[repo.full_name.toLowerCase()] = repo.stars;
    return acc;
  }, {});

  const getGitHubStars = (url) => {
    if (!url || !url.includes("github.com")) return null;
    const match = url.match(/github\.com\/([^\/]+\/[^\/]+)/);
    if (match) {
      return repoStarsMap[match[1].toLowerCase()] || null;
    }
    return null;
  };

  $: categories = ["All", ...new Set(papers.map((p) => p.category).filter(Boolean))];
  $: domains = ["All", ...new Set(stats.domain_counts?.map((d) => d.domain) || [])];
  $: years = [
    "All",
    ...Array.from(new Set(papers.map((p) => p.year).filter(Boolean))).sort((a, b) => b - a),
  ];
  $: page = 1, query, category, domain, yearFilter; // reset page on filter change
  $: filtered = papers.filter((p) => {
    const q = query.trim().toLowerCase();
    const matchesQuery =
      !q ||
      p.title.toLowerCase().includes(q) ||
      (p.venue && p.venue.toLowerCase().includes(q));
    const matchesCategory = category === "All" || p.category === category;
    const matchesDomain = domain === "All" || p.domain === domain;
    const matchesYear = yearFilter === "All" || p.year === yearFilter;
    return matchesQuery && matchesCategory && matchesDomain && matchesYear;
  });
  $: pageCount = filtered.length ? Math.max(1, Math.ceil(filtered.length / pageSize)) : 1;
  $: page = Math.min(page, pageCount);
  $: pageItems = filtered.slice((page - 1) * pageSize, page * pageSize);

  function resetFilters() {
    query = "";
    category = "All";
    domain = "All";
    yearFilter = "All";
  }

  /* ---------------------------------------------------------
     Chart option builders (take a `c` colors object so they
     are fully theme-reactive).
     --------------------------------------------------------- */
  const baseTooltip = (c) => ({
    backgroundColor: c.tooltipBg,
    borderColor: c.tooltipBorder,
    borderWidth: 1,
    textStyle: { color: c.text },
    extraCssText: "box-shadow: 0 8px 28px rgba(0,0,0,0.18); border-radius: 10px;",
  });

  const baseBar = (c, items, xKey, yKey, title, horizontal = false, color = palette.blue, labelOpts = {}) => ({
    textStyle: { color: c.text },
    title: { text: title, textStyle: { color: c.text, fontSize: 14, fontWeight: 700 } },
    tooltip: { trigger: "axis", ...baseTooltip(c) },
    grid: { left: horizontal ? 170 : 48, right: 24, top: 38, bottom: 38, containLabel: !horizontal },
    xAxis: horizontal
      ? { type: "value", axisLine: { lineStyle: { color: c.axis } }, axisLabel: { color: c.muted }, splitLine: { lineStyle: { color: c.split } } }
      : {
          type: "category",
          data: items.map((d) => d[xKey]),
          axisLabel: { rotate: 30, color: c.muted },
          axisLine: { lineStyle: { color: c.axis } },
        },
    yAxis: horizontal
      ? {
          type: "category",
          data: items.map((d) => d[yKey]),
          axisLabel: { color: c.muted },
          axisLine: { lineStyle: { color: c.axis } },
        }
      : { type: "value", axisLine: { lineStyle: { color: c.axis } }, axisLabel: { color: c.muted }, splitLine: { lineStyle: { color: c.split } } },
    animationDuration: 800,
    animationEasing: "cubicOut",
    animationDelay: (idx) => idx * 50,
    series: [
      {
        type: "bar",
        data: items.map((d) => d[horizontal ? xKey : yKey]),
        itemStyle: {
          color: {
            type: "linear",
            x: 0,
            y: horizontal ? 0 : 1,
            x2: horizontal ? 1 : 0,
            y2: 0,
            colorStops: [
              { offset: 0, color: color },
              { offset: 1, color: color + "aa" },
            ],
          },
          borderRadius: horizontal ? [0, 6, 6, 0] : [6, 6, 0, 0],
        },
        emphasis: { itemStyle: { shadowBlur: 14, shadowColor: color + "66" } },
        barMaxWidth: horizontal ? 22 : 40,
        label: labelOpts,
      },
    ],
  });

  const pie = (c, items, name, title) => ({
    textStyle: { color: c.text },
    title: { text: title, textStyle: { color: c.text, fontSize: 14, fontWeight: 700 } },
    tooltip: { trigger: "item", ...baseTooltip(c) },
    legend: { bottom: 0, textStyle: { color: c.muted }, icon: "circle" },
    animationDuration: 900,
    animationEasing: "cubicOut",
    series: [
      {
        type: "pie",
        radius: ["42%", "66%"],
        center: ["50%", "46%"],
        data: items.map((d) => ({ name: d[name], value: d.count || d.bytes || d.value })),
        label: { color: c.text },
        labelLine: { lineStyle: { color: c.axis } },
        itemStyle: { borderWidth: 3, borderColor: c.pieBorder, borderRadius: 4 },
        emphasis: { itemStyle: { shadowBlur: 18, shadowColor: "rgba(99,102,241,0.4)" }, scale: true, scaleSize: 8 },
      },
    ],
  });

  const radar = (c, items, labelKey, valueKey, title) => ({
    textStyle: { color: c.text },
    title: { text: title, textStyle: { color: c.text, fontSize: 14, fontWeight: 700 } },
    tooltip: { ...baseTooltip(c) },
    animationDuration: 900,
    animationEasing: "cubicOut",
    radar: {
      indicator: items.map((d) => ({
        name: d[labelKey],
        max: Math.max(...items.map((i) => i[valueKey])) * 1.2,
      })),
      axisName: { color: c.muted },
      axisLine: { lineStyle: { color: c.split } },
      splitLine: { lineStyle: { color: c.split } },
      splitArea: { areaStyle: { color: ["transparent", c.split] } },
    },
    series: [
      {
        type: "radar",
        data: [
          {
            value: items.map((d) => d[valueKey]),
            name: title,
            areaStyle: {
              color: {
                type: "linear", x: 0, y: 0, x2: 0, y2: 1,
                colorStops: [
                  { offset: 0, color: "rgba(20,184,166,0.45)" },
                  { offset: 1, color: "rgba(20,184,166,0.08)" },
                ],
              },
            },
            lineStyle: { color: palette.teal, width: 2 },
            itemStyle: { color: palette.teal },
          },
        ],
      },
    ],
  });

  const excludeArxiv = (items) =>
    items?.filter((d) => !["arxiv", "arXiv", "Arxiv"].includes(d.venue)) || [];

  const psMethods = paperStats.top_10_method_families.map((d) => ({ method: d.method_family, count: d.count }));
  const psDomains = paperStats.top_10_application_domains.map((d) => ({ domain: d.application_domain, count: d.count }));
  const psDatasets = paperStats.top_10_datasets;

  $: yearOption = stats.year_counts ? baseBar(c, stats.year_counts, "year", "count", "Papers by year", false, palette.blue, { show: false }) : null;
  $: categoryOption = stats.category_counts ? baseBar(c, stats.category_counts, "count", "category", "Entries by category", true, palette.teal) : null;
  $: topicOption = stats.topics ? baseBar(c, stats.topics, "topic", "count", "Frequent title terms", false, palette.coral) : null;
  $: methodOption = psMethods.length ? baseBar(c, psMethods, "count", "method", "Method families", true, palette.lavender) : null;
  $: domainOption = psDomains.length ? baseBar(c, psDomains, "count", "domain", "Application domains", true, palette.slate) : null;
  $: filteredVenues = excludeArxiv(stats.venue_counts);
  $: venueOption = filteredVenues.length ? baseBar(c, filteredVenues.slice(0, 12), "count", "venue", "Top venues", true, palette.blue) : null;
  $: strataOption = stats.venue_strata ? pie(c, stats.venue_strata, "stratum", "Venue strata") : null;
  $: codeOption = stats.code_availability
    ? pie(c, [
        { label: "With code", count: stats.code_availability.with_code },
        { label: "No code", count: stats.code_availability.without_code },
      ], "label", "Code availability")
    : null;
  $: langOption = stats.language_counts && stats.language_counts.length
    ? pie(c, stats.language_counts, "language", "Language share (code repos)")
    : null;
  $: radarOption = psMethods.length >= 3 ? radar(c, psMethods.slice(0, 8), "method", "count", "Method comparison") : null;
  $: datasetOption = psDatasets.length
    ? baseBar(c, psDatasets.map((d) => ({ dataset: d.dataset, count: d.count })), "count", "dataset", "Top cited datasets", true, palette.gold)
    : null;

  const navItems = [
    { id: "highlights", label: "Highlights" },
    { id: "top-cited", label: "Top Cited" },
    { id: "distributions", label: "Trends" },
    { id: "methods", label: "Methods" },
    { id: "venues", label: "Venues" },
    { id: "table", label: "Explorer" },
    { id: "resources", label: "Resources" },
  ];
</script>

<div class="glow" aria-hidden="true"></div>

<nav class="nav">
  <div class="nav-brand">
    <span class="nav-logo">◈</span>
    <span>Fraud&nbsp;Detection&nbsp;Papers</span>
  </div>
  <div class="nav-links">
    {#each navItems as item}
      <a href={`#${item.id}`}>{item.label}</a>
    {/each}
  </div>
  <button
    class="theme-toggle"
    on:click={toggleTheme}
    aria-label="Toggle light and dark theme"
    title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
  >
    {theme === "dark" ? "☀️" : "🌙"}
  </button>
</nav>

<main>
  <header class="hero">
    <ScrollReveal>
      <span class="pill">Graph &amp; Transformer Fraud Detection</span>
      <h1>An interactive map of the<br /><span class="grad">Safe-Graph paper collection</span></h1>
      <p class="lede">
        Trends, venues, methods, and the most-cited work in graph- and transformer-based
        fraud, anomaly, and outlier detection — refreshed automatically from the upstream list.
      </p>
    </ScrollReveal>
    <div class="stat-grid">
      <ScrollReveal delay={0}>
        <div class="stat featured">
          <div class="label"><span class="stat-ico">📄</span> Total papers</div>
          <div class="value"><AnimatedNumber value={stats.paper_count || papers.length} delay={150} /></div>
          <div class="sub">across {categories.length - 1} categories</div>
        </div>
      </ScrollReveal>
      <ScrollReveal delay={80}>
        <div class="stat">
          <div class="label"><span class="stat-ico">💻</span> With code</div>
          <div class="value">
            {#if stats.code_availability}
              <AnimatedNumber value={stats.code_availability.with_code} delay={250} />
            {:else}–{/if}
          </div>
          <div class="sub">
            {#if stats.code_availability}{stats.code_availability.percentage || 0}% of all papers{/if}
          </div>
        </div>
      </ScrollReveal>
      <ScrollReveal delay={160}>
        <div class="stat">
          <div class="label"><span class="stat-ico">🏛️</span> Top venue</div>
          <div class="value" style="font-size:24px;">{stats.venue_counts?.[0]?.venue || "–"}</div>
          <div class="sub">{stats.venue_counts?.[0]?.count || 0} papers</div>
        </div>
      </ScrollReveal>
      <ScrollReveal delay={240}>
        <div class="stat">
          <div class="label"><span class="stat-ico">🔥</span> Dominant topic</div>
          <div class="value" style="font-size:24px;text-transform:capitalize;">{stats.topics?.[0]?.topic || "–"}</div>
          <div class="sub">most frequent title term</div>
        </div>
      </ScrollReveal>
    </div>
  </header>

  {#if loading}
    <section class="section"><div class="panel">Loading…</div></section>
  {:else if error}
    <section class="section"><div class="panel">{error}</div></section>
  {:else}
    <ScrollReveal>
      <section class="section" id="highlights">
        <div class="section-head"><span class="eyebrow">Overview</span><h2>What stands out</h2></div>
        <div class="panel insights">
          <ul>
            {#if stats.insights?.length}
              {#each stats.insights as insight}<li>{insight}</li>{/each}
            {:else}<li>No insights available.</li>{/if}
          </ul>
        </div>
      </section>
    </ScrollReveal>

    <ScrollReveal>
      <section class="section" id="top-cited">
        <div class="section-head"><span class="eyebrow">Impact</span><h2>Most cited papers</h2></div>
        <p class="section-sub">
          Ranked by citation count{#if stats.citation_source} via {stats.citation_source}{/if}.
          Counts refresh on each automated build.
        </p>
        <div class="panel">
          <div class="list">
            {#if stats.top_cited?.length}
              {#each stats.top_cited as paper, idx}
                <div class="list-item">
                  <span class="li-main">
                    <span class="rank">{idx + 1}</span>
                    <span class="li-text">
                      <a href={paper.paper_url || paper.openalex_url || "#"} target="_blank" rel="noopener">{paper.title}</a>
                      {#if paper.year || paper.venue}
                        <div class="li-meta">{paper.year || "—"} · {paper.venue || "Venue N/A"}</div>
                      {/if}
                    </span>
                  </span>
                  <span class="badge">{fmt(paper.citation_count)} cites</span>
                </div>
              {/each}
            {:else}
              <p style="color: var(--muted); margin: 0;">
                {stats.citation_note || "Citation data unavailable (OpenAlex lookup failed)."}
              </p>
            {/if}
          </div>
        </div>
      </section>
    </ScrollReveal>

    <ScrollReveal>
      <section class="section" id="distributions">
        <div class="section-head"><span class="eyebrow">Trends</span><h2>Distributions</h2></div>
        <div class="grid">
          <div class="panel">{#if yearOption}<EChart option={yearOption} height="320px" />{:else}<p>No data.</p>{/if}</div>
          <div class="panel">{#if categoryOption}<EChart option={categoryOption} height="320px" />{:else}<p>No data.</p>{/if}</div>
          <div class="panel">{#if topicOption}<EChart option={topicOption} height="320px" />{:else}<p>No data.</p>{/if}</div>
        </div>
      </section>
    </ScrollReveal>

    <ScrollReveal>
      <section class="section" id="methods">
        <div class="section-head"><span class="eyebrow">Techniques</span><h2>Method &amp; domain signals</h2></div>
        <div class="grid">
          <div class="panel">{#if methodOption}<EChart option={methodOption} height="320px" />{:else}<p>No data.</p>{/if}</div>
          <div class="panel">{#if domainOption}<EChart option={domainOption} height="320px" />{:else}<p>No data.</p>{/if}</div>
          <div class="panel">{#if radarOption}<EChart option={radarOption} height="320px" />{:else}<p>Not enough method data for radar.</p>{/if}</div>
        </div>
      </section>
    </ScrollReveal>

    <ScrollReveal>
      <section class="section" id="venues">
        <div class="section-head"><span class="eyebrow">Where it's published</span><h2>Venues &amp; strata</h2></div>
        <div class="grid">
          <div class="panel">{#if venueOption}<EChart option={venueOption} height="360px" />{:else}<p>No data.</p>{/if}</div>
          <div class="panel">{#if strataOption}<EChart option={strataOption} height="360px" />{:else}<p>No data.</p>{/if}</div>
          <div class="panel">
            <h3>Top venues</h3>
            <div class="list">
              {#if filteredVenues?.length}
                {#each filteredVenues.slice(0, 10) as v}
                  <div class="list-item">
                    <span>{@html makeChip(v.venue, venueIcons[v.venue] || "🏛️")}</span>
                    <span class="badge">{fmt(v.count)}</span>
                  </div>
                {/each}
              {:else}<p style="color: var(--muted);">No venue data.</p>{/if}
            </div>
          </div>
        </div>
      </section>
    </ScrollReveal>

    <ScrollReveal>
      <section class="section">
        <div class="section-head"><span class="eyebrow">Reproducibility</span><h2>Code availability &amp; repos</h2></div>
        <div class="grid">
          <div class="panel">{#if codeOption}<EChart option={codeOption} height="300px" />{:else}<p>No data.</p>{/if}</div>
          <div class="panel">{#if langOption}<EChart option={langOption} height="300px" />{:else}<p style="color:var(--muted);">No language data (run without --skip-code-fetch).</p>{/if}</div>
          <div class="panel">
            <h3>Top GitHub repos</h3>
            <div class="list">
              {#if stats.top_repos?.length}
                {#each stats.top_repos as repo, idx}
                  <div class="list-item">
                    <span class="li-main"><span class="rank">{idx + 1}</span><span class="li-text"><a href={repo.url} target="_blank" rel="noopener">{repo.full_name}</a></span></span>
                    <span style="display:flex;align-items:center;gap:8px;">
                      {#if repo.language}<span class="chip"><span class="icon">{langIcons[repo.language] || "💻"}</span>{repo.language}</span>{/if}
                      <span class="badge">★ {fmt(repo.stars)}</span>
                    </span>
                  </div>
                {/each}
              {:else}<p style="color: var(--muted);">No GitHub metadata (run without --skip-code-fetch + set GITHUB_TOKEN).</p>{/if}
            </div>
          </div>
        </div>
      </section>
    </ScrollReveal>

    <ScrollReveal>
      <section class="section">
        <div class="section-head"><span class="eyebrow">Benchmarks</span><h2>Top cited datasets</h2></div>
        <div class="grid">
          <div class="panel">{#if datasetOption}<EChart option={datasetOption} height="340px" />{:else}<p>No data.</p>{/if}</div>
          <div class="panel">
            <h3>Datasets by usage</h3>
            <div class="list">
              {#each psDatasets as ds}
                <div class="list-item">
                  <span>
                    <a href={ds.source_url} target="_blank" rel="noopener" style="text-transform:capitalize;">{ds.dataset}</a>
                    {#if getGitHubStars(ds.source_url)}<span class="badge" style="margin-left:8px;">★ {fmt(getGitHubStars(ds.source_url))}</span>{/if}
                  </span>
                  <span class="badge">{fmt(ds.count)} papers</span>
                </div>
              {/each}
            </div>
          </div>
        </div>
      </section>
    </ScrollReveal>

    <ScrollReveal>
      <section class="section" id="table">
        <div class="section-head"><span class="eyebrow">Explore</span><h2>Paper explorer</h2></div>
        <div class="panel">
          <div class="filter-bar">
            <div class="search-field">
              <span class="s-icon">🔍</span>
              <input placeholder="Search title or venue…" bind:value={query} />
            </div>
            <select bind:value={category}>{#each categories as cat}<option value={cat}>{cat}</option>{/each}</select>
            <select bind:value={domain}>{#each domains as d}<option value={d}>{d === "All" ? "All domains" : d}</option>{/each}</select>
            <select bind:value={yearFilter}>{#each years as y}<option value={y}>{y === "All" ? "All years" : y}</option>{/each}</select>
            <button class="reset-btn" on:click={resetFilters}>Reset</button>
            <div class="count-chip">{fmt(filtered.length)} papers</div>
          </div>
          <div class="table-wrap">
            <table class="table">
              <thead>
                <tr><th>Year</th><th>Title</th><th>Venue</th><th>Category</th><th>Section</th><th>Code</th></tr>
              </thead>
              <tbody>
                {#each pageItems as p}
                  <tr>
                    <td>{p.year || "—"}</td>
                    <td><a href={p.paper_url || "#"} target="_blank" rel="noopener">{p.title}</a></td>
                    <td>{p.venue}</td>
                    <td><span class="tag">{p.category}</span></td>
                    <td>{p.subcategory || "—"}</td>
                    <td>{#if p.code_url}<a href={p.code_url} target="_blank" rel="noopener">Code ↗</a>{:else}—{/if}</td>
                  </tr>
                {/each}
                {#if !pageItems.length}
                  <tr><td colspan="6" style="text-align:center;color:var(--muted);padding:28px;">No papers match these filters.</td></tr>
                {/if}
              </tbody>
            </table>
          </div>
          <div class="pagination">
            <button on:click={() => (page = Math.max(1, page - 1))} disabled={page === 1}>← Prev</button>
            <span>Page {page} of {pageCount}</span>
            <button on:click={() => (page = Math.min(pageCount, page + 1))} disabled={page === pageCount}>Next →</button>
          </div>
        </div>
      </section>
    </ScrollReveal>

    <ScrollReveal>
      <section class="section" id="resources">
        <div class="section-head"><span class="eyebrow">Resources</span><h2>Toolboxes &amp; libraries</h2></div>
        <div class="grid">
          {#each resources.filter((r) => r.category === "Toolbox") as res}
            <div class="res-item">
              <a href={res.url} target="_blank" rel="noopener">{res.title}</a>
              {#if getGitHubStars(res.url)}<span class="badge">★ {fmt(getGitHubStars(res.url))}</span>{/if}
            </div>
          {/each}
        </div>
      </section>
    </ScrollReveal>

    <ScrollReveal>
      <section class="section">
        <div class="section-head"><span class="eyebrow">Data</span><h2>Datasets</h2></div>
        <div class="grid">
          {#each resources.filter((r) => r.category === "Dataset") as res}
            <div class="res-item">
              <a href={res.url} target="_blank" rel="noopener">{res.title}</a>
              {#if getGitHubStars(res.url)}<span class="badge">★ {fmt(getGitHubStars(res.url))}</span>{/if}
            </div>
          {/each}
        </div>
      </section>
    </ScrollReveal>

    <ScrollReveal>
      <section class="section">
        <div class="section-head"><span class="eyebrow">Reading</span><h2>Survey papers</h2></div>
        <p class="section-sub">
          Citation counts from <a href="https://openalex.org" target="_blank" rel="noopener">OpenAlex</a>
          {#if citationsLoading}<span style="font-size:12px;"> (loading…)</span>{/if}
        </p>
        <div class="list">
          {#each resources.filter((r) => r.category === "Survey Paper") as res}
            <div class="list-item">
              <span><a href={res.url} target="_blank" rel="noopener">{res.title}</a></span>
              {#if surveyCitations[res.title] !== undefined}
                <span class="badge">{fmt(surveyCitations[res.title])} cites</span>
              {:else if citationsLoading}
                <span class="badge" style="opacity:0.4;">…</span>
              {/if}
            </div>
          {/each}
        </div>
      </section>
    </ScrollReveal>
  {/if}

  <footer>
    Static SPA built with Svelte + ECharts · Data generated by the Python pipeline (see README) ·
    Citations via OpenAlex.
  </footer>
</main>
