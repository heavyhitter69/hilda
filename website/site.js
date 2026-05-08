(function () {
  var INSTALLER_PATH = "downloads/Hilda-Setup.exe";

  window.hildaInstaller = {
    path: INSTALLER_PATH,
    check: function () {
      return fetch(INSTALLER_PATH, { method: "HEAD" }).then(function (r) {
        return r.ok;
      });
    },
    bindDownloadAnchors: function (selector, onMissingTitle) {
      var nodes = document.querySelectorAll(selector);
      window.hildaInstaller.check().then(function (ok) {
        nodes.forEach(function (a) {
          if (!ok) {
            a.classList.add("disabled");
            a.setAttribute("href", "#installer-missing");
            if (onMissingTitle) a.setAttribute("title", onMissingTitle);
          } else {
            a.classList.remove("disabled");
            a.setAttribute("href", INSTALLER_PATH);
            a.removeAttribute("title");
          }
        });
      });
    },
  };
})();
