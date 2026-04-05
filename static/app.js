/**
 * FlightScope - Flight Price Comparison App
 * Tokyo (HND/NRT) departure flight price comparison tool
 */

// --- State ---
const state = {
    selectedDest: null, // { iata, name }
    year: new Date().getFullYear(),
    month: new Date().getMonth() + 1,
    results: null,
    acIndex: -1, // autocomplete active index
};

// --- DOM Elements ---
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const els = {
    input: $("#destination-input"),
    acList: $("#autocomplete-list"),
    monthDisplay: $("#month-display"),
    prevMonth: $("#prev-month"),
    nextMonth: $("#next-month"),
    searchBtn: $("#search-btn"),
    selectedDest: $("#selected-dest"),
    selectedDestText: $("#selected-dest-text"),
    clearDest: $("#clear-dest"),
    loading: $("#loading"),
    results: $("#results"),
    initialState: $("#initial-state"),
    hndBest: $("#hnd-best"),
    nrtBest: $("#nrt-best"),
    recommendation: $("#recommendation"),
    recommendationText: $("#recommendation-text"),
    calendar: $("#calendar"),
    priceChart: $("#price-chart"),
    priceTable: $("#price-table"),
    dataSourceNotice: $("#data-source-notice"),
};

// --- Utilities ---
const DAY_NAMES = ["日", "月", "火", "水", "木", "金", "土"];
const MONTH_NAMES = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"];

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

// --- Month Navigation ---
function updateMonthDisplay() {
    els.monthDisplay.textContent = `${state.year}年${state.month}月`;
}

function changeMonth(delta) {
    state.month += delta;
    if (state.month > 12) {
        state.month = 1;
        state.year++;
    } else if (state.month < 1) {
        state.month = 12;
        state.year--;
    }
    updateMonthDisplay();
    if (state.selectedDest && state.results) {
        performSearch();
    }
}

// --- Autocomplete ---
let acDebounce = null;

async function searchAirports(query) {
    if (query.length < 2) {
        hideAutocomplete();
        return;
    }

    try {
        const res = await fetch(`/api/airports?q=${encodeURIComponent(query)}`);
        const airports = await res.json();
        showAutocomplete(airports);
    } catch (e) {
        console.error("Airport search failed:", e);
    }
}

function showAutocomplete(airports) {
    if (airports.length === 0) {
        hideAutocomplete();
        return;
    }

    els.acList.innerHTML = airports
        .map(
            (a, i) => `
        <div class="ac-item" data-index="${i}" data-iata="${a.iata}" data-name="${a.city_ja || a.city}">
            <span class="iata-code">${a.iata}</span>
            <span class="airport-name">${a.name_ja || a.name}</span>
            <div class="city-country">${a.city_ja || a.city}, ${a.country}</div>
        </div>
    `
        )
        .join("");

    els.acList.classList.remove("hidden");
    state.acIndex = -1;

    // Add click handlers
    els.acList.querySelectorAll(".ac-item").forEach((item) => {
        item.addEventListener("click", () => {
            selectDestination(item.dataset.iata, item.dataset.name);
        });
    });
}

function hideAutocomplete() {
    els.acList.classList.add("hidden");
    state.acIndex = -1;
}

function selectDestination(iata, name) {
    state.selectedDest = { iata, name };
    els.input.value = "";
    els.selectedDestText.textContent = `${name} (${iata})`;
    els.selectedDest.classList.remove("hidden");
    hideAutocomplete();
    els.searchBtn.focus();
}

function clearDestination() {
    state.selectedDest = null;
    els.selectedDest.classList.add("hidden");
    els.input.value = "";
    els.input.focus();
}

