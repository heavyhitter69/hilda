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
    bindDownloadAnchors: function (selector, path) {
      var nodes = document.querySelectorAll(selector);
      // Construct the GitHub Release URL
      var githubPath = path;
      if (!path.startsWith("http")) {
         var filename = path.split('/').pop();
         githubPath = "https://github.com/heavyhitter69/hilda/releases/latest/download/" + filename;
      }

      nodes.forEach(function (a) {
        a.classList.remove("disabled");
        if (a.tagName.toLowerCase() === 'a') {
            a.setAttribute("href", githubPath);
        }
        a.removeAttribute("title");
      });
    },
  };
})();
