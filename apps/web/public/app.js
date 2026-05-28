const state = {
  videos: [],
  tags: [],
  selectedTag: null,
  query: ""
};

const els = {
  search: document.querySelector("#searchInput"),
  tags: document.querySelector("#tagFilters"),
  list: document.querySelector("#videoList"),
  count: document.querySelector("#resultCount"),
  detail: document.querySelector("#videoDetail")
};

const json = async (path) => {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`failed to load ${path}: ${response.status}`);
  return response.json();
};

const fmtDate = (value) => new Intl.DateTimeFormat("ja-JP", {
  dateStyle: "medium",
  timeStyle: "short"
}).format(new Date(value));

const fmtDuration = (seconds) => {
  if (!Number.isFinite(seconds)) return "時間未設定";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return h > 0 ? `${h}時間${m}分` : `${m}分`;
};

const filtered = () => {
  const q = state.query.trim().toLowerCase();
  return state.videos.filter((video) => {
    const tagOk = !state.selectedTag || video.tags.includes(state.selectedTag);
    const text = `${video.title} ${video.tags.join(" ")}`.toLowerCase();
    return tagOk && (!q || text.includes(q));
  });
};

const renderTags = () => {
  els.tags.innerHTML = "";
  for (const tag of state.tags) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = `${tag.label} ${tag.video_count}`;
    button.setAttribute("aria-pressed", String(state.selectedTag === tag.label));
    button.addEventListener("click", () => {
      state.selectedTag = state.selectedTag === tag.label ? null : tag.label;
      render();
    });
    els.tags.append(button);
  }
};

const renderList = () => {
  const videos = filtered();
  els.count.textContent = `${videos.length}件`;
  els.list.innerHTML = "";
  for (const video of videos) {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "video-card";
    card.innerHTML = `
      <img src="${video.thumbnail_url || "/assets/placeholder-thumbnail.svg"}" alt="">
      <span>
        <h3>${video.title}</h3>
        <p class="meta">${fmtDate(video.published_at)} / ${fmtDuration(video.duration_sec)}</p>
        <span class="tag-row">${video.tags.map((tag) => `<span class="tag-pill">${tag}</span>`).join("")}</span>
      </span>
    `;
    card.addEventListener("click", () => showDetail(video));
    els.list.append(card);
  }
};

const showDetail = async (video) => {
  els.detail.textContent = "読み込み中";
  const detail = await json(video.detail_path);
  const terms = detail.chat_summary.top_terms.map((item) => `<li>${item.term}: ${item.score}</li>`).join("");
  const timestamps = detail.timestamps.map((item) => `<li>${fmtDuration(item.offset_sec)} ${item.label} (${item.source})</li>`).join("");
  els.detail.innerHTML = `
    <img src="${video.thumbnail_url || "/assets/placeholder-thumbnail.svg"}" alt="">
    <h3>${detail.video.title}</h3>
    <p class="detail-meta">${fmtDate(detail.video.published_at)}</p>
    <p>${detail.video.description || "説明は未設定です。"}</p>
    <p><a href="${detail.video.youtube_url}" rel="noreferrer" target="_blank">YouTubeで開く</a></p>
    <h3>チャット集計</h3>
    <p>${detail.chat_summary.message_count.toLocaleString("ja-JP")}件</p>
    <ul class="term-list">${terms || "<li>集計語なし</li>"}</ul>
    <h3>タイムスタンプ候補</h3>
    <ul class="timestamp-list">${timestamps || "<li>候補なし</li>"}</ul>
  `;
};

const render = () => {
  renderTags();
  renderList();
};

const init = async () => {
  const manifest = await json("/data/latest-manifest.json");
  const [videos, tags] = await Promise.all([
    json(manifest.indexes.videos_latest),
    json(manifest.indexes.tags)
  ]);
  state.videos = videos.items;
  state.tags = tags.items;
  render();
  if (state.videos[0]) await showDetail(state.videos[0]);
};

els.search.addEventListener("input", (event) => {
  state.query = event.target.value;
  renderList();
});

document.querySelector(".bottom-nav").addEventListener("click", async (event) => {
  const action = event.target?.dataset?.action;
  if (action === "clear") {
    state.query = "";
    state.selectedTag = null;
    els.search.value = "";
    render();
  }
  if (action === "latest" && state.videos[0]) await showDetail(state.videos[0]);
  if (action === "random" && state.videos.length > 0) {
    const video = state.videos[Math.floor(Math.random() * state.videos.length)];
    await showDetail(video);
  }
});

init().catch((error) => {
  els.list.textContent = "公開データを読み込めませんでした。";
  console.error(error);
});
