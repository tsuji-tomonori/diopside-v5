const store = {
  get(key, fallback) {
    try {
      return JSON.parse(localStorage.getItem(`diopside:${key}`)) ?? fallback;
    } catch {
      return fallback;
    }
  },
  set(key, value) {
    localStorage.setItem(`diopside:${key}`, JSON.stringify(value));
  }
};

const state = {
  videos: [],
  tags: [],
  selectedTag: null,
  query: "",
  year: "",
  duration: "",
  sort: "published_desc",
  wordcloud: "",
  timestamp: "",
  favorites: store.get("favorites", []),
  history: store.get("history", []),
  recentSearches: store.get("recent-searches", [])
};

const els = {
  search: document.querySelector("#searchInput"),
  tags: document.querySelector("#tagFilters"),
  list: document.querySelector("#videoList"),
  count: document.querySelector("#resultCount"),
  detail: document.querySelector("#videoDetail"),
  filterSheet: document.querySelector("#filterSheet"),
  filterForm: document.querySelector("#filterForm"),
  filterTag: document.querySelector("#filterTagSelect"),
  clearFilter: document.querySelector("#clearFilterButton"),
  quick: document.querySelector("#quickChips"),
  recent: document.querySelector("#recentSearches"),
  favorites: document.querySelector("#favoriteVideos"),
  history: document.querySelector("#historyVideos"),
  clearTag: document.querySelector("#clearTagButton"),
  admin: document.querySelector("#adminPanel"),
  adminResult: document.querySelector("#adminResult"),
  adminData: document.querySelector("#adminData")
};

const json = async (path, options = {}) => {
  const response = await fetch(path, { headers: { Accept: "application/json", ...(options.headers || {}) }, ...options });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.message || `failed to load ${path}: ${response.status}`);
  return body;
};

const el = (tag, attrs = {}, children = []) => {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2).toLowerCase(), value);
    else if (value !== null && value !== undefined) node.setAttribute(key, String(value));
  }
  node.append(...children);
  return node;
};

