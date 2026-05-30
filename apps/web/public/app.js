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
  quick: document.querySelector("#quickChips"),
  recent: document.querySelector("#recentSearches"),
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
    return tagOk && yearOk && durationOk && (!q || text.includes(q));
  });
  return list.sort((a, b) => state.sort === "duration_desc" ? Number(b.duration_sec || 0) - Number(a.duration_sec || 0) : String(b.published_at || "").localeCompare(String(a.published_at || "")));
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

const showDetail = async (video) => {
  els.detail.replaceChildren(el("p", { text: "読み込み中" }));
  const detail = await json(video.detail_path);
  rememberHistory(video.video_id);
  const terms = (detail.chat_summary?.top_terms || []).map((item) => el("li", { text: `${item.term}: ${item.score}` }));
  const timestamps = (detail.timestamps || []).map((item) => el("li", {}, [
    el("a", { href: `${detail.video.youtube_url}&t=${item.offset_sec}s`, target: "_blank", rel: "noreferrer", text: `${fmtDuration(item.offset_sec)} ${item.label} (${item.source})` })
  ]));
  els.detail.replaceChildren(
    el("img", { src: video.thumbnail_url || "/assets/placeholder-thumbnail.svg", alt: "" }),
    el("h3", { text: detail.video.title }),
    el("p", { class: "detail-meta", text: fmtDate(detail.video.published_at) }),
    el("p", { text: detail.video.description || "説明は未設定です。" }),
    el("p", {}, [el("a", { href: detail.video.youtube_url, rel: "noreferrer", target: "_blank", text: "YouTubeで開く" })]),
    el("h3", { text: "チャット集計" }),
    el("p", { text: `${Number(detail.chat_summary?.message_count || 0).toLocaleString("ja-JP")}件 / 投稿者 ${Number(detail.chat_summary?.unique_author_count || 0).toLocaleString("ja-JP")}人` }),
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
};

const rememberHistory = (videoId) => {
  state.history = [videoId, ...state.history.filter((id) => id !== videoId)].slice(0, 20);
  store.set("history", state.history);
};

const selectTag = (tag) => {
  state.selectedTag = state.selectedTag === tag ? null : tag;
  state.query = "";
  els.search.value = "";
  render();
};

const showLatest = async () => {
  Object.assign(state, { query: "", selectedTag: null, year: "", duration: "", sort: "published_desc" });
  els.search.value = "";
  render();
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
  renderQuick();
  renderTags();
  renderRecent();
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

document.querySelector(".bottom-nav").addEventListener("click", async (event) => {
  const action = event.target?.dataset?.action;
  if (action === "filter") els.filterSheet.showModal();
  if (action === "admin") els.admin.showModal();
  if (action === "clear") {
    Object.assign(state, { query: "", selectedTag: null, year: "", duration: "", sort: "published_desc" });
    els.search.value = "";
    render();
  }
  if (action === "latest") await showLatest();
});

document.querySelector("#filterForm").addEventListener("change", (event) => {
  const data = new FormData(event.currentTarget);
  state.year = String(data.get("year") || "");
  state.duration = String(data.get("duration") || "");
  state.sort = String(data.get("sort") || "published_desc");
  renderList();
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
    els.adminResult.textContent = `queued: ${result.job_id}`;
    await loadAdminData("jobs");
  } catch (error) {
    els.adminResult.textContent = error.message;
  }
});

const adminHeaders = () => {
  const data = new FormData(document.querySelector("#adminJobForm"));
  return { authorization: `Bearer ${String(data.get("token") || "")}` };
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

const loadAdminData = async (kind) => {
  try {
    const result = await json(kind === "quota" ? "/api/admin/quota-usage" : "/api/admin/jobs", { headers: adminHeaders() });
    const items = result.items || [];
    els.adminData.replaceChildren(
      el("h3", { text: kind === "quota" ? "quota usage" : "jobs" }),
      items.length ? el("ul", {}, items.slice(0, 12).map((item) => el("li", { text: kind === "quota" ? quotaUsageText(item) : `${item.job_id} / ${item.job_type} / ${item.derived_state}` }))) : el("p", { class: "empty-state", text: "表示できる項目はありません。" })
    );
  } catch (error) {
    els.adminData.replaceChildren(el("p", { class: "empty-state", text: error.message }));
  }
};

document.querySelector("#loadJobsButton").addEventListener("click", () => loadAdminData("jobs"));
document.querySelector("#loadQuotaButton").addEventListener("click", () => loadAdminData("quota"));

init().catch((error) => {
  els.list.textContent = "公開データを読み込めませんでした。";
  console.error(error);
});
