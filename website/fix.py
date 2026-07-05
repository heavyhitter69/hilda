import re
import os

pages = [
    'src/pages/Home.tsx',
    'src/pages/About.tsx',
    'src/pages/Privacy.tsx',
    'src/pages/Terms.tsx',
    'src/components/Header.tsx',
    'src/components/Footer.tsx'
]

def repl(file_path):
    if not os.path.exists(file_path):
        return
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Text colors
    content = re.sub(r"'#fff'", "'var(--text)'", content)
    content = re.sub(r'"#fff"', '"var(--text)"', content)
    
    # RGBA replacements
    content = content.replace("rgba(255, 255, 255, 0.95)", "var(--bg-elevated)")
    content = content.replace("rgba(255,255,255,0.1)", "var(--line)")
    content = content.replace("rgba(255, 255, 255, 0.1)", "var(--line)")
    content = content.replace("rgba(255,255,255,0.05)", "var(--line-strong)")
    content = content.replace("rgba(255,255,255,0.08)", "var(--line)")
    content = content.replace("rgba(255,255,255,0.03)", "var(--accent-subtle)")
    content = content.replace("rgba(255,255,255,0.02)", "var(--accent-subtle)")
    content = content.replace("rgba(255,255,255,0.8)", "var(--text)")
    content = content.replace("rgba(255,255,255,0.2)", "var(--line-strong)")
    content = content.replace("rgba(255, 255, 255, 0.05)", "var(--line-strong)")
    
    # Background and dark alpha
    content = content.replace("rgba(0,0,0,0.4)", "var(--bg-card)")
    content = content.replace("rgba(0, 0, 0, 0.5)", "var(--bg-elevated)")
    content = content.replace("rgba(0, 0, 0, 0.1)", "var(--line)")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

for p in pages:
    repl(p)

print('Replaced inline styles')