const fmtDate = (value) => value ? new Intl.DateTimeFormat("ja-JP", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "日時未設定";
const fmtNumber = (value) => Number.isFinite(Number(value)) ? Number(value).toLocaleString("ja-JP") : "未設定";
const fmtBoolean = (value) => value === true ? "yes" : value === false ? "no" : "未設定";
const fmtDuration = (seconds) => {
  if (!Number.isFinite(Number(seconds))) return "時間未設定";
  const h = Math.floor(Number(seconds) / 3600);
  const m = Math.floor((Number(seconds) % 3600) / 60);
  return h > 0 ? `${h}時間${m}分` : `${m}分`;
};

const filtered = () => {
  const q = state.query.trim().toLowerCase();
  const list = state.videos.filter((video) => {
    const tagOk = !state.selectedTag || video.tags.includes(state.selectedTag);
    const text = `${video.title} ${video.tags.join(" ")}`.toLowerCase();
    const yearOk = !state.year || String(video.published_at || "").startsWith(state.year);
    const durationOk = !state.duration || durationMatch(video.duration_sec, state.duration);
    const wordcloudOk = availabilityMatch(video.wordcloud_available, state.wordcloud);
    const timestampOk = availabilityMatch(video.timestamp_available, state.timestamp);
    return tagOk && yearOk && durationOk && wordcloudOk && timestampOk && (!q || text.includes(q));
  });
  return list.sort((a, b) => state.sort === "duration_desc" ? Number(b.duration_sec || 0) - Number(a.duration_sec || 0) : String(b.published_at || "").localeCompare(String(a.published_at || "")));
};

const availabilityMatch = (value, mode) => {
  if (!mode) return true;
  const available = value === true;
  return mode === "yes" ? available : !available;
};

const durationMatch = (seconds, mode) => {
  const value = Number(seconds || 0);
  if (mode === "short") return value > 0 && value < 1800;
  if (mode === "medium") return value >= 1800 && value < 7200;
  if (mode === "long") return value >= 7200;
  return true;
};

const renderTags = () => {
  els.tags.replaceChildren();
  if (!state.tags.length) {
    els.tags.append(el("p", { class: "empty-state", text: "タグはまだありません。" }));
    return;
  }
  for (const tag of state.tags) {
    const button = el("button", { type: "button", text: `${tag.label} ${tag.video_count}`, "aria-pressed": String(state.selectedTag === tag.label), "data-tag": tag.label });
    button.addEventListener("click", () => {
      selectTag(tag.label);
    });
    els.tags.append(button);
  }
};

const quickChipItems = () => {
  const topTags = [...state.tags]
    .sort((a, b) => Number(b.video_count || 0) - Number(a.video_count || 0))
    .slice(0, 4)
    .map((tag) => ({ kind: "tag", label: tag.label, count: tag.video_count }));
  return [{ kind: "latest", label: "最新アーカイブ" }, ...topTags];
};

const renderQuick = () => {
  els.quick.replaceChildren();
  const items = quickChipItems();
  for (const item of items) {
    const isTagActive = item.kind === "tag" && state.selectedTag === item.label;
    const text = item.kind === "tag" ? `${item.label} ${item.count}` : item.label;
    const button = el("button", { type: "button", text, "aria-pressed": String(isTagActive) });
    button.addEventListener("click", async () => {
      if (item.kind === "latest") {
        await showLatest();
      } else {
        selectTag(item.label);
      }
    });
    els.quick.append(button);
  }
};

const renderRecent = () => {
  els.recent.replaceChildren();
  const values = state.recentSearches.slice(0, 6);
  if (!values.length) {
    els.recent.append(el("p", { class: "empty-state", text: "最近検索はありません。" }));
    return;
  }
  for (const value of values) {
    els.recent.append(el("button", { type: "button", text: value, onclick: () => {
      state.query = value;
      els.search.value = value;
      renderList();
    }}));
  }
};

const renderFilterOptions = () => {
  const current = state.selectedTag || "";
  els.filterTag.replaceChildren(el("option", { value: "", text: "すべて" }));
  for (const tag of state.tags) {
    els.filterTag.append(el("option", { value: tag.label, text: `${tag.label} ${tag.video_count}` }));
  }
  els.filterTag.value = current;
};

const syncFilterForm = () => {
  els.filterForm.elements.tag.value = state.selectedTag || "";
  els.filterForm.elements.year.value = state.year;
  els.filterForm.elements.duration.value = state.duration;
  els.filterForm.elements.sort.value = state.sort;
  els.filterForm.elements.wordcloud.value = state.wordcloud;
  els.filterForm.elements.timestamp.value = state.timestamp;
};

const applyFilterForm = () => {
  const data = new FormData(els.filterForm);
  state.selectedTag = String(data.get("tag") || "") || null;
  state.year = String(data.get("year") || "");
  state.duration = String(data.get("duration") || "");
  state.sort = String(data.get("sort") || "published_desc");
  state.wordcloud = String(data.get("wordcloud") || "");
  state.timestamp = String(data.get("timestamp") || "");
  render();
};

const renderList = () => {
  const videos = filtered();
  els.count.textContent = `${videos.length}件`;
  els.list.replaceChildren();
  if (!videos.length) {
    els.list.append(el("p", { class: "empty-state", text: "条件に一致する公開アーカイブはありません。" }));
    return;
  }
  for (const video of videos) {
    const favorite = state.favorites.includes(video.video_id);
    const card = el("article", { class: "video-card" }, [
      el("button", { type: "button", class: "video-main", onclick: () => showDetail(video) }, [
        el("img", { src: video.thumbnail_url || "/assets/placeholder-thumbnail.svg", alt: "" }),
        el("span", {}, [
          el("h3", { text: video.title }),
          el("p", { class: "meta", text: `${fmtDate(video.published_at)} / ${fmtDuration(video.duration_sec)}` }),
          el("span", { class: "tag-row" }, video.tags.map((tag) => el("span", { class: "tag-pill", text: tag })))
        ])
      ]),
      el("button", { type: "button", class: "icon-button", "aria-pressed": String(favorite), "aria-label": favorite ? "お気に入り解除" : "お気に入り追加", text: favorite ? "★" : "☆", onclick: () => toggleFavorite(video.video_id) })
    ]);
    els.list.append(card);
  }
};

const videosByIds = (ids) => ids.map((id) => state.videos.find((video) => video.video_id === id)).filter(Boolean);

const savedButton = (video, mode) => el("button", { type: "button", class: "saved-item", onclick: () => showDetail(video) }, [
  el("span", { class: "saved-title", text: video.title }),
  el("span", { class: "detail-meta", text: `${fmtDate(video.published_at)} / ${fmtDuration(video.duration_sec)}` }),
  el("span", { class: "tag-row" }, (video.tags || []).slice(0, 3).map((tag) => el("span", { class: "tag-pill", text: tag }))),
  mode === "favorite" ? el("span", { class: "saved-marker", text: "お気に入り" }) : el("span", { class: "saved-marker", text: "履歴" })
]);

const renderSaved = () => {
  const favorites = videosByIds(state.favorites);
  const history = videosByIds(state.history);
  els.favorites.replaceChildren(
    ...(favorites.length ? favorites.map((video) => savedButton(video, "favorite")) : [el("p", { class: "empty-state", text: "お気に入りはありません。" })])
  );
  els.history.replaceChildren(
    ...(history.length ? history.map((video) => savedButton(video, "history")) : [el("p", { class: "empty-state", text: "閲覧履歴はありません。" })])
  );
};

const showDetail = async (video) => {
  els.detail.replaceChildren(el("p", { text: "読み込み中" }));
  const detail = await json(video.detail_path);
  rememberHistory(video.video_id);
  const detailVideo = detail.video || {};
  const live = detailVideo.live_details || {};
  const statistics = detailVideo.statistics || {};
  const tags = detailVideo.tags || video.tags || [];
  const terms = (detail.chat_summary?.top_terms || []).map((item) => el("li", { text: `${item.term}: ${fmtNumber(item.score)}` }));
  const timestamps = (detail.timestamps || []).map((item) => {
    const offset = Number(item.offset_sec || 0);
    const href = detailVideo.youtube_url ? `${detailVideo.youtube_url}&t=${offset}s` : null;
    const evidence = (item.evidence_terms || []).join(" / ") || "根拠語なし";
    return el("li", { class: "timestamp-item" }, [
      href
        ? el("a", { href, target: "_blank", rel: "noreferrer", text: `${fmtDuration(offset)} ${item.label}` })
        : el("span", { text: `${fmtDuration(offset)} ${item.label}` }),
      el("p", { class: "detail-meta", text: `${item.source || "source未設定"} / score ${fmtNumber(item.score)} / messages ${fmtNumber(item.message_count)}` }),
      el("p", { class: "detail-meta", text: evidence })
    ]);
  });
  const metadataRows = [
    ["video_id", detailVideo.video_id || video.video_id || "未設定"],
    ["公開日時", fmtDate(detailVideo.published_at || video.published_at)],
    ["予定開始", fmtDate(live.scheduled_start_time || video.scheduled_start_time)],
    ["実開始", fmtDate(live.actual_start_time)],
    ["実終了", fmtDate(live.actual_end_time)],
    ["再生数", fmtNumber(statistics.view_count)],
    ["高評価", fmtNumber(statistics.like_count)]
  ];
  els.detail.replaceChildren(
    el("img", { class: "detail-thumbnail", src: video.thumbnail_url || "/assets/placeholder-thumbnail.svg", alt: "" }),
    el("div", { class: "detail-title-row" }, [
      el("h3", { text: detailVideo.title || video.title || "タイトル未設定" }),
      detailVideo.youtube_url ? el("a", { class: "primary-link", href: detailVideo.youtube_url, rel: "noreferrer", target: "_blank", text: "YouTube" }) : el("span", { class: "empty-state", text: "YouTube URL未設定" })
    ]),
    el("p", { class: "detail-description", text: detailVideo.description || "説明は未設定です。" }),
    el("div", { class: "tag-row detail-tags" }, tags.length ? tags.map((tag) => el("button", { type: "button", class: "tag-pill", text: tag, onclick: () => selectTag(tag) })) : [el("span", { class: "empty-state", text: "タグ未設定" })]),
    el("h3", { text: "metadata" }),
    el("dl", { class: "metadata-grid" }, metadataRows.flatMap(([name, value]) => [
      el("dt", { text: name }),
      el("dd", { text: value })
    ])),
    el("h3", { text: "チャット集計" }),
    el("div", { class: "detail-stats" }, [
      el("div", {}, [el("strong", { text: fmtNumber(detail.chat_summary?.message_count) }), el("span", { text: "messages" })]),
      el("div", {}, [el("strong", { text: fmtNumber(detail.chat_summary?.unique_author_count) }), el("span", { text: "authors" })]),
      el("div", {}, [el("strong", { text: terms.length ? String(terms.length) : "0" }), el("span", { text: "top terms" })])
    ]),
    detail.chat_summary?.wordcloud_url ? el("img", { class: "wordcloud", src: detail.chat_summary.wordcloud_url, alt: "ワードクラウド" }) : el("p", { class: "empty-state", text: "ワードクラウドは未生成です。" }),
    el("ul", { class: "term-list" }, terms.length ? terms : [el("li", { text: "集計語なし" })]),
    el("h3", { text: "タイムスタンプ候補" }),
    el("ul", { class: "timestamp-list" }, timestamps.length ? timestamps : [el("li", { text: "候補なし" })])
  );
};

const toggleFavorite = (videoId) => {
  state.favorites = state.favorites.includes(videoId) ? state.favorites.filter((id) => id !== videoId) : [videoId, ...state.favorites];
  store.set("favorites", state.favorites);
  renderList();
  renderSaved();
};

const rememberHistory = (videoId) => {
  state.history = [videoId, ...state.history.filter((id) => id !== videoId)].slice(0, 20);
  store.set("history", state.history);
  renderSaved();
};

const selectTag = (tag) => {
  state.selectedTag = state.selectedTag === tag ? null : tag;
  state.query = "";
  els.search.value = "";
  render();
};

const clearFilters = ({ includeQuery = false } = {}) => {
  Object.assign(state, { selectedTag: null, year: "", duration: "", sort: "published_desc", wordcloud: "", timestamp: "" });
  if (includeQuery) {
    state.query = "";
    els.search.value = "";
  }
  render();
};

const showLatest = async () => {
  clearFilters({ includeQuery: true });
  if (state.videos[0]) await showDetail(state.videos[0]);
};

const rememberSearch = () => {
  const value = state.query.trim();
  if (!value) return;
  state.recentSearches = [value, ...state.recentSearches.filter((item) => item !== value)].slice(0, 8);
  store.set("recent-searches", state.recentSearches);
  renderRecent();
};

const render = () => {
  renderFilterOptions();
  syncFilterForm();
  renderQuick();
  renderTags();
  renderRecent();
  renderSaved();
  renderList();
};

const init = async () => {
  const manifest = await json("/data/latest-manifest.json");
  const [videos, tags] = await Promise.all([json(manifest.indexes.videos_latest), json(manifest.indexes.tags)]);
  state.videos = videos.items;
  state.tags = tags.items;
  render();
  if (state.videos[0]) await showDetail(state.videos[0]);
};

els.search.addEventListener("input", (event) => {
  state.query = event.target.value;
  renderList();
});
els.search.addEventListener("change", rememberSearch);
els.search.addEventListener("keydown", (event) => {
  if (event.key === "Enter") rememberSearch();
});

els.clearTag.addEventListener("click", () => {
  state.selectedTag = null;
  render();
});

els.clearFilter.addEventListener("click", () => {
  clearFilters();
});

document.querySelector(".bottom-nav").addEventListener("click", async (event) => {
  const action = event.target?.dataset?.action;
  if (action === "filter") {
    syncFilterForm();
    els.filterSheet.showModal();
  }
  if (action === "admin") els.admin.showModal();
  if (action === "clear") {
    clearFilters({ includeQuery: true });
  }
  if (action === "latest") await showLatest();
});

els.filterForm.addEventListener("change", applyFilterForm);
els.filterForm.addEventListener("input", (event) => {
  if (event.target?.name === "year") applyFilterForm();
});

document.querySelector("#adminJobForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  const token = String(data.get("token") || "");
  const csrf = String(data.get("csrf") || "");
  const jobType = String(data.get("jobType") || "static-export");
  const videoId = String(data.get("videoId") || "");
  const body = { idempotency_key: `${jobType}:${videoId || "all"}:${Date.now()}` };
  if (videoId && ["chat-collect", "chat-normalize", "rebuild-artifacts"].includes(jobType)) body.video_id = videoId;
  try {
    const result = await json(`/api/admin/jobs/${jobType}`, {
      method: "POST",
      headers: { "content-type": "application/json", authorization: `Bearer ${token}`, "x-csrf-token": csrf },
      body: JSON.stringify(body)
    });
    document.querySelector("#adminJobId").value = result.job_id || "";
    renderAdminJobResult(result);
    await loadAdminData("jobs");
  } catch (error) {
    els.adminResult.textContent = error.message;
  }
});