// --- Search ---
async function performSearch() {
    if (!state.selectedDest) return;

    els.loading.classList.remove("hidden");
    els.results.classList.add("hidden");
    els.initialState.classList.add("hidden");
    els.dataSourceNotice.classList.add("hidden");

    try {
        const params = new URLSearchParams({
            destination: state.selectedDest.iata,
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
        renderResults(data);
    } catch (e) {
        console.error("Search failed:", e);
        alert("検索に失敗しました。もう一度お試しください。");
    } finally {
        els.loading.classList.add("hidden");
    }
}

// --- Render Results ---
function renderResults(data) {
    const hndPrices = data.origins.HND || [];
    const nrtPrices = data.origins.NRT || [];

    // Build lookup maps by date
    const hndMap = Object.fromEntries(hndPrices.map((p) => [p.date, p]));
    const nrtMap = Object.fromEntries(nrtPrices.map((p) => [p.date, p]));

    // Find cheapest for each origin
    const hndMin = hndPrices.length > 0 ? hndPrices.reduce((a, b) => (a.price < b.price ? a : b)) : null;
    const nrtMin = nrtPrices.length > 0 ? nrtPrices.reduce((a, b) => (a.price < b.price ? a : b)) : null;

    // Render summary cards
    renderSummary(hndMin, nrtMin);

    // Render recommendation
    renderRecommendation(hndMin, nrtMin);

    // Render calendar
    renderCalendar(hndMap, nrtMap, hndMin, nrtMin, data.year, data.month);

    // Render chart
    renderChart(hndMap, nrtMap, data.year, data.month);

    // Render table
    renderTable(hndPrices, nrtPrices);

    // Show data source
    if (data.data_source === "demo") {
        els.dataSourceNotice.textContent = "※ デモデータを表示しています。Amadeus APIキーを設定すると実際の航空券価格が表示されます。";
    } else {
        els.dataSourceNotice.textContent = "※ Amadeus API経由の参考価格です。実際の価格は各航空会社サイトでご確認ください。";
    }
    els.dataSourceNotice.classList.remove("hidden");

    els.results.classList.remove("hidden");
}

function renderSummary(hndMin, nrtMin) {
    if (hndMin) {
        els.hndBest.innerHTML = `
            <div class="text-2xl font-bold text-red-600">${formatPrice(hndMin.price)}</div>
            <div class="text-sm text-gray-500 mt-1">
                最安日: ${formatDate(hndMin.date)} (${getDayOfWeek(hndMin.date)})
                ${hndMin.airline ? `· ${hndMin.airline}` : ""}
                ${hndMin.direct ? '<span class="direct-badge">直行便</span>' : '<span class="transfer-badge">乗継</span>'}
            </div>
        `;
    } else {
        els.hndBest.innerHTML = '<div class="text-gray-400">データなし</div>';
    }

    if (nrtMin) {
        els.nrtBest.innerHTML = `
            <div class="text-2xl font-bold text-blue-600">${formatPrice(nrtMin.price)}</div>
            <div class="text-sm text-gray-500 mt-1">
                最安日: ${formatDate(nrtMin.date)} (${getDayOfWeek(nrtMin.date)})
                ${nrtMin.airline ? `· ${nrtMin.airline}` : ""}
                ${nrtMin.direct ? '<span class="direct-badge">直行便</span>' : '<span class="transfer-badge">乗継</span>'}
            </div>
        `;
    } else {
        els.nrtBest.innerHTML = '<div class="text-gray-400">データなし</div>';
    }
}

function renderRecommendation(hndMin, nrtMin) {
    if (!hndMin || !nrtMin) {
        els.recommendation.classList.add("hidden");
        return;
    }

    const overallMin = hndMin.price <= nrtMin.price ? hndMin : nrtMin;
    const otherMin = hndMin.price <= nrtMin.price ? nrtMin : hndMin;
    const saving = otherMin.price - overallMin.price;
    const originName = overallMin.origin === "HND" ? "羽田" : "成田";
    const otherName = overallMin.origin === "HND" ? "成田" : "羽田";

    els.recommendationText.innerHTML = `
        <div class="font-bold text-lg mb-1">
            おすすめ: ${formatDate(overallMin.date)} (${getDayOfWeek(overallMin.date)}) ${originName}発 — ${formatPrice(overallMin.price)}
        </div>
        <div class="text-sm">
            ${otherName}発より <span class="font-bold text-green-700">${formatPrice(saving)} お得</span>
            ${overallMin.direct ? "｜直行便あり" : ""}
            ${overallMin.airline ? `｜${overallMin.airline}` : ""}
        </div>
    `;
    els.recommendation.classList.remove("hidden");
}

function renderCalendar(hndMap, nrtMap, hndMin, nrtMin, year, month) {
    const cal = els.calendar;
    cal.innerHTML = "";

    // Headers
    DAY_NAMES.forEach((day, i) => {
        const h = document.createElement("div");
        h.className = `cal-header${i === 0 || i === 6 ? " weekend" : ""}`;
        h.textContent = day;
        cal.appendChild(h);
    });

    // First day of month
    const firstDay = new Date(year, month - 1, 1);
    const daysInMonth = new Date(year, month, 0).getDate();
    const startDow = firstDay.getDay();
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    // Find overall min for highlighting
    const allPrices = [...Object.values(hndMap), ...Object.values(nrtMap)].map((p) => p.price);
    const globalMin = allPrices.length > 0 ? Math.min(...allPrices) : 0;
    const globalMax = allPrices.length > 0 ? Math.max(...allPrices) : 0;

    // Empty cells before start
    for (let i = 0; i < startDow; i++) {
        const empty = document.createElement("div");
        empty.className = "cal-cell bg-gray-50";
        cal.appendChild(empty);
    }

    // Day cells
    for (let day = 1; day <= daysInMonth; day++) {
        const dateStr = `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
        const cellDate = new Date(year, month - 1, day);
        const isPast = cellDate < today;

        const hnd = hndMap[dateStr];
        const nrt = nrtMap[dateStr];

        const cell = document.createElement("div");
        let cellClass = "cal-cell bg-white border border-gray-100";

        if (isPast) {
            cellClass += " past";
        } else {
            // Highlight cheapest
            const minHere = Math.min(hnd ? hnd.price : Infinity, nrt ? nrt.price : Infinity);
            if (minHere === globalMin && minHere !== Infinity) {
                cellClass += " cheapest-overall";
            } else if (hndMin && hnd && hnd.price === hndMin.price) {
                cellClass += " cheapest-hnd";
            } else if (nrtMin && nrt && nrt.price === nrtMin.price) {
                cellClass += " cheapest-nrt";
            }
        }

        const isWknd = isWeekend(dateStr);
        const dayNumClass = isWknd ? "text-red-500" : "";

        cell.className = cellClass;
        cell.innerHTML = `
            <div class="day-number ${dayNumClass}">${day}</div>
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
    const chart = els.priceChart;
    chart.innerHTML = "";

    const daysInMonth = new Date(year, month, 0).getDate();
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    // Find max price for scaling
    const allPrices = [...Object.values(hndMap), ...Object.values(nrtMap)].map((p) => p.price);
    const maxPrice = allPrices.length > 0 ? Math.max(...allPrices) : 50000;
    const chartHeight = 220;

    for (let day = 1; day <= daysInMonth; day++) {
        const dateStr = `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
        const cellDate = new Date(year, month - 1, day);
        if (cellDate < today) continue;

        const hnd = hndMap[dateStr];
        const nrt = nrtMap[dateStr];

        const group = document.createElement("div");
        group.className = "chart-bar-group";

        const barsWrapper = document.createElement("div");
        barsWrapper.style.display = "flex";
        barsWrapper.style.gap = "2px";
        barsWrapper.style.alignItems = "flex-end";
        barsWrapper.style.height = chartHeight + "px";

        if (hnd) {
            const bar = document.createElement("div");
            bar.className = "chart-bar hnd";
            bar.style.height = Math.max(4, (hnd.price / maxPrice) * chartHeight) + "px";
            bar.innerHTML = `<div class="chart-tooltip">羽田 ${formatPrice(hnd.price)}</div>`;
            barsWrapper.appendChild(bar);
        }

        if (nrt) {
            const bar = document.createElement("div");
            bar.className = "chart-bar nrt";
            bar.style.height = Math.max(4, (nrt.price / maxPrice) * chartHeight) + "px";
            bar.innerHTML = `<div class="chart-tooltip">成田 ${formatPrice(nrt.price)}</div>`;
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
    const table = els.priceTable;
    table.innerHTML = "";

    // Merge and sort
    const all = [...hndPrices, ...nrtPrices].sort((a, b) => a.price - b.price);

    if (all.length === 0) {
        table.innerHTML = '<tr><td colspan="7" class="text-center py-8 text-gray-400">データがありません</td></tr>';
        return;
    }

    const cheapest = all[0].price;

    all.forEach((flight, i) => {
        const originLabel = flight.origin === "HND" ? "羽田" : "成田";
        const originColor = flight.origin === "HND" ? "text-red-600" : "text-blue-600";
        const diff = flight.price - cheapest;
        const dow = getDayOfWeek(flight.date);
        const isWknd = isWeekend(flight.date);

        const rankClass = i < 3 ? `rank-${i + 1}` : "";

        const tr = document.createElement("tr");
        tr.className = `border-b border-gray-100 ${rankClass}`;
        tr.innerHTML = `
            <td class="py-3 px-4 font-medium">${formatDate(flight.date)}</td>
            <td class="py-3 px-4 ${isWknd ? "text-red-500 font-bold" : ""}">${dow}</td>
            <td class="py-3 px-4 font-bold ${originColor}">${originLabel}</td>
            <td class="py-3 px-4 font-bold">${formatPrice(flight.price)}</td>
            <td class="py-3 px-4">${flight.direct ? '<span class="direct-badge">直行便</span>' : '<span class="transfer-badge">乗継</span>'}</td>
            <td class="py-3 px-4 text-sm">${flight.airline || "-"}</td>
            <td class="py-3 px-4 text-sm ${diff === 0 ? "saving-good" : "saving-bad"}">
                ${diff === 0 ? "最安" : `+${formatPrice(diff)}`}
            </td>
        `;
        table.appendChild(tr);
    });
}

// --- Event Listeners ---
els.input.addEventListener("input", (e) => {
    clearTimeout(acDebounce);
    acDebounce = setTimeout(() => searchAirports(e.target.value), 200);
});

els.input.addEventListener("keydown", (e) => {
    const items = els.acList.querySelectorAll(".ac-item");
    if (items.length === 0) return;

    if (e.key === "ArrowDown") {
        e.preventDefault();
        state.acIndex = Math.min(state.acIndex + 1, items.length - 1);
        items.forEach((item, i) => item.classList.toggle("active", i === state.acIndex));
    } else if (e.key === "ArrowUp") {
        e.preventDefault();
        state.acIndex = Math.max(state.acIndex - 1, 0);
        items.forEach((item, i) => item.classList.toggle("active", i === state.acIndex));
    } else if (e.key === "Enter" && state.acIndex >= 0) {
        e.preventDefault();
        const item = items[state.acIndex];
        selectDestination(item.dataset.iata, item.dataset.name);
    } else if (e.key === "Escape") {
        hideAutocomplete();
    }
});

document.addEventListener("click", (e) => {
    if (!els.acList.contains(e.target) && e.target !== els.input) {
        hideAutocomplete();
    }
});

els.prevMonth.addEventListener("click", () => changeMonth(-1));
els.nextMonth.addEventListener("click", () => changeMonth(1));

els.searchBtn.addEventListener("click", performSearch);

els.clearDest.addEventListener("click", clearDestination);

// Destination shortcuts
$$(".dest-shortcut").forEach((btn) => {
    btn.addEventListener("click", () => {
        selectDestination(btn.dataset.iata, btn.dataset.name);
        performSearch();
    });
});

// Enter key on input triggers search if destination selected
els.input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && state.selectedDest && els.acList.classList.contains("hidden")) {
        performSearch();
    }
});

// --- Init ---
updateMonthDisplay();
