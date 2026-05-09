(function () {
  window.hildaInstaller = {
    check: function (path) {
      return fetch(path, { method: "HEAD" }).then(function (r) {
        return r.ok;
      }).catch(function() { return false; });
    },
    bindDownloadAnchors: function (selector, path, onMissingTitle) {
      var nodes = document.querySelectorAll(selector);
      window.hildaInstaller.check(path).then(function (ok) {
        nodes.forEach(function (a) {
          if (!ok) {
            a.classList.add("disabled");
            if (a.tagName.toLowerCase() === 'a') {
                a.setAttribute("href", "#installer-missing");
            }
            if (onMissingTitle) a.setAttribute("title", onMissingTitle);
          } else {
            a.classList.remove("disabled");
            if (a.tagName.toLowerCase() === 'a') {
                a.setAttribute("href", path);
            }
            a.removeAttribute("title");
          }
        });
      });
    },
  };
})();