const adminHeaders = () => {
  const data = new FormData(document.querySelector("#adminJobForm"));
  return { authorization: `Bearer ${String(data.get("token") || "")}` };
};

const renderAdminJobResult = (result) => {
  els.adminResult.replaceChildren(
    el("strong", { text: result.job_id || "job_id未設定" }),
    el("span", { text: ` / ${result.job_type || "job_type未設定"} / ${result.derived_state || "state未設定"}` }),
    el("span", { text: ` / dry_run ${fmtBoolean(result.dry_run)} / deduplicated ${fmtBoolean(result.deduplicated)}` })
  );
};

const quotaUsageText = (item) => {
  const parts = [
    item.method,
    `${item.units} units`,
    `videos ${item.video_count ?? "-"}`,
    `channel ${item.channel_id ?? "-"}`,
    `job ${item.job_id ?? "-"}`
  ];
  return parts.join(" / ");
};

const jobSummaryText = (item) => [
  item.job_id || "job_id未設定",
  item.job_type || "job_type未設定",
  item.derived_state || "state未設定",
  fmtDate(item.updated_at || item.created_at)
].join(" / ");

const renderJobList = (items) => items.length
  ? el("div", { class: "admin-list" }, items.slice(0, 12).map((item) => {
    const button = el("button", { type: "button", text: jobSummaryText(item) });
    button.addEventListener("click", async () => {
      document.querySelector("#adminJobId").value = item.job_id || "";
      await loadJobDetail(item.job_id);
    });
    return button;
  }))
  : el("p", { class: "empty-state", text: "表示できる job はありません。" });

