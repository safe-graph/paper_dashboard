<script>
  import EChart from "./lib/EChart.svelte";
  import dataInline from "../public/data.json";

  let data = dataInline;
  let error = "";
  let loading = false;
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

  const makeChip = (label, icon) => `<span class="chip"><span class="icon">${icon || "★"}</span>${label}</span>`;

  const fmt = (n) => (n || n === 0 ? n.toLocaleString("en-US") : "–");

  const palette = {
    blue: "#94b0ff",
    teal: "#7fc8c2",
    coral: "#f2b6a0",
    lavender: "#c6b2ff",
    gold: "#f7d19e",
    slate: "#9dbad5",
  };
  const chartText = "#e6edf3";
  const chartMuted = "#b7c3cd";
  const chartAxis = "#63707f";

  // Data is bundled statically to avoid fetch/runtime path issues on GitHub Pages.
  // If we ever need to refresh via fetch, we can add a lightweight onMount fetch fallback.

  $: papers = data?.papers || [];
  $: stats = data?.stats || {};
  $: resources = data?.resources || [];
  $: categories = ["All", ...new Set(papers.map((p) => p.category).filter(Boolean))];
  $: domains = ["All", ...new Set(stats.domain_counts?.map((d) => d.domain) || [])];
  $: years = ["All", ...Array.from(new Set(papers.map((p) => p.year).filter(Boolean))).sort((a, b) => b - a)];
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

  const baseBar = (items, xKey, yKey, title, horizontal = false, color = palette.blue, labelOpts = {}) => ({
    textStyle: { color: chartText },
    title: { text: title, textStyle: { color: chartText, fontSize: 14 } },
    tooltip: { trigger: "axis" },
    grid: { left: horizontal ? 140 : 50, right: 20, top: 30, bottom: 40 },
    xAxis: horizontal
      ? { type: "value", axisLine: { lineStyle: { color: chartAxis } } }
      : {
          type: "category",
          data: items.map((d) => d[xKey]),
          axisLabel: { rotate: 30, color: chartMuted },
          axisLine: { lineStyle: { color: chartAxis } },
        },
    yAxis: horizontal
      ? {
          type: "category",
          data: items.map((d) => d[yKey]),
          axisLabel: { color: chartMuted },
          axisLine: { lineStyle: { color: chartAxis } },
        }
      : { type: "value", axisLine: { lineStyle: { color: chartAxis } } },
    series: [
      {
        type: "bar",
        data: items.map((d) => d[horizontal ? xKey : yKey]),
        itemStyle: { color },
        showBackground: true,
        backgroundStyle: { color: "rgba(255,255,255,0.04)" },
        label: labelOpts,
      },
    ],
  });

  const pie = (items, name, title) => ({
    textStyle: { color: chartText },
    title: { text: title, textStyle: { color: chartText, fontSize: 14 } },
    tooltip: { trigger: "item" },
    series: [
      {
        type: "pie",
        radius: ["35%", "60%"],
        center: ["50%", "55%"],
        data: items.map((d) => ({ name: d[name], value: d.count || d.bytes || d.value })),
        label: { color: chartText },
      },
    ],
  });

  $: yearOption = stats.year_counts ? baseBar(stats.year_counts, "year", "count", "Papers by year", false, palette.blue, { show: false }) : null;
  $: categoryOption = stats.category_counts ? baseBar(stats.category_counts, "count", "category", "Entries by category", true, palette.teal) : null;
  $: topicOption = stats.topics ? baseBar(stats.topics, "topic", "count", "Frequent title terms", false, palette.coral) : null;
  $: methodOption = stats.method_counts ? baseBar(stats.method_counts, "count", "method", "Method families", true, palette.lavender) : null;
  $: domainOption = stats.domain_counts ? baseBar(stats.domain_counts, "count", "domain", "Domain focus", true, palette.slate) : null;
  $: venueOption = stats.venue_counts ? baseBar(stats.venue_counts.slice(0, 12), "count", "venue", "Top venues", true, palette.blue) : null;
  $: strataOption = stats.venue_strata ? pie(stats.venue_strata, "stratum", "Venue strata") : null;
  $: datasetOption = stats.dataset_counts ? baseBar(stats.dataset_counts, "count", "dataset", "Dataset mentions", true, palette.teal) : null;
  $: codeOption = stats.code_availability
    ? pie(
        [
          { label: "With code", count: stats.code_availability.with_code },
          { label: "No code", count: stats.code_availability.without_code },
        ],
        "label",
        "Code availability"
      )
    : null;
  $: langOption = stats.language_counts && stats.language_counts.length
    ? pie(stats.language_counts, "language", "Language share (code repos)")
    : null;
