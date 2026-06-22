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
  let workspaceHydrated = false;
  let savedPaperIds = [];
  let reviewMeta = {};
  let workspaceOpen = false;
  let compareIds = [];
  let compareOpen = false;
  let toast = "";
  let toastTimer;
  let searchInput;

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

  onMount(() => {
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

    try {
      const workspace = JSON.parse(localStorage.getItem("paper-review-workspace") || "{}");
      savedPaperIds = Array.isArray(workspace.savedPaperIds) ? workspace.savedPaperIds : [];
      reviewMeta = workspace.reviewMeta && typeof workspace.reviewMeta === "object" ? workspace.reviewMeta : {};
    } catch (e) {
      savedPaperIds = [];
      reviewMeta = {};
    }
    workspaceHydrated = true;

  });

  /* ---------------------------------------------------------
     Filters / table state
     --------------------------------------------------------- */
  let query = "";
  let category = "All";
  let domain = "All";
  let yearFilter = "All";
  let codeOnly = false;
  let savedOnly = false;
  let sortBy = "newest";
  let viewMode = "cards";
  let page = 1;
  const pageSize = 18;

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
  const fmtDate = (value) => value
    ? new Intl.DateTimeFormat("en-US", { dateStyle: "medium" }).format(new Date(value))
    : "";
  const paperKey = (paper) => paper.paper_url || `${paper.title}::${paper.year || ""}`;

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
  $: codePaperCount = papers.filter((paper) => paper.has_code || paper.code_url).length;
  $: codePercentage = papers.length ? ((codePaperCount / papers.length) * 100).toFixed(1) : 0;
  $: citationEntries = stats.paper_citations?.length ? stats.paper_citations : (stats.top_cited || []);
  $: citationMap = citationEntries.reduce((acc, paper) => {
    acc[paper.title] = paper.citation_count;
    return acc;
  }, {});

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
  $: page = 1, query, category, domain, yearFilter, codeOnly, savedOnly, sortBy; // reset page on filter change
  $: filtered = papers.filter((p) => {
    const q = query.trim().toLowerCase();
    const matchesQuery =
      !q ||
      p.title.toLowerCase().includes(q) ||
      (p.venue && p.venue.toLowerCase().includes(q)) ||
      (p.domain && p.domain.toLowerCase().includes(q)) ||
      (p.category && p.category.toLowerCase().includes(q)) ||
      (p.subcategory && p.subcategory.toLowerCase().includes(q));
    const matchesCategory = category === "All" || p.category === category;
    const matchesDomain = domain === "All" || p.domain === domain;
    const matchesYear = yearFilter === "All" || p.year === yearFilter;
    const matchesCode = !codeOnly || p.has_code || p.code_url;
    const matchesSaved = !savedOnly || savedPaperIds.includes(paperKey(p));
    return matchesQuery && matchesCategory && matchesDomain && matchesYear && matchesCode && matchesSaved;
  }).sort((a, b) => {
    if (sortBy === "oldest") return (a.year || 0) - (b.year || 0) || a.title.localeCompare(b.title);
    if (sortBy === "title") return a.title.localeCompare(b.title);
    if (sortBy === "cited") return (citationMap[b.title] || 0) - (citationMap[a.title] || 0) || (b.year || 0) - (a.year || 0);
    return (b.year || 0) - (a.year || 0) || a.title.localeCompare(b.title);
  });
  $: pageCount = filtered.length ? Math.max(1, Math.ceil(filtered.length / pageSize)) : 1;
  $: page = Math.min(page, pageCount);
  $: pageItems = filtered.slice((page - 1) * pageSize, page * pageSize);
  $: savedPapers = savedPaperIds.map((id) => papers.find((paper) => paperKey(paper) === id)).filter(Boolean);
  $: comparePapers = compareIds.map((id) => papers.find((paper) => paperKey(paper) === id)).filter(Boolean);
  $: activeFilterCount = [category !== "All", domain !== "All", yearFilter !== "All", codeOnly, savedOnly].filter(Boolean).length;

  function persistWorkspace() {
    if (!workspaceHydrated) return;
    try {
      localStorage.setItem("paper-review-workspace", JSON.stringify({ savedPaperIds, reviewMeta }));
    } catch (e) {
      /* ignore storage failures */
    }
  }

  function showToast(message) {
    toast = message;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => (toast = ""), 2200);
  }

  function toggleSaved(paper) {
    const id = paperKey(paper);
    const isSaved = savedPaperIds.includes(id);
    savedPaperIds = isSaved ? savedPaperIds.filter((item) => item !== id) : [...savedPaperIds, id];
    if (!isSaved && !reviewMeta[id]) {
      reviewMeta = { ...reviewMeta, [id]: { status: "To read", notes: "" } };
    }
    persistWorkspace();
    showToast(isSaved ? "Removed from reading list" : "Saved to reading list");
  }

  function updateReviewMeta(paper, field, value) {
    const id = paperKey(paper);
    reviewMeta = {
      ...reviewMeta,
      [id]: { status: "To read", notes: "", ...(reviewMeta[id] || {}), [field]: value },
    };
    persistWorkspace();
  }

  function clearReadingList() {
    savedPaperIds = [];
    compareIds = [];
    persistWorkspace();
    showToast("Reading list cleared");
  }

  function toggleCompare(paper) {
    const id = paperKey(paper);
    if (compareIds.includes(id)) {
      compareIds = compareIds.filter((item) => item !== id);
      return;
    }
    if (compareIds.length >= 3) {
      showToast("Compare up to three papers at a time");
      return;
    }
    compareIds = [...compareIds, id];
  }

  function jumpToExplorer() {
    document.getElementById("table")?.scrollIntoView({ behavior: "smooth", block: "start" });
    setTimeout(() => searchInput?.focus(), 350);
  }

  function applyTopic(topic) {
    query = topic;
    jumpToExplorer();
  }

  function escapeCell(value) {
    return String(value || "").replace(/\|/g, "\\|").replace(/\n/g, " ");
  }

  function exportReadingList() {
    if (!savedPapers.length) {
      showToast("Save papers before exporting");
      return;
    }
    const rows = savedPapers.map((paper) => {
      const meta = reviewMeta[paperKey(paper)] || {};
      return `| [${escapeCell(paper.title)}](${paper.paper_url || "#"}) | ${paper.year || "—"} | ${escapeCell(paper.venue)} | ${escapeCell(paper.domain)} | ${escapeCell(meta.status || "To read")} | ${escapeCell(meta.notes)} |`;
    });
    const content = `# Literature review reading list\n\nExported from SafeGraph Research Atlas.\n\n| Paper | Year | Venue | Domain | Status | Notes |\n| --- | ---: | --- | --- | --- | --- |\n${rows.join("\n")}\n`;
    const url = URL.createObjectURL(new Blob([content], { type: "text/markdown;charset=utf-8" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "safegraph-literature-review.md";
    anchor.click();
    URL.revokeObjectURL(url);
    showToast("Reading list exported");
  }

  async function copyReference(paper) {
    const reference = `${paper.title}. ${paper.venue || ""}${paper.year ? ` (${paper.year})` : ""}. ${paper.paper_url || ""}`.trim();
    try {
      await navigator.clipboard.writeText(reference);
      showToast("Reference copied");
    } catch (e) {
      showToast("Could not copy reference");
    }
  }

  function handleKeydown(event) {
    if (event.key === "Escape") {
      workspaceOpen = false;
      compareOpen = false;
    }
    if (event.key === "/" && !["INPUT", "TEXTAREA", "SELECT"].includes(event.target?.tagName)) {
      event.preventDefault();
      jumpToExplorer();
    }
  }

  function resetFilters() {
    query = "";
    category = "All";
    domain = "All";
    yearFilter = "All";
    codeOnly = false;
    savedOnly = false;
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
    legend: { type: "scroll", bottom: 0, textStyle: { color: c.muted }, icon: "circle", pageTextStyle: { color: c.muted }, pageIconColor: c.muted, pageIconInactiveColor: c.split },
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
    { id: "table", label: "Discover" },
    { id: "top-cited", label: "Top cited" },
    { id: "distributions", label: "Landscape" },
    { id: "methods", label: "Methods" },
    { id: "resources", label: "Resources" },
  ];
</script>

<svelte:window on:keydown={handleKeydown} />

<div class="glow" aria-hidden="true"></div>

<nav class="nav">
  <div class="nav-brand">
    <span class="nav-logo">S</span>
    <span><strong>SafeGraph</strong><small>Research Atlas</small></span>
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
  <button class="workspace-button" on:click={() => (workspaceOpen = true)} aria-label="Open reading list">
    <span>Reading list</span>
    <strong>{savedPaperIds.length}</strong>
  </button>
</nav>

<main>
  <header class="hero">
    <div class="hero-layout">
      <ScrollReveal>
        <span class="pill">Living literature map · Updated automatically</span>
        <h1>Find the papers that<br /><span class="grad">move your review forward.</span></h1>
        <p class="lede">
          Search, compare, annotate, and organize graph and transformer research for fraud,
          anomaly, and outlier detection—all in one evidence-first workspace.
        </p>
        <div class="hero-search">
          <span aria-hidden="true">⌕</span>
          <input
            aria-label="Search the paper collection"
            placeholder="Try “heterogeneous graph”, “financial fraud”, or a venue…"
            bind:value={query}
            on:keydown={(event) => event.key === "Enter" && jumpToExplorer()}
          />
          <button on:click={jumpToExplorer}>Search collection</button>
        </div>
        <div class="topic-row" aria-label="Popular research topics">
          <span>Popular:</span>
          {#each (stats.topics || []).slice(0, 4) as topic}
            <button on:click={() => applyTopic(topic.topic)}>{topic.topic}</button>
          {/each}
        </div>
      </ScrollReveal>
      <aside class="hero-note" aria-label="Literature review workflow">
        <div class="hero-note-head"><span>Review workflow</span><strong>01—04</strong></div>
        <ol>
          <li><span>01</span><div><strong>Discover</strong><small>Search 500+ curated papers</small></div></li>
          <li><span>02</span><div><strong>Shortlist</strong><small>Save promising evidence</small></div></li>
          <li><span>03</span><div><strong>Compare</strong><small>Evaluate methods side by side</small></div></li>
          <li><span>04</span><div><strong>Synthesize</strong><small>Add notes and export your matrix</small></div></li>
        </ol>
      </aside>
    </div>
    <div class="stat-grid">
      <ScrollReveal delay={0}>
        <div class="stat featured">
          <div class="label"><span class="stat-ico">📄</span> Total papers</div>
          <div class="value"><AnimatedNumber value={papers.length} delay={150} /></div>
          <div class="sub">across {categories.length - 1} categories</div>
        </div>
      </ScrollReveal>
      <ScrollReveal delay={80}>
        <div class="stat">
          <div class="label"><span class="stat-ico">💻</span> With code</div>
          <div class="value">
            <AnimatedNumber value={codePaperCount} delay={250} />
          </div>
          <div class="sub">
            {codePercentage}% of all papers
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

  <section class="section discover" id="table">
    <div class="discover-heading">
      <div>
        <span class="eyebrow">Research workspace</span>
        <h2>Discover and triage papers</h2>
        <p>Use <kbd>/</kbd> to jump to search. Save papers to build a persistent reading list.</p>
      </div>
      <div class="view-switch" aria-label="Choose results view">
        <button class:active={viewMode === "cards"} on:click={() => (viewMode = "cards")} aria-pressed={viewMode === "cards"}>Cards</button>
        <button class:active={viewMode === "compact"} on:click={() => (viewMode = "compact")} aria-pressed={viewMode === "compact"}>Compact</button>
      </div>
    </div>

    <div class="explorer-shell">
      <aside class="filter-panel">
        <div class="filter-title">
          <strong>Refine results</strong>
          {#if activeFilterCount}<span>{activeFilterCount} active</span>{/if}
        </div>

        <label class="filter-search">
          <span>Search</span>
          <div><span aria-hidden="true">⌕</span><input bind:this={searchInput} bind:value={query} placeholder="Title, venue, domain…" /></div>
        </label>

        <label>
          <span>Research family</span>
          <select bind:value={category}>{#each categories as cat}<option value={cat}>{cat === "All" ? "All research families" : cat}</option>{/each}</select>
        </label>
        <label>
          <span>Application domain</span>
          <select bind:value={domain}>{#each domains as d}<option value={d}>{d === "All" ? "All domains" : d}</option>{/each}</select>
        </label>
        <div class="filter-split">
          <label>
            <span>Year</span>
            <select bind:value={yearFilter}>{#each years as y}<option value={y}>{y === "All" ? "Any year" : y}</option>{/each}</select>
          </label>
          <label>
            <span>Sort by</span>
            <select bind:value={sortBy}>
              <option value="newest">Newest</option>
              <option value="oldest">Oldest</option>
              <option value="cited">Most cited</option>
              <option value="title">Title A–Z</option>
            </select>
          </label>
        </div>
        <label class="check-filter"><input type="checkbox" bind:checked={codeOnly} /><span><strong>Code available</strong><small>Reproducible papers only</small></span></label>
        <label class="check-filter"><input type="checkbox" bind:checked={savedOnly} /><span><strong>Saved papers</strong><small>Your current reading list</small></span></label>

        <div class="quick-topics">
          <span>Topic shortcuts</span>
          <div>
            {#each (stats.topics || []).slice(0, 6) as topic}
              <button class:active={query.toLowerCase() === topic.topic.toLowerCase()} on:click={() => (query = topic.topic)}>{topic.topic}</button>
            {/each}
          </div>
        </div>
        <button class="reset-btn full" on:click={resetFilters} disabled={!query && !activeFilterCount}>Clear all filters</button>
      </aside>

      <div class="results-panel">
        <div class="results-toolbar">
          <div><strong>{fmt(filtered.length)}</strong> papers <span>of {fmt(papers.length)} in the collection</span></div>
          <button class="saved-shortcut" on:click={() => (workspaceOpen = true)}>Saved <strong>{savedPaperIds.length}</strong></button>
        </div>

        {#if viewMode === "cards"}
          <div class="paper-grid">
            {#each pageItems as paper}
              <article class:saved={savedPaperIds.includes(paperKey(paper))} class="paper-card">
                <div class="paper-card-top">
                  <div class="paper-meta"><span>{paper.year || "N/A"}</span><span>{paper.venue || "Venue unavailable"}</span></div>
                  <button
                    class:active={savedPaperIds.includes(paperKey(paper))}
                    class="save-button"
                    on:click={() => toggleSaved(paper)}
                    aria-label={savedPaperIds.includes(paperKey(paper)) ? `Remove ${paper.title} from reading list` : `Save ${paper.title} to reading list`}
                    title="Save to reading list"
                  >{savedPaperIds.includes(paperKey(paper)) ? "●" : "○"}</button>
                </div>
                <h3><a href={paper.paper_url || "#"} target="_blank" rel="noopener">{paper.title}</a></h3>
                <div class="paper-tags">
                  <span>{paper.domain || "General"}</span>
                  <span>{paper.category}</span>
                  {#if citationMap[paper.title]}<span class="citation-tag">{fmt(citationMap[paper.title])} citations</span>{/if}
                </div>
                <div class="paper-card-actions">
                  <a href={paper.paper_url || "#"} target="_blank" rel="noopener">Open paper ↗</a>
                  {#if paper.code_url}<a class="code-link" href={paper.code_url} target="_blank" rel="noopener">Code ↗</a>{/if}
                  <button class:active={compareIds.includes(paperKey(paper))} on:click={() => toggleCompare(paper)}>
                    {compareIds.includes(paperKey(paper)) ? "Selected" : "Compare"}
                  </button>
                </div>
              </article>
            {/each}
          </div>
        {:else}
          <div class="compact-results">
            {#each pageItems as paper}
              <article class:saved={savedPaperIds.includes(paperKey(paper))}>
                <button class:active={savedPaperIds.includes(paperKey(paper))} class="save-button" on:click={() => toggleSaved(paper)} aria-label="Toggle saved paper">{savedPaperIds.includes(paperKey(paper)) ? "●" : "○"}</button>
                <div class="compact-year">{paper.year || "—"}</div>
                <div class="compact-main">
                  <h3><a href={paper.paper_url || "#"} target="_blank" rel="noopener">{paper.title}</a></h3>
                  <p>{paper.venue || "Venue unavailable"} · {paper.domain || "General"}</p>
                </div>
                <div class="compact-actions">
                  {#if paper.code_url}<a href={paper.code_url} target="_blank" rel="noopener">Code</a>{/if}
                  <button class:active={compareIds.includes(paperKey(paper))} on:click={() => toggleCompare(paper)}>Compare</button>
                </div>
              </article>
            {/each}
          </div>
        {/if}

        {#if !pageItems.length}
          <div class="empty-state"><span>⌕</span><h3>No matching papers</h3><p>Try removing a filter or using a broader search term.</p><button on:click={resetFilters}>Reset search</button></div>
        {/if}

        {#if pageItems.length}
          <div class="pagination">
            <button on:click={() => (page = Math.max(1, page - 1))} disabled={page === 1}>← Previous</button>
            <span>Page {page} of {pageCount}</span>
            <button on:click={() => (page = Math.min(pageCount, page + 1))} disabled={page === pageCount}>Next →</button>
          </div>
        {/if}
      </div>
    </div>
  </section>

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
          Ranked by {stats.citation_source || "OpenAlex"}-indexed citations.
          {#if stats.citation_updated_at} Updated {fmtDate(stats.citation_updated_at)}.{/if}
          {#if stats.citation_coverage}
            Matched {fmt(stats.citation_coverage.matched)} of {fmt(stats.citation_coverage.queried)} unique papers.
          {/if}
          Counts vary across scholarly indexes; this dashboard reports OpenAlex only and does not mix sources.
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
                  <span class="badge">{fmt(paper.citation_count)} OpenAlex cites</span>
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
                    <span class="repo-meta">
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
          Citation counts are matched and cached during the automated build using
          <a href="https://openalex.org" target="_blank" rel="noopener">OpenAlex</a>.
        </p>
        <div class="list">
          {#each resources.filter((r) => r.category === "Survey Paper") as res}
            <div class="list-item">
              <span><a href={res.url} target="_blank" rel="noopener">{res.title}</a></span>
              {#if res.citation_count !== undefined}
                <a class="badge" href={res.openalex_url || res.url} target="_blank" rel="noopener">{fmt(res.citation_count)} OpenAlex cites</a>
              {:else}
                <span class="badge" style="opacity:0.55;">Not indexed</span>
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

{#if compareIds.length}
  <div class="compare-dock" aria-live="polite">
    <div><span>{compareIds.length}</span><strong>{compareIds.length === 1 ? "paper" : "papers"} selected</strong><small>Select up to 3 to compare</small></div>
    <button class="text-button" on:click={() => (compareIds = [])}>Clear</button>
    <button class="primary-button" on:click={() => (compareOpen = true)}>Compare papers</button>
  </div>
{/if}

{#if workspaceOpen}
  <div class="drawer-backdrop" aria-hidden="true"></div>
  <div class="workspace-drawer" role="dialog" aria-modal="true" aria-label="Reading list" tabindex="-1">
    <header>
      <div><span class="eyebrow">Your workspace</span><h2>Reading list</h2><p>{savedPapers.length} saved {savedPapers.length === 1 ? "paper" : "papers"}</p></div>
      <button class="close-button" on:click={() => (workspaceOpen = false)} aria-label="Close reading list">×</button>
    </header>
    <div class="drawer-actions">
      <button class="primary-button" on:click={exportReadingList} disabled={!savedPapers.length}>Export review matrix</button>
      <button class="text-button danger" on:click={clearReadingList} disabled={!savedPapers.length}>Clear list</button>
    </div>
    <div class="saved-list">
      {#each savedPapers as paper}
        <article class="saved-paper">
          <div class="saved-paper-head">
            <div><span>{paper.year || "—"} · {paper.venue || "Venue unavailable"}</span><h3><a href={paper.paper_url || "#"} target="_blank" rel="noopener">{paper.title}</a></h3></div>
            <button class="remove-button" on:click={() => toggleSaved(paper)} aria-label={`Remove ${paper.title}`}>×</button>
          </div>
          <div class="saved-controls">
            <label><span>Review status</span><select value={reviewMeta[paperKey(paper)]?.status || "To read"} on:change={(event) => updateReviewMeta(paper, "status", event.currentTarget.value)}><option>To read</option><option>Reading</option><option>Reviewed</option><option>Key evidence</option></select></label>
            <button on:click={() => copyReference(paper)}>Copy reference</button>
          </div>
          <label class="notes-field"><span>Review notes</span><textarea rows="3" placeholder="Finding, limitation, dataset, follow-up…" value={reviewMeta[paperKey(paper)]?.notes || ""} on:input={(event) => updateReviewMeta(paper, "notes", event.currentTarget.value)}></textarea></label>
        </article>
      {:else}
        <div class="drawer-empty"><span>◇</span><h3>Your reading list is empty</h3><p>Save papers from the explorer to annotate and export them later.</p><button class="primary-button" on:click={() => { workspaceOpen = false; jumpToExplorer(); }}>Discover papers</button></div>
      {/each}
    </div>
  </div>
{/if}

{#if compareOpen}
  <div class="modal-backdrop">
    <div class="compare-modal" role="dialog" aria-modal="true" aria-labelledby="compare-title" tabindex="-1">
      <header><div><span class="eyebrow">Evidence matrix</span><h2 id="compare-title">Compare selected papers</h2></div><button class="close-button" on:click={() => (compareOpen = false)} aria-label="Close comparison">×</button></header>
      <div class="comparison-grid" style={`--comparison-count:${Math.max(comparePapers.length, 1)}`}>
        {#each comparePapers as paper}
          <article>
            <div class="comparison-title"><span>{paper.year || "—"}</span><h3><a href={paper.paper_url || "#"} target="_blank" rel="noopener">{paper.title}</a></h3></div>
            <dl>
              <div><dt>Venue</dt><dd>{paper.venue || "Not available"}</dd></div>
              <div><dt>Domain</dt><dd>{paper.domain || "General"}</dd></div>
              <div><dt>Research family</dt><dd>{paper.category || "Not available"}</dd></div>
              <div><dt>Section</dt><dd>{paper.subcategory || "Not specified"}</dd></div>
              <div><dt>Citations</dt><dd>{citationMap[paper.title] ? fmt(citationMap[paper.title]) : "Not indexed"}</dd></div>
              <div><dt>Code</dt><dd>{#if paper.code_url}<a href={paper.code_url} target="_blank" rel="noopener">Repository ↗</a>{:else}Not linked{/if}</dd></div>
            </dl>
            <div class="comparison-actions"><button on:click={() => toggleSaved(paper)}>{savedPaperIds.includes(paperKey(paper)) ? "Saved" : "Save paper"}</button><button on:click={() => copyReference(paper)}>Copy reference</button></div>
          </article>
        {/each}
      </div>
    </div>
  </div>
{/if}

{#if toast}<div class="toast" role="status">{toast}</div>{/if}