const renderQuotaUsage = (items) => items.length
  ? el("ul", {}, items.slice(0, 12).map((item) => el("li", { text: quotaUsageText(item) })))
  : el("p", { class: "empty-state", text: "表示できる quota usage はありません。" });

const renderJobDetail = (item) => {
  const events = item.events || [];
  const summaryRows = [
    ["job_id", item.job_id || "未設定"],
    ["job_type", item.job_type || "未設定"],
    ["state", item.derived_state || "未設定"],
    ["created_at", fmtDate(item.created_at)],
    ["updated_at", fmtDate(item.updated_at)],
    ["idempotency_key", item.idempotency_key || "未設定"]
  ];
  return el("section", { class: "admin-detail" }, [
    el("h3", { text: "job詳細" }),
    el("dl", { class: "metadata-grid" }, summaryRows.flatMap(([name, value]) => [
      el("dt", { text: name }),
      el("dd", { text: value })
    ])),
    el("h3", { text: "JobEvent" }),
    events.length
      ? el("ol", { class: "admin-events" }, events.map((event) => el("li", {}, [
        el("strong", { text: event.event_type || "event_type未設定" }),
        el("span", { text: ` / ${fmtDate(event.created_at)}` }),
        el("p", { class: "detail-meta", text: event.message || event.result || event.reason || "message未設定" })
      ])))
      : el("p", { class: "empty-state", text: "JobEvent はありません。" })
  ]);
};

