// Small helpers: current year in the footer, and the Copy button on the contact page.
(function () {
  document.querySelectorAll("[data-year]").forEach(function (el) {
    el.textContent = String(new Date().getFullYear());
  });

  var btn = document.getElementById("copy-email");
  if (!btn) return;
  btn.addEventListener("click", function () {
    var text = btn.getAttribute("data-copy") || "";
    var done = function () {
      btn.textContent = "Copied";
      setTimeout(function () { btn.textContent = "Copy"; }, 1600);
    };
    var selectIt = function () {
      var el = document.getElementById("email-address");
      if (!el) return;
      var range = document.createRange();
      range.selectNodeContents(el);
      var sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
      btn.textContent = "Selected";
    };
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, selectIt);
      } else {
        selectIt();
      }
    } catch (e) {
      selectIt();
    }
  });
})();
