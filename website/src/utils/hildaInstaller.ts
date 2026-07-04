export function detectOS(): 'Mac' | 'Windows' | 'Linux' | null {
  const userAgent = window.navigator.userAgent;
  // @ts-ignore - platform is deprecated but still works for this logic
  const platform = window.navigator.platform;
  const macosPlatforms = ['Macintosh', 'MacIntel', 'MacPPC', 'Mac68K'];
  const windowsPlatforms = ['Win32', 'Win64', 'Windows', 'WinCE'];
  let os: 'Mac' | 'Windows' | 'Linux' | null = null;

  if (macosPlatforms.indexOf(platform) !== -1 || userAgent.indexOf('Mac') !== -1) {
    os = 'Mac';
  } else if (windowsPlatforms.indexOf(platform) !== -1 || userAgent.indexOf('Win') !== -1) {
    os = 'Windows';
  } else if (!os && /Linux/.test(platform)) {
    os = 'Linux';
  }

  return os;
}

export async function checkFileExists(path: string): Promise<boolean> {
  try {
    const res = await fetch(path, { method: 'HEAD' });
    return res.ok;
  } catch (e) {
    return false;
  }
}

export async function getDownloadPathAndMessage(
  basePath: string
): Promise<{ path: string; isFallback: boolean }> {
  const exists = await checkFileExists(basePath);
  if (exists) {
    return { path: basePath, isFallback: false };
  } else {
    const filename = basePath.split('/').pop();
    const githubUrl = `https://github.com/heavyhitter69/hilda/releases/latest/download/${filename}`;
    return { path: githubUrl, isFallback: true };
  }
}
