/**
 * FlightScope - Destination Page Logic
 * Handles price display for /destinations/:IATA
 */

// --- State ---
const state = {
    destCode: null,
    destInfo: null,
    year: new Date().getFullYear(),
    month: new Date().getMonth() + 1,
    results: null,
};

// --- Utilities ---
const DAY_NAMES = ["日", "月", "火", "水", "木", "金", "土"];

function formatPrice(price) {
    return "¥" + price.toLocaleString("ja-JP");
}

function formatDate(dateStr) {
    const d = new Date(dateStr);
    return `${d.getMonth() + 1}/${d.getDate()}`;
}

function getDayOfWeek(dateStr) {
    return DAY_NAMES[new Date(dateStr).getDay()];
}

function isWeekend(dateStr) {
    const dow = new Date(dateStr).getDay();
    return dow === 0 || dow === 6;
}

function buildSearchUrl(flight) {
    // Build a Google Flights search URL as fallback
    const d = new Date(flight.date);
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    const dd = String(d.getDate()).padStart(2, "0");
    return `https://www.google.com/travel/flights?q=flights+from+${flight.origin}+to+${flight.destination}+on+${yyyy}-${mm}-${dd}`;
}

// --- Init: extract IATA from URL ---
function init() {
    const path = window.location.pathname;
    const match = path.match(/\/destinations\/([A-Z]{3})/i);
    if (!match) {
        window.location.href = "/";
        return;
    }
    state.destCode = match[1].toUpperCase();
    updateMonthDisplay();
    loadDestInfo();
    performSearch();
    setupHeaderSearch();
}

async function loadDestInfo() {
    try {
        const res = await fetch(`/api/airports?q=${state.destCode}`);
        const airports = await res.json();
        state.destInfo = airports.find(a => a.iata === state.destCode) || {
            iata: state.destCode, city_ja: state.destCode, name_ja: "", flag: "✈", country: ""
        };
    } catch {
        state.destInfo = { iata: state.destCode, city_ja: state.destCode, name_ja: "", flag: "✈", country: "" };
    }
    updateDestHeader();
}

function updateDestHeader() {
    const d = state.destInfo;
    document.getElementById("dest-flag").textContent = d.flag || "✈";
    document.getElementById("dest-title").textContent = `東京 → ${d.city_ja || d.city || d.iata}`;
    document.getElementById("dest-subtitle").textContent =
        `${d.name_ja || d.name || ""} (${d.iata}) · ${d.country || ""}`;
    document.getElementById("breadcrumb-dest").textContent = d.city_ja || d.city || d.iata;
    document.title = `東京→${d.city_ja || d.iata} フライト価格比較 | FlightScope`;
}

// --- Month Navigation ---
function updateMonthDisplay() {
    document.getElementById("month-display").textContent = `${state.year}年${state.month}月`;
}

function changeMonth(delta) {
    state.month += delta;
    if (state.month > 12) { state.month = 1; state.year++; }
    else if (state.month < 1) { state.month = 12; state.year--; }
    updateMonthDisplay();
    performSearch();
}

document.getElementById("prev-month").addEventListener("click", () => changeMonth(-1));
document.getElementById("next-month").addEventListener("click", () => changeMonth(1));

// --- Search ---
async function performSearch() {
    const loading = document.getElementById("loading");
    const results = document.getElementById("results");
    const notice = document.getElementById("data-source-notice");

    loading.classList.remove("hidden");
    results.classList.add("hidden");
    notice.classList.add("hidden");

    try {
        const params = new URLSearchParams({
            destination: state.destCode,
            year: state.year,
            month: state.month,
        });
        const res = await fetch(`/api/search?${params}`);
        const data = await res.json();

        if (data.error) {
            alert(data.error);
            return;
        }

        state.results = data;
        if (data.destination_info) state.destInfo = data.destination_info;
        updateDestHeader();
        renderResults(data);
    } catch (e) {
        console.error("Search failed:", e);
        alert("検索に失敗しました。もう一度お試しください。");
    } finally {
        loading.classList.add("hidden");
    }
}

