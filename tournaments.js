// Tournament finder. Reads tournaments.json and renders:
//  - the full finder on /tournaments (#tf-list + #tf-filters)
//  - the "On deck" board on the home page ([data-tf-next="N"])
// ZIP search: assets/zip/<first digit>.json maps ZIP -> [lat, lng, city, state]. Shards load only
// when someone searches by ZIP, and venue ZIPs in tournaments.json are looked up the same way.
// Filters live in the URL query (?zip=75201&radius=100&sport=softball…) so a filtered view can be shared.
(function () {
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var MONTHS_LONG = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

  // "2026-11-21" -> local Date (avoids the UTC shift of new Date("2026-11-21")).
  function day(s) {
    var p = String(s || "").split("-");
    return new Date(+p[0], +p[1] - 1, +p[2]);
  }
  function today() {
    var d = new Date();
    return new Date(d.getFullYear(), d.getMonth(), d.getDate());
  }
  function monthKey(d) {
    return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0");
  }
  function dateRange(t) {
    var a = day(t.start), b = day(t.end || t.start);
    if (+a === +b) return MONTHS[a.getMonth()] + " " + a.getDate();
    if (a.getMonth() === b.getMonth()) return MONTHS[a.getMonth()] + " " + a.getDate() + "–" + b.getDate();
    return MONTHS[a.getMonth()] + " " + a.getDate() + " – " + MONTHS[b.getMonth()] + " " + b.getDate();
  }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function safeUrl(u) {
    return /^https?:\/\//i.test(u || "") ? u : "";
  }
  function cap(s) {
    return s ? s.charAt(0).toUpperCase() + s.slice(1) : "";
  }

  // ---------- ZIP lookup ----------
  var shardCache = {};
  function shard(d) {
    if (!shardCache[d]) {
      shardCache[d] = fetch("assets/zip/" + d + ".json")
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
        .catch(function (e) { delete shardCache[d]; throw e; });
    }
    return shardCache[d];
  }
  // Resolves to {lat, lng, city, state} or null if the ZIP isn't known.
  function lookupZip(zip) {
    if (!/^\d{5}$/.test(zip)) return Promise.resolve(null);
    return shard(zip.charAt(0)).then(function (m) {
      var r = m[zip];
      return r ? { lat: r[0], lng: r[1], city: r[2], state: r[3] } : null;
    });
  }
  function miles(a, b) {
    var rad = Math.PI / 180, R = 3958.8;
    var dLat = (b.lat - a.lat) * rad, dLng = (b.lng - a.lng) * rad;
    var h = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(a.lat * rad) * Math.cos(b.lat * rad) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
    return 2 * R * Math.asin(Math.min(1, Math.sqrt(h)));
  }
  // Give every tournament a .geo from its own lat/lng, or from its zip.
  var geoReady = null;
  function ensureEventGeo(items) {
    if (geoReady) return geoReady;
    geoReady = Promise.all(items.map(function (t) {
      if (typeof t.lat === "number" && typeof t.lng === "number") { t.geo = { lat: t.lat, lng: t.lng }; return null; }
      return lookupZip(String(t.zip || "")).then(function (g) { t.geo = g; }, function () { t.geo = null; });
    }));
    return geoReady;
  }

  function sportsFrom(data, items) {
    var list = Array.isArray(data.sports) ? data.sports.filter(function (s) { return s && s.id; }) : [];
    var known = {};
    list.forEach(function (s) { known[s.id] = true; });
    items.forEach(function (t) { if (t.sport && !known[t.sport]) { known[t.sport] = true; list.push({ id: t.sport, name: cap(t.sport) }); } });
    return list;
  }

  function sanctionsFrom(data) {
    var map = {};
    (Array.isArray(data.sanctions) ? data.sanctions : []).forEach(function (s) { if (s && s.id) map[s.id] = s; });
    return map;
  }
  // All sanctioning bodies for a tournament (co-sanctioned events list more than one).
  function sanctionIds(t) {
    var ids = (Array.isArray(t.sanctions) && t.sanctions.length ? t.sanctions : [t.sanction]).filter(Boolean);
    return ids.filter(function (id, i) { return ids.indexOf(id) === i; });
  }
  // "$495" or "$275–$325"; suffix e.g. " / team"
  function feeText(t, suffix) {
    if (typeof t.fee !== "number") return "";
    var f = function (n) { return "$" + n.toLocaleString("en-US"); };
    return (typeof t.feeMax === "number" && t.feeMax > t.fee ? f(t.fee) + "–" + f(t.feeMax) : f(t.fee)) + (suffix || "");
  }
  function detailUrl(t) {
    return "tournaments/" + encodeURIComponent(t.id);
  }

  // Shared with tournament.js (the detail page).
  window.NXTTournaments = {
    day: day, today: today, dateRange: dateRange, esc: esc, safeUrl: safeUrl, cap: cap,
    sportsFrom: sportsFrom, sanctionsFrom: sanctionsFrom, sanctionIds: sanctionIds, feeText: feeText, detailUrl: detailUrl, MONTHS: MONTHS, MONTHS_LONG: MONTHS_LONG
  };

  var list = document.getElementById("tf-list");
  var nextBoard = document.querySelector("[data-tf-next]");
  if (!list && !nextBoard) return;

  function upcoming(data) {
    var now = today();
    return (data.tournaments || [])
      .filter(function (t) { return t && t.start && day(t.end || t.start) >= now; })
      .sort(function (a, b) { return day(a.start) - day(b.start) || String(a.name).localeCompare(b.name); });
  }

  fetch("tournaments.json", { cache: "no-cache" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (data) {
      var items = upcoming(data);
      if (nextBoard) renderNext(items, data);
      if (list) initFinder(items, data);
    })
    .catch(function () {
      if (list) {
        document.getElementById("tf-results-h").textContent = "Couldn't load tournaments.";
        list.innerHTML = "";
      }
    });

  // ---------- home page board ----------
  function renderNext(items, data) {
    var names = {};
    sportsFrom(data, items).forEach(function (s) { names[s.id] = s.name; });
    var n = parseInt(nextBoard.getAttribute("data-tf-next"), 10) || 3;
    var rows = items.slice(0, n).map(function (t) {
      return '<div class="board-row"><dt>' + esc(dateRange(t)) + "</dt><dd><a href=\"" + esc(detailUrl(t)) + "\">" + esc(t.name) + "</a>" +
        '<span class="tf-board-sub">' + esc(t.city) + ", " + esc(t.state) + " · " + esc(names[t.sport] || cap(t.sport)) + "</span></dd></div>";
    });
    if (!rows.length) return; // keep the static "See all tournaments" row
    if (data.sample) rows.push('<div class="board-row"><dt>Note</dt><dd class="plain">Sample listings</dd></div>');
    nextBoard.innerHTML = rows.join("");
  }

  // ---------- finder ----------
  function initFinder(items, data) {
    var form = document.getElementById("tf-filters");
    var sportsBox = document.getElementById("tf-sports");
    var stateSel = document.getElementById("tf-state");
    var monthSel = document.getElementById("tf-month");
    var zipIn = document.getElementById("tf-zip");
    var radiusSel = document.getElementById("tf-radius");
    var zipMsg = document.getElementById("tf-zip-msg");
    var sortSel = document.getElementById("tf-sort");
    var sanctionSel = document.getElementById("tf-sanction");
    var sanctions = sanctionsFrom(data);
    var usedSanctions = {};
    items.forEach(function (t) { sanctionIds(t).forEach(function (id) { usedSanctions[id] = true; }); });
    Object.keys(usedSanctions).sort(function (a, b) {
      return String((sanctions[a] || {}).name || a).localeCompare(String((sanctions[b] || {}).name || b));
    }).forEach(function (id) { sanctionSel.add(new Option((sanctions[id] || {}).name || id.toUpperCase(), id)); });
    var distOpt = sortSel.querySelector('option[value="distance"]');
    var count = document.getElementById("tf-results-h");
    var empty = document.getElementById("tf-empty");
    var notice = document.getElementById("tf-notice");
    if (data.sample) notice.hidden = false;

    // Sports come from tournaments.json, so adding one there adds a button here.
    var sports = sportsFrom(data, items), sportName = {};
    sports.forEach(function (s) {
      sportName[s.id] = s.name || cap(s.id);
      var l = document.createElement("label");
      l.innerHTML = '<input type="radio" name="sport" value="' + esc(s.id) + '"><span>' + esc(sportName[s.id]) + "</span>";
      sportsBox.appendChild(l);
    });
    sportsBox.style.gridTemplateColumns = "repeat(" + (sports.length + 1) + ", minmax(0, 1fr))";

    // Every state is listed; ones with events show a count.
    var perState = {};
    items.forEach(function (t) { if (t.state) perState[t.state] = (perState[t.state] || 0) + 1; });
    Array.prototype.forEach.call(stateSel.options, function (o) {
      if (o.value && perState[o.value]) o.textContent += " (" + perState[o.value] + ")";
    });

    // Months come from the data; a tournament counts for every month it touches.
    var months = {};
    items.forEach(function (t) {
      var d = day(t.start), end = day(t.end || t.start);
      while (d <= end) { months[monthKey(d)] = true; d = new Date(d.getFullYear(), d.getMonth() + 1, 1); }
    });
    Object.keys(months).sort().forEach(function (k) {
      var p = k.split("-");
      monthSel.add(new Option(MONTHS_LONG[+p[1] - 1] + " " + p[0], k));
    });

    // Restore filters from the URL.
    var params = new URLSearchParams(location.search);
    form.q.value = params.get("q") || "";
    zipIn.value = (params.get("zip") || "").replace(/\D/g, "").slice(0, 5);
    var sport = params.get("sport") || "";
    var radios = form.querySelectorAll('input[name="sport"]');
    if (!Array.prototype.some.call(radios, function (r) { return r.value === sport; })) sport = "";
    Array.prototype.forEach.call(radios, function (r) { r.checked = r.value === sport; });
    ["state", "age", "month", "sanction"].forEach(function (k) { setSelect(form[k], params.get(k)); });
    if (params.has("radius")) setSelect(radiusSel, params.get("radius"));
    var sortTouched = params.has("sort");
    setSelect(sortSel, params.get("sort"));

    function setSelect(sel, v) {
      v = v == null ? "" : v;
      if (Array.prototype.some.call(sel.options, function (o) { return o.value === v; })) sel.value = v;
    }

    // origin: null (no ZIP), {lat,lng,city,state}, or a string status ("short" | "loading" | "notfound" | "error")
    var origin = null, zipSeq = 0;
    function setOrigin() {
      var z = zipIn.value.replace(/\D/g, "");
      if (z !== zipIn.value) zipIn.value = z;
      var seq = ++zipSeq;
      if (!z) { origin = null; return Promise.resolve(); }
      if (z.length < 5) { origin = "short"; return Promise.resolve(); }
      origin = "loading";
      return Promise.all([lookupZip(z), ensureEventGeo(items)]).then(function (res) {
        if (seq !== zipSeq) return;
        origin = res[0] || "notfound";
      }, function () {
        if (seq === zipSeq) origin = "error";
      });
    }
    function hasOrigin() { return origin && typeof origin === "object"; }

    function read() {
      return {
        q: form.q.value.trim().toLowerCase(),
        sport: (form.querySelector('input[name="sport"]:checked') || {}).value || "",
        state: form.state.value,
        age: form.age.value,
        month: form.month.value,
        sanction: form.sanction.value,
        radius: parseInt(radiusSel.value, 10) || 0
      };
    }

    function matches(t, f) {
      if (f.sport && t.sport !== f.sport) return false;
      if (f.state && t.state !== f.state) return false;
      if (f.sanction && sanctionIds(t).indexOf(f.sanction) === -1) return false;
      if (f.age && (t.ages || []).indexOf(f.age) === -1) return false;
      if (f.month) {
        var p = f.month.split("-");
        var mStart = new Date(+p[0], +p[1] - 1, 1), mEnd = new Date(+p[0], +p[1], 0);
        if (day(t.start) > mEnd || day(t.end || t.start) < mStart) return false;
      }
      if (f.q) {
        var hay = [t.name, t.city, t.state, t.zip, t.venue, t.organizer, sanctionIds(t).map(function (id) { return (sanctions[id] || {}).name || id; }).join(" ")].join(" ").toLowerCase();
        if (hay.indexOf(f.q) === -1) return false;
      }
      if (hasOrigin() && f.radius) {
        if (t._mi == null || t._mi > f.radius) return false;
      }
      return true;
    }

    function card(t) {
      var a = day(t.start);
      var url = safeUrl(t.url);
      var fee = feeText(t, " / team");
      var tags = '<li class="tf-tag tf-sport">' + esc(sportName[t.sport] || cap(t.sport)) + "</li>" +
        sanctionIds(t).map(function (id) { return '<li class="tf-tag tf-sanction">' + esc((sanctions[id] || {}).name || id) + "</li>"; }).join("") +
        (t.ages || []).map(function (g) { return '<li class="tf-tag">' + esc(g) + "</li>"; }).join("");
      var meta = [t.format, fee, t.organizer ? "Run by " + t.organizer : ""].filter(Boolean).map(esc).join(" · ");
      var dist = hasOrigin() && t._mi != null
        ? '<span class="tf-dist">' + (t._mi < 1 ? "Under 1 mi" : Math.round(t._mi).toLocaleString("en-US") + " mi") + "</span>"
        : "";
      var action = url
        ? '<a class="btn tf-register" href="' + esc(url) + '" target="_blank" rel="noopener">Register<span class="sr-only"> for ' + esc(t.name) + " (opens organizer site)</span></a>"
        : '<span class="tf-soon">Registration opens soon</span>';
      return '<li class="tf-card">' +
        '<div class="tf-date" aria-hidden="true"><span class="tf-mon">' + MONTHS[a.getMonth()] + '</span><span class="tf-day">' + a.getDate() + "</span></div>" +
        '<div class="tf-body">' +
          '<h3 class="tf-name"><a href="' + esc(detailUrl(t)) + '">' + esc(t.name) + "</a></h3>" +
          '<p class="tf-where"><time datetime="' + esc(t.start) + '">' + esc(dateRange(t)) + ", " + a.getFullYear() + "</time> · " +
            esc(t.city) + ", " + esc(t.state) + (t.venue ? " · " + esc(t.venue) : "") + "</p>" +
          '<ul class="tf-tags" aria-label="Sport and age groups">' + tags + "</ul>" +
          (meta ? '<p class="tf-meta">' + meta + "</p>" : "") +
        "</div>" +
        '<div class="tf-action">' + dist + action + "</div>" +
      "</li>";
    }

    function zipStatus(f) {
      zipMsg.classList.remove("bad");
      if (origin === "loading") { zipMsg.textContent = "Looking up ZIP code…"; return; }
      if (origin === "short") { zipMsg.textContent = "Enter all 5 digits."; return; }
      if (origin === "notfound") { zipMsg.textContent = "We couldn't find that ZIP code."; zipMsg.classList.add("bad"); return; }
      if (origin === "error") { zipMsg.textContent = "ZIP search isn't available right now."; zipMsg.classList.add("bad"); return; }
      zipMsg.textContent = hasOrigin() ? "Near " + origin.city + ", " + origin.state : "";
    }

    function render() {
      var f = read();
      items.forEach(function (t) { t._mi = hasOrigin() && t.geo ? miles(origin, t.geo) : null; });

      distOpt.disabled = !hasOrigin();
      if (hasOrigin() && !sortTouched) sortSel.value = "distance";
      if (!hasOrigin() && sortSel.value === "distance") sortSel.value = "date";
      radiusSel.disabled = !hasOrigin() && !zipIn.value;
      zipStatus(f);

      var shown = items.filter(function (t) { return matches(t, f); });
      if (sortSel.value === "distance") {
        shown.sort(function (a, b) {
          var x = a._mi == null ? Infinity : a._mi, y = b._mi == null ? Infinity : b._mi;
          return x - y || day(a.start) - day(b.start);
        });
      }
      list.innerHTML = shown.map(card).join("");
      empty.hidden = shown.length > 0 || items.length === 0;

      var n = shown.length + (shown.length === 1 ? " tournament" : " tournaments");
      if (items.length === 0) count.textContent = "No upcoming tournaments yet. Check back soon.";
      else if (hasOrigin() && f.radius) count.textContent = n + " within " + f.radius + " mi of " + origin.city + ", " + origin.state;
      else if (hasOrigin()) count.textContent = n + " near " + origin.city + ", " + origin.state;
      else count.textContent = n + (shown.length === items.length ? " coming up" : " match");

      var qs = new URLSearchParams();
      if (form.q.value.trim()) qs.set("q", form.q.value.trim());
      if (f.sport) qs.set("sport", f.sport);
      if (zipIn.value) { qs.set("zip", zipIn.value); qs.set("radius", radiusSel.value || "any"); }
      ["state", "age", "month", "sanction"].forEach(function (k) { if (f[k]) qs.set(k, f[k]); });
      if (sortTouched && (zipIn.value || sortSel.value !== "date")) qs.set("sort", sortSel.value);
      var s = qs.toString();
      history.replaceState(null, "", location.pathname + (s ? "?" + s : ""));
    }

    function zipChanged() {
      var p = setOrigin();
      render();
      p.then(render);
    }

    var timer;
    form.addEventListener("input", function (e) {
      if (e.target === form.q) { clearTimeout(timer); timer = setTimeout(render, 120); }
      else if (e.target === zipIn) zipChanged();
    });
    form.addEventListener("change", function (e) {
      if (e.target === zipIn) return;
      render();
    });
    // The sort control sits outside the <form> (form="tf-filters"), so its events don't bubble to it.
    sortSel.addEventListener("change", function () { sortTouched = true; render(); });
    form.addEventListener("submit", function (e) { e.preventDefault(); zipChanged(); });
    form.addEventListener("reset", function () {
      setTimeout(function () { sortTouched = false; zipIn.value = ""; zipChanged(); }, 0);
    });
    if (params.get("radius") === "any") radiusSel.value = "";
    zipChanged();
  }
})();
