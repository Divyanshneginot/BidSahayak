import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

with open(r'C:\Users\Divyansh\Downloads\index.html', 'r', encoding='utf-8') as f:
    text = f.read()

checks = {
    'demo-shell var(--paper)': ('background:var(--paper)' in text) or ('background: var(--paper)' in text),
    'counts 1+1/6': ('1+1' in text) and ('requirements met' in text),
    'menuTgl in HTML': ('menuTgl' in text),
    'Escape in JS': ('Escape' in text),
    'upload validation': ('25*1024*1024' in text) or ('25 * 1024 * 1024' in text),
    'inline favicon': ('data:image/svg+xml' in text),
    'trace disclosure': ('trace-disclosure' in text),
    'html:not count': text.count('html:not([data-theme="light"])')
}

for k, v in checks.items():
    print(f'{k}: {v}')
