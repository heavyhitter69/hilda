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
    bindDownloadAnchors: function (selector, path, missingMessage) {
      console.log("Hilda Installer: Binding " + selector + " to " + path);
      var nodes = document.querySelectorAll(selector);
      var self = this;
      nodes.forEach(function (a) {
        self.check(path).then(function(exists) {
            if (exists) {
                // If it exists locally, use the local path
                a.classList.remove("disabled");
                if (a.tagName.toLowerCase() === 'a' && path) {
                    a.setAttribute("href", path);
                }
                a.removeAttribute("title");
            } else {
                // FALLBACK: If missing locally, point to GitHub Releases
                var filename = path.split('/').pop();
                var githubUrl = "https://github.com/heavyhitter69/hilda/releases/latest/download/" + filename;
                
                a.classList.remove("disabled");
                if (a.tagName.toLowerCase() === 'a') {
                    a.setAttribute("href", githubUrl);
                }
                a.removeAttribute("title");
                console.log("Hilda Installer: " + filename + " not found locally, falling back to GitHub.");
            }
        });
      });
    },
    check: function (path) {
      // Check if the file actually exists on the server
      return fetch(path, { method: 'HEAD' })
        .then(function (res) {
          return res.ok;
        })
        .catch(function () {
          return false;
        });
    }
  };
})();