</script>

<div class="glow" aria-hidden="true"></div>
<main>
  <header>
    <span class="pill">Graph & Transformer Fraud Detection Papers</span>
    <h1>Interactive summary of the Safe-Graph curated list</h1>
    <p class="lede">
      SPA front-end built with Svelte + ECharts. Data is fetched from <code>data.json</code> generated by the Python pipeline.
    </p>
    <div class="grid">
      <div class="card">
        <h3>Total papers</h3>
        <div class="value">{fmt(stats.paper_count || papers.length)}</div>
      </div>
      <div class="card">
        <h3>Code availability</h3>
        <div class="value">
          {stats.code_availability
            ? `${fmt(stats.code_availability.with_code)} (${stats.code_availability.percentage || 0}%)`
            : "–"}
        </div>
      </div>
      <div class="card">
        <h3>Top venue</h3>
        <div class="value">{stats.venue_counts?.[0]?.venue || "–"}</div>
      </div>
      <div class="card">
        <h3>Dominant topic</h3>
        <div class="value">{stats.topics?.[0]?.topic || "–"}</div>
      </div>
    </div>
  </header>

  {#if loading}
    <section class="section"><div class="card">Loading…</div></section>
  {:else if error}
    <section class="section"><div class="card">{error}</div></section>
  {:else}
    <section class="section">
      <h2>What stands out</h2>
      <div class="card">
        <ul>
          {#if stats.insights?.length}
            {#each stats.insights as insight}
              <li>{insight}</li>
            {/each}
          {:else}
            <li>No insights available.</li>
          {/if}
        </ul>
      </div>
    </section>

    <section class="section">
      <h2>Top cited papers</h2>
      <div class="panel">
        <div class="list">
          {#if stats.top_cited?.length}
            {#each stats.top_cited as paper, idx}
              <div class="list-item">
                <span>
                  {idx + 1}. <a href={paper.paper_url || paper.openalex_url || "#"} target="_blank" rel="noopener">{paper.title}</a>
                  {#if paper.year || paper.venue}
                    <span style="color: var(--muted); font-size: 12px;">({paper.year || "—"} - {paper.venue || "Venue N/A"})</span>
                  {/if}
                </span>
                <span class="badge">{fmt(paper.citation_count)}</span>
              </div>
            {/each}
          {:else}
            <p style="color: var(--muted); margin: 0;">
              {stats.citation_note || "Citation data unavailable (OpenAlex lookup failed)."}
            </p>
          {/if}
        </div>
        {#if stats.citation_source}
          <p style="color: var(--muted); margin: 10px 0 0;">Source: {stats.citation_source}</p>
        {/if}
      </div>
    </section>

    <section class="section">
      <h2>Distributions</h2>
      <div class="grid">
        <div class="panel">{#if yearOption}<EChart option={yearOption} height="320px" />{:else}<p>No data.</p>{/if}</div>
        <div class="panel">{#if categoryOption}<EChart option={categoryOption} height="320px" />{:else}<p>No data.</p>{/if}</div>
        <div class="panel">{#if topicOption}<EChart option={topicOption} height="320px" />{:else}<p>No data.</p>{/if}</div>
      </div>
    </section>

    <section class="section">
      <h2>Method & domain signals</h2>
      <div class="grid">
        <div class="panel">{#if methodOption}<EChart option={methodOption} height="320px" />{:else}<p>No data.</p>{/if}</div>
        <div class="panel">{#if domainOption}<EChart option={domainOption} height="320px" />{:else}<p>No data.</p>{/if}</div>
      </div>
    </section>

    <section class="section">
      <h2>Venues and strata</h2>
      <div class="grid">
        <div class="panel">{#if venueOption}<EChart option={venueOption} height="360px" />{:else}<p>No data.</p>{/if}</div>
        <div class="panel">{#if strataOption}<EChart option={strataOption} height="360px" />{:else}<p>No data.</p>{/if}</div>
        <div class="panel">
          <h3 style="margin:0 0 8px;">Top venues</h3>
          <div class="list">
            {#if stats.venue_counts?.length}
              {#each stats.venue_counts.slice(0, 10) as v, idx}
                <div class="list-item" >
                  <span>{@html makeChip(v.venue, venueIcons[v.venue] || "🏛️")}</span>
                  <span class="badge">{fmt(v.count)}</span>
                </div>
              {/each}
            {:else}
              <p style="color: var(--muted);">No venue data.</p>
            {/if}
          </div>
        </div>
      </div>
    </section>

    <section class="section">
      <h2>Code availability & repos</h2>
      <div class="grid">
        <div class="panel">{#if codeOption}<EChart option={codeOption} height="280px" />{:else}<p>No data.</p>{/if}</div>
        <div class="panel">{#if langOption}<EChart option={langOption} height="280px" />{:else}<p>No language data.</p>{/if}</div>
        <div class="panel">
          <h3 style="margin:0 0 6px;">Top GitHub repos</h3>
          <div class="list">
            {#if stats.top_repos?.length}
              {#each stats.top_repos as repo, idx}
                <div class="list-item">
                  <span>{idx + 1}. <a href={repo.url} target="_blank" rel="noopener">{repo.full_name}</a></span>
                  <span style="display:flex;align-items:center;gap:8px;">
                    {#if repo.language}<span class="chip"><span class="icon">{langIcons[repo.language] || "💻"}</span>{repo.language}</span>{/if}
                    <span class="badge">★ {fmt(repo.stars)}</span>
                  </span>
                </div>
              {/each}
            {:else}
              <p style="color: var(--muted);">No GitHub metadata (run without --skip-code-fetch + set GITHUB_TOKEN).</p>
            {/if}
          </div>
        </div>
      </div>
    </section>

    <section class="section">
      <h2>Dataset mentions</h2>
      <div class="grid">
        <div class="panel">{#if datasetOption}<EChart option={datasetOption} height="300px" />{:else}<p>No dataset mentions detected.</p>{/if}</div>
        <div class="panel">
          <h3 style="margin:0 0 8px;">Most cited datasets</h3>
          <div class="list">
            {#if stats.dataset_counts?.length}
              {#each stats.dataset_counts as ds}
                <div class="list-item">
                  <span>{ds.dataset}</span>
                  <span class="badge">{fmt(ds.count)}</span>
                </div>
              {/each}
            {:else}
              <p style="color: var(--muted);">No dataset mentions detected.</p>
            {/if}
          </div>
        </div>
      </div>
    </section>

    <section class="section">
      <h2>Interactive paper table</h2>
      <div class="panel">
        <div class="filter-bar">
          <input placeholder="Search title or venue" bind:value={query} />
          <select bind:value={category}>
            {#each categories as c}<option value={c}>{c}</option>{/each}
          </select>
          <select bind:value={domain}>
            {#each domains as d}<option value={d}>{d}</option>{/each}
          </select>
          <select bind:value={yearFilter}>
            {#each years as y}<option value={y}>{y}</option>{/each}
          </select>
          <div class="chip">Showing {fmt(filtered.length)} papers</div>
        </div>
        <div style="overflow:auto;">
          <table class="table">
            <thead>
              <tr>
                <th>Year</th>
                <th>Title</th>
                <th>Venue</th>
                <th>Category</th>
                <th>Section</th>
                <th>Code</th>
              </tr>
            </thead>
            <tbody>
              {#each pageItems as p}
                <tr>
                  <td>{p.year || "—"}</td>
                  <td><a href={p.paper_url || "#"} target="_blank" rel="noopener">{p.title}</a></td>
                  <td>{p.venue}</td>
                  <td>{p.category}</td>
                  <td>{p.subcategory || "—"}</td>
                  <td>{#if p.code_url}<a href={p.code_url} target="_blank" rel="noopener">Code</a>{:else}—{/if}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        <div class="pagination">
          <button on:click={() => (page = Math.max(1, page - 1))} disabled={page === 1}>Prev</button>
          <span>Page {page} / {pageCount}</span>
          <button on:click={() => (page = Math.min(pageCount, page + 1))} disabled={page === pageCount}>Next</button>
        </div>
      </div>
    </section>

    <section class="section">
      <h2>Resources, toolboxes, surveys</h2>
      <div class="grid">
        {#each resources as res}
          <div class="panel">
            <div style="color: var(--muted); font-size:12px;text-transform:uppercase;letter-spacing:1px;">{res.category}</div>
            <a href={res.url} target="_blank" rel="noopener">{res.title}</a>
          </div>
        {/each}
      </div>
    </section>
  {/if}

  <footer>
    Built as a static SPA with Svelte + ECharts. Data comes from the Python pipeline (see README).
  </footer>
</main>
