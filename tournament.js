// Tournament detail page. One template (tournament.html) serves every tournament:
// /tournaments/<id> (vercel.json rewrite) or /tournament.html?id=<id>.
// Helpers come from tournaments.js (window.NXTTournaments), which loads first.
(function () {
  var T = window.NXTTournaments;
  var titleEl = document.getElementById("td-title");
  if (!T || !titleEl) return;

  var m = location.pathname.match(/\/tournaments\/([^/?#]+)\/?$/);
  var id = m ? decodeURIComponent(m[1]) : new URLSearchParams(location.search).get("id") || "";

  function $(x) { return document.getElementById(x); }
  function text(x, v) { $(x).textContent = v; }

  function notFound() {
    titleEl.textContent = "Tournament not found";
    document.title = "Tournament not found · NXT Play Labs";
    var meta = document.createElement("meta");
    meta.name = "robots"; meta.content = "noindex";
    document.head.appendChild(meta);
    $("td-missing").hidden = false;
  }

  fetch("tournaments.json", { cache: "no-cache" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (data) {
      var t = (data.tournaments || []).filter(function (x) { return x && x.id === id; })[0];
      if (!t) return notFound();
      render(t, data);
    })
    .catch(notFound);

  function render(t, data) {
    var esc = T.esc;
    var sportName = {};
    T.sportsFrom(data, [t]).forEach(function (s) { sportName[s.id] = s.name || T.cap(s.id); });
    var allSanc = T.sanctionsFrom(data);
    var sancList = T.sanctionIds(t).map(function (id) { return allSanc[id] || { id: id, name: id }; });
    var sport = sportName[t.sport] || T.cap(t.sport);
    var sancName = sancList.map(function (s) { return s.name; }).join(" + ");
    var start = T.day(t.start), end = T.day(t.end || t.start);
    var dates = T.dateRange(t) + ", " + end.getFullYear();
    var days = Math.round((end - start) / 864e5) + 1;
    var place = [t.city, t.state].filter(Boolean).join(", ") + (t.zip ? " " + t.zip : "");
    var fee = T.feeText(t, " per team") || "Contact the organizer";
    var url = T.safeUrl(t.url);

    document.title = t.name + " · " + sport + " tournament · NXT Play Labs";
    var desc = t.name + ": " + sport + " tournament in " + [t.city, t.state].filter(Boolean).join(", ") + ", " + dates +
      (sancName ? ". " + sancName + " sanctioned" : "") + ".";
    var md = document.querySelector('meta[name="description"]');
    if (md) md.setAttribute("content", desc);

    text("td-kicker", sport + " tournament");
    titleEl.textContent = t.name;
    $("td-tags").innerHTML =
      '<li class="tf-tag tf-sport">' + esc(sport) + "</li>" +
      sancList.map(function (s) { return '<li class="tf-tag tf-sanction">' + esc(s.name) + "</li>"; }).join("") +
      (t.ages || []).map(function (g) { return '<li class="tf-tag">' + esc(g) + "</li>"; }).join("");

    text("td-dates", dates + " · " + days + (days === 1 ? " day" : " days"));
    var mapQ = encodeURIComponent([t.venue, t.city, t.state, t.zip].filter(Boolean).join(", "));
    $("td-location").innerHTML = (t.venue ? "<strong>" + esc(t.venue) + "</strong><br>" : "") +
      (t.address ? esc(t.address) + "<br>" : "") + esc(place) +
      '<br><a class="td-map" href="https://www.google.com/maps/search/?api=1&query=' + mapQ + '" target="_blank" rel="noopener">Open in Maps</a>';
    text("td-cost", fee);
    $("td-sanction").innerHTML = sancList.length ? sancList.map(function (sanc) {
      return '<span class="td-sanc">' + (T.safeUrl(sanc.url) ? '<a href="' + esc(sanc.url) + '" target="_blank" rel="noopener">' + esc(sanc.name) + "</a>" : esc(sanc.name)) +
        (sanc.fullName && sanc.fullName !== sanc.name ? '<span class="td-sub">' + esc(sanc.fullName) + "</span>" : "") + "</span>";
    }).join("") : "Not listed";
    text("td-sport", sport);
    text("td-ages", (t.ages || []).join(", ") || "Not listed");
    if (t.format) text("td-format", t.format); else $("td-format-row").hidden = true;
    if (t.organizer) text("td-organizer", t.organizer); else $("td-organizer-row").hidden = true;

    $("td-actions").innerHTML = (url
      ? '<a class="btn" href="' + esc(url) + '" target="_blank" rel="noopener">Register with the organizer</a>'
      : '<span class="btn secondary td-disabled" aria-disabled="true">Registration opens soon</span>') +
      '<a class="btn secondary" href="tournaments">More tournaments</a>';

    if (t.source && t.source.name) {
      var su = T.safeUrl(t.source.url);
      $("td-source").innerHTML = "Listing from " + (su ? '<a href="' + esc(su) + '" target="_blank" rel="noopener">' + esc(t.source.name) + "</a>" : esc(t.source.name)) +
        ". Check with the organizer for the latest details.";
      $("td-source").hidden = false;
    }

    $("td-board").innerHTML = [
      ["Dates", T.MONTHS[start.getMonth()] + " " + start.getDate() + (days > 1 ? " +" + (days - 1) : "")],
      ["Where", [t.city, t.state].filter(Boolean).join(", ")],
      ["Cost", T.feeText(t) || "TBA"],
      ["Sanction", sancName || "TBA"],
      ["Sport", sport]
    ].map(function (r) { return '<div class="board-row"><dt>' + esc(r[0]) + "</dt><dd>" + esc(r[1]) + "</dd></div>"; }).join("");

    $("td-ended").hidden = end >= T.today();
    $("td-sample").hidden = !data.sample;
    $("td-body").hidden = false;

    // Structured data so search engines can show the event.
    var ld = {
      "@context": "https://schema.org", "@type": "SportsEvent", name: t.name, sport: sport,
      startDate: t.start, endDate: t.end || t.start, eventStatus: "https://schema.org/EventScheduled",
      location: { "@type": "Place", name: t.venue || place, address: { "@type": "PostalAddress",
        streetAddress: t.address || undefined, addressLocality: t.city, addressRegion: t.state, postalCode: t.zip, addressCountry: "US" } },
      organizer: t.organizer ? { "@type": "Organization", name: t.organizer } : undefined,
      offers: typeof t.fee === "number" ? (typeof t.feeMax === "number" && t.feeMax > t.fee
        ? { "@type": "AggregateOffer", lowPrice: t.fee, highPrice: t.feeMax, priceCurrency: "USD", url: url || undefined }
        : { "@type": "Offer", price: t.fee, priceCurrency: "USD", url: url || undefined }) : undefined
    };
    if (!data.sample) {
      var s = document.createElement("script");
      s.type = "application/ld+json"; s.textContent = JSON.stringify(ld);
      document.head.appendChild(s);
    }
  }
})();
