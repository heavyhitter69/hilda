(function () {
  function detectOS() {
    var userAgent = window.navigator.userAgent,
        platform = window.navigator.platform,
        macosPlatforms = ['Macintosh', 'MacIntel', 'MacPPC', 'Mac68K'],
        windowsPlatforms = ['Win32', 'Win64', 'Windows', 'WinCE'],
        os = null;

    if (macosPlatforms.indexOf(platform) !== -1 || userAgent.indexOf('Mac') !== -1) {
      os = 'Mac';
    } else if (windowsPlatforms.indexOf(platform) !== -1 || userAgent.indexOf('Win') !== -1) {
      os = 'Windows';
    } else if (!os && /Linux/.test(platform)) {
      os = 'Linux';
    }

    return os;
  }

  window.hildaInstaller = {
    detectOS: detectOS,
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