// --- Render ---
function renderResults(data) {
    const hndPrices = data.origins.HND || [];
    const nrtPrices = data.origins.NRT || [];

    const hndMap = Object.fromEntries(hndPrices.map(p => [p.date, p]));
    const nrtMap = Object.fromEntries(nrtPrices.map(p => [p.date, p]));

    const hndMin = hndPrices.length > 0 ? hndPrices.reduce((a, b) => a.price < b.price ? a : b) : null;
    const nrtMin = nrtPrices.length > 0 ? nrtPrices.reduce((a, b) => a.price < b.price ? a : b) : null;

    renderExternalLinks(data.destination, data.year, data.month);
    renderSummary(hndMin, nrtMin);
    renderRecommendation(hndMin, nrtMin);
    renderCalendar(hndMap, nrtMap, hndMin, nrtMin, data.year, data.month);
    renderChart(hndMap, nrtMap, data.year, data.month);
    renderTable(hndPrices, nrtPrices);

    const notice = document.getElementById("data-source-notice");
    if (data.data_source === "demo") {
        notice.textContent = "※ デモデータを表示中。TRAVELPAYOUTS_TOKEN を設定すると実際の航空券価格が表示されます。";
    } else {
        notice.textContent = "※ Aviasales/Travelpayouts API経由の参考価格です。実際の価格は各航空会社サイトでご確認ください。";
    }
    notice.classList.remove("hidden");
    document.getElementById("results").classList.remove("hidden");
}

function renderExternalLinks(destination, year, month) {
    const container = document.getElementById("external-search-links");
    if (!container) return;

    const mm = String(month).padStart(2, "0");
    const ym = `${year}${mm}`;

    // Build search URLs for various sites
    const links = [
        {
            name: "Google Flights",
            icon: "🔍",
            hnd: `https://www.google.com/travel/flights?q=flights+from+HND+to+${destination}+on+${year}-${mm}`,
            nrt: `https://www.google.com/travel/flights?q=flights+from+NRT+to+${destination}+on+${year}-${mm}`,
        },
        {
            name: "Skyscanner",
            icon: "🛫",
            hnd: `https://www.skyscanner.jp/transport/flights/hnd/${destination.toLowerCase()}/${year}${mm}/`,
            nrt: `https://www.skyscanner.jp/transport/flights/nrt/${destination.toLowerCase()}/${year}${mm}/`,
        },
        {
            name: "Aviasales",
            icon: "✈",
            hnd: `https://www.aviasales.com/search/HND01${mm}${destination}1`,
            nrt: `https://www.aviasales.com/search/NRT01${mm}${destination}1`,
        },
    ];

    container.innerHTML = links.map(l => `
        <div class="flex flex-col gap-1">
            <span class="text-xs text-gray-500 font-medium">${l.icon} ${l.name}</span>
            <div class="flex gap-2">
                <a href="${l.hnd}" target="_blank" rel="noopener"
                   class="px-3 py-1.5 text-sm bg-red-50 text-red-700 rounded-lg hover:bg-red-100 transition font-medium">
                    羽田発
                </a>
                <a href="${l.nrt}" target="_blank" rel="noopener"
                   class="px-3 py-1.5 text-sm bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition font-medium">
                    成田発
                </a>
            </div>
        </div>
    `).join("");
}

function renderSummary(hndMin, nrtMin) {
    const hndEl = document.getElementById("hnd-best");
    const nrtEl = document.getElementById("nrt-best");

    if (hndMin) {
        hndEl.innerHTML = `
            <div class="text-2xl font-bold text-red-600">${formatPrice(hndMin.price)}</div>
            <div class="text-sm text-gray-500 mt-1">
                最安日: ${formatDate(hndMin.date)} (${getDayOfWeek(hndMin.date)})
                ${hndMin.airline ? `· ${hndMin.airline}` : ""}
                ${hndMin.direct ? '<span class="direct-badge">直行便</span>' : `<span class="transfer-badge">乗継${hndMin.stopovers ? "×" + hndMin.stopovers : ""}</span>`}
            </div>
            ${hndMin.departure_time ? `<div class="text-xs text-gray-400 mt-1">${hndMin.departure_time}発 · 約${hndMin.duration_hours}時間</div>` : ""}
        `;
    } else {
        hndEl.innerHTML = '<div class="text-gray-400">データなし</div>';
    }

    if (nrtMin) {
        nrtEl.innerHTML = `
            <div class="text-2xl font-bold text-blue-600">${formatPrice(nrtMin.price)}</div>
            <div class="text-sm text-gray-500 mt-1">
                最安日: ${formatDate(nrtMin.date)} (${getDayOfWeek(nrtMin.date)})
                ${nrtMin.airline ? `· ${nrtMin.airline}` : ""}
                ${nrtMin.direct ? '<span class="direct-badge">直行便</span>' : `<span class="transfer-badge">乗継${nrtMin.stopovers ? "×" + nrtMin.stopovers : ""}</span>`}
            </div>
            ${nrtMin.departure_time ? `<div class="text-xs text-gray-400 mt-1">${nrtMin.departure_time}発 · 約${nrtMin.duration_hours}時間</div>` : ""}
        `;
    } else {
        nrtEl.innerHTML = '<div class="text-gray-400">データなし</div>';
    }
}