const loadAdminData = async (kind) => {
  try {
    const result = await json(kind === "quota" ? "/api/admin/quota-usage" : "/api/admin/jobs", { headers: adminHeaders() });
    const items = result.items || [];
    els.adminData.replaceChildren(
      el("h3", { text: kind === "quota" ? "quota usage" : "jobs" }),
      kind === "quota" ? renderQuotaUsage(items) : renderJobList(items)
    );
  } catch (error) {
    els.adminData.replaceChildren(el("p", { class: "empty-state", text: error.message }));
  }
};

const loadJobDetail = async (jobId) => {
  if (!jobId) {
    els.adminData.replaceChildren(el("p", { class: "empty-state", text: "job_id を入力してください。" }));
    return;
  }
  try {
    const result = await json(`/api/admin/jobs/${jobId}`, { headers: adminHeaders() });
    els.adminData.replaceChildren(renderJobDetail(result.item || {}));
  } catch (error) {
    els.adminData.replaceChildren(el("p", { class: "empty-state", text: error.message }));
  }
};

document.querySelector("#loadJobsButton").addEventListener("click", () => loadAdminData("jobs"));
document.querySelector("#loadQuotaButton").addEventListener("click", () => loadAdminData("quota"));
document.querySelector("#loadJobDetailButton").addEventListener("click", () => {
  const data = new FormData(document.querySelector("#adminJobForm"));
  loadJobDetail(String(data.get("jobId") || ""));
});

init().catch((error) => {
  els.list.textContent = "公開データを読み込めませんでした。";
  console.error(error);
});