function renderRecommendation(hndMin, nrtMin) {
    const el = document.getElementById("recommendation");
    const textEl = document.getElementById("recommendation-text");

    if (!hndMin || !nrtMin) { el.classList.add("hidden"); return; }

    const best = hndMin.price <= nrtMin.price ? hndMin : nrtMin;
    const other = hndMin.price <= nrtMin.price ? nrtMin : hndMin;
    const saving = other.price - best.price;
    const bestName = best.origin === "HND" ? "羽田" : "成田";
    const otherName = best.origin === "HND" ? "成田" : "羽田";

    textEl.innerHTML = `
        <div class="font-bold text-lg mb-1">
            おすすめ: ${formatDate(best.date)} (${getDayOfWeek(best.date)}) ${bestName}発 — ${formatPrice(best.price)}
        </div>
        <div class="text-sm">
            ${otherName}発より <span class="font-bold text-green-700">${formatPrice(saving)} お得</span>
            ${best.direct ? "｜直行便あり" : ""}
            ${best.airline ? `｜${best.airline}` : ""}
        </div>
    `;
    el.classList.remove("hidden");
}

function renderCalendar(hndMap, nrtMap, hndMin, nrtMin, year, month) {
    const cal = document.getElementById("calendar");
    cal.innerHTML = "";

    DAY_NAMES.forEach((day, i) => {
        const h = document.createElement("div");
        h.className = `cal-header${i === 0 || i === 6 ? " weekend" : ""}`;
        h.textContent = day;
        cal.appendChild(h);
    });

    const firstDay = new Date(year, month - 1, 1);
    const daysInMonth = new Date(year, month, 0).getDate();
    const startDow = firstDay.getDay();
    const today = new Date(); today.setHours(0, 0, 0, 0);

    const allPrices = [...Object.values(hndMap), ...Object.values(nrtMap)].map(p => p.price);
    const globalMin = allPrices.length > 0 ? Math.min(...allPrices) : 0;

    for (let i = 0; i < startDow; i++) {
        const empty = document.createElement("div");
        empty.className = "cal-cell bg-gray-50";
        cal.appendChild(empty);
    }

    for (let day = 1; day <= daysInMonth; day++) {
        const dateStr = `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
        const cellDate = new Date(year, month - 1, day);
        const isPast = cellDate < today;
        const hnd = hndMap[dateStr];
        const nrt = nrtMap[dateStr];

        let cellClass = "cal-cell bg-white border border-gray-100";
        if (isPast) {
            cellClass += " past";
        } else {
            const minHere = Math.min(hnd ? hnd.price : Infinity, nrt ? nrt.price : Infinity);
            if (minHere === globalMin && minHere !== Infinity) cellClass += " cheapest-overall";
            else if (hndMin && hnd && hnd.price === hndMin.price) cellClass += " cheapest-hnd";
            else if (nrtMin && nrt && nrt.price === nrtMin.price) cellClass += " cheapest-nrt";
        }

        const wknd = isWeekend(dateStr);
        const cell = document.createElement("div");
        cell.className = cellClass;
        cell.innerHTML = `
            <div class="day-number ${wknd ? "text-red-500" : ""}">${day}</div>
            ${hnd ? `<div class="price-hnd">H ${formatPrice(hnd.price)}</div>` : ""}
            ${nrt ? `<div class="price-nrt">N ${formatPrice(nrt.price)}</div>` : ""}
            ${hnd && nrt ? `<div class="airline-tag">${getCheaperIndicator(hnd.price, nrt.price)}</div>` : ""}
        `;
        cal.appendChild(cell);
    }
}

function getCheaperIndicator(hndPrice, nrtPrice) {
    const diff = hndPrice - nrtPrice;
    if (Math.abs(diff) < 1000) return "≒同額";
    if (diff > 0) return `N ${formatPrice(Math.abs(diff))}安`;
    return `H ${formatPrice(Math.abs(diff))}安`;
}

function renderChart(hndMap, nrtMap, year, month) {
    const chart = document.getElementById("price-chart");
    chart.innerHTML = "";
    const daysInMonth = new Date(year, month, 0).getDate();
    const today = new Date(); today.setHours(0, 0, 0, 0);

    const allPrices = [...Object.values(hndMap), ...Object.values(nrtMap)].map(p => p.price);
    const maxPrice = allPrices.length > 0 ? Math.max(...allPrices) : 50000;
    const chartHeight = 220;

    for (let day = 1; day <= daysInMonth; day++) {
        const dateStr = `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
        if (new Date(year, month - 1, day) < today) continue;

        const hnd = hndMap[dateStr];
        const nrt = nrtMap[dateStr];
        const group = document.createElement("div");
        group.className = "chart-bar-group";

        const barsWrapper = document.createElement("div");
        barsWrapper.style.cssText = `display:flex;gap:2px;align-items:flex-end;height:${chartHeight}px`;

        if (hnd) {
            const bar = document.createElement("div");
            bar.className = "chart-bar hnd";
            bar.style.height = Math.max(4, (hnd.price / maxPrice) * chartHeight) + "px";
            bar.innerHTML = `<div class="chart-tooltip">羽田 ${formatPrice(hnd.price)}${hnd.airline ? " · " + hnd.airline : ""}</div>`;
            barsWrapper.appendChild(bar);
        }
        if (nrt) {
            const bar = document.createElement("div");
            bar.className = "chart-bar nrt";
            bar.style.height = Math.max(4, (nrt.price / maxPrice) * chartHeight) + "px";
            bar.innerHTML = `<div class="chart-tooltip">成田 ${formatPrice(nrt.price)}${nrt.airline ? " · " + nrt.airline : ""}</div>`;
            barsWrapper.appendChild(bar);
        }

        group.appendChild(barsWrapper);
        const label = document.createElement("div");
        label.className = "chart-date-label";
        label.textContent = `${day}`;
        if (isWeekend(dateStr)) label.style.color = "#ef4444";
        group.appendChild(label);
        chart.appendChild(group);
    }
}

function renderTable(hndPrices, nrtPrices) {
    const table = document.getElementById("price-table");
    table.innerHTML = "";

    const all = [...hndPrices, ...nrtPrices].sort((a, b) => a.price - b.price);
    if (all.length === 0) {
        table.innerHTML = '<tr><td colspan="10" class="text-center py-8 text-gray-400">データがありません</td></tr>';
        return;
    }

    const cheapest = all[0].price;
    all.forEach((f, i) => {
        const originLabel = f.origin === "HND" ? "羽田" : "成田";
        const originColor = f.origin === "HND" ? "text-red-600" : "text-blue-600";
        const diff = f.price - cheapest;
        const dow = getDayOfWeek(f.date);
        const wknd = isWeekend(f.date);
        const rankClass = i < 3 ? `rank-${i + 1}` : "";

        const tr = document.createElement("tr");
        tr.className = `border-b border-gray-100 ${rankClass}`;
        tr.innerHTML = `
            <td class="py-3 px-3 font-medium">${formatDate(f.date)}</td>
            <td class="py-3 px-3 ${wknd ? "text-red-500 font-bold" : ""}">${dow}</td>
            <td class="py-3 px-3 font-bold ${originColor}">${originLabel}</td>
            <td class="py-3 px-3 font-bold">${formatPrice(f.price)}</td>
            <td class="py-3 px-3">${f.direct ? '<span class="direct-badge">直行便</span>' : `<span class="transfer-badge">乗継${f.stopovers ? "×" + f.stopovers : ""}</span>`}</td>
            <td class="py-3 px-3 text-sm">${f.airline || "-"}</td>
            <td class="py-3 px-3 text-sm">${f.departure_time || "-"}</td>
            <td class="py-3 px-3 text-sm">${f.duration_hours ? f.duration_hours + "h" : "-"}</td>
            <td class="py-3 px-3 text-sm ${diff === 0 ? "saving-good" : "saving-bad"}">
                ${diff === 0 ? "最安" : `+${formatPrice(diff)}`}
            </td>
            <td class="py-3 px-3"><a href="${f.deep_link || buildSearchUrl(f)}" target="_blank" rel="noopener" class="inline-block px-3 py-1 bg-blue-600 text-white text-xs rounded-full hover:bg-blue-700 transition">検索 →</a></td>
        `;
        table.appendChild(tr);
    });
}

// --- Header Search (on destination page) ---
function setupHeaderSearch() {
    const input = document.getElementById("header-search");
    const acList = document.getElementById("header-ac-list");
    if (!input) return;

    let debounce = null;
    input.addEventListener("input", (e) => {
        clearTimeout(debounce);
        debounce = setTimeout(async () => {
            const q = e.target.value.trim();
            if (q.length < 2) { acList.classList.add("hidden"); return; }
            const res = await fetch(`/api/airports?q=${encodeURIComponent(q)}`);
            const airports = await res.json();
            if (airports.length === 0) { acList.classList.add("hidden"); return; }
            acList.innerHTML = airports.map(a => `
                <a href="/destinations/${a.iata}" class="block px-4 py-3 border-b border-gray-50 hover:bg-blue-50 text-gray-800">
                    <span class="font-bold text-blue-600">${a.iata}</span>
                    <span class="ml-2">${a.city_ja || a.city}</span>
                </a>
            `).join("");
            acList.classList.remove("hidden");
        }, 200);
    });

    document.addEventListener("click", (e) => {
        if (!acList.contains(e.target) && e.target !== input) acList.classList.add("hidden");
    });
}

// --- Go ---
init();
