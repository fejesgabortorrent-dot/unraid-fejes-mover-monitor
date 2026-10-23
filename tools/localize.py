"""Compile trusted UI literals into three self-contained PHP page branches.

Only source templates are translated: filenames, logs and runtime script contents
never pass through replacement. Runtime language selection is an allowlisted cookie.
"""
from pathlib import Path
import base64
import json
import re

ROOT = Path(__file__).resolve().parents[1]

def compile_page(source):
    # The verified .97 owner baseline is stored as self-contained trilingual
    # PHP source. Preserve it verbatim; do not compile its branches again.
    if "$fmCookie=$_COOKIE['fejes_mover_lang']" in source:
        return source
    source=source.replace('FM_ICON_DATA_URI', 'data:image/svg+xml;base64,'+base64.b64encode((ROOT/'icon.svg').read_bytes()).decode('ascii'))
    catalog = json.loads((ROOT / 'src/translations.json').read_text(encoding='utf-8'))
    for key, values in catalog.items():
        if set(values) != {'en', 'de'} or any(not isinstance(v, str) or any(c in v for c in "\"'\\$<>\r\n") for v in values.values()):
            raise ValueError(f'Unsafe or incomplete source-literal translation: {key}')
    header, body = source.split('---\n', 1)
    title_match=re.search(r'^Title="([^"]+)"',header,re.M)
    source_title=title_match[1] if title_match else ''
    # Unraid menu metadata is static; neutral English names work in every locale.
    header = header.replace('Mover figyelő', 'Mover Monitor').replace('Mover beállítások', 'Mover Settings')
    selector = '''<label style="display:inline-block;margin:10px 12px;font-size:14px"><span aria-hidden="true" style="display:inline-block;width:26px;margin-right:7px;vertical-align:middle">FLAG_IMAGE</span><select aria-label="Language / Nyelv / Sprache" onchange="document.cookie=\x27fejes_mover_lang=\x27+this.value+\x27; Path=/; Max-Age=31536000; SameSite=Lax\x27;location.assign(location.pathname)"><option value="hu" HU_SELECTED>🇭🇺 Magyar</option><option value="en" EN_SELECTED>🇺🇸 English (US)</option><option value="de" DE_SELECTED>🇩🇪 Deutsch</option></select></label>'''
    prefix = '''<?php
$fmCookie=$_COOKIE['fejes_mover_lang']??'hu';
$fmLang=is_string($fmCookie)&&in_array($fmCookie,['hu','en','de'],true)?$fmCookie:'hu';
$fmLanguageSelector=SELECTOR;
$fmLanguageSelector=str_replace(['HU_SELECTED','EN_SELECTED','DE_SELECTED'],[$fmLang==='hu'?'selected':'',$fmLang==='en'?'selected':'',$fmLang==='de'?'selected':''],$fmLanguageSelector);
'''.replace('SELECTOR;', json.dumps(selector, ensure_ascii=False).replace('\\/', '/')+';')
    # JSON double-quoted text is a PHP double-quoted literal; selector has no $.
    # Inline SVG stays visible on Windows even if emoji flags are unsupported.
    svg = lambda body: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 190 100" width="26" height="16">'+body+'</svg>'
    flags = {
        'hu': svg('<path fill="#ce2939" d="M0 0h190v34H0z"/><path fill="#fff" d="M0 34h190v33H0z"/><path fill="#477050" d="M0 67h190v33H0z"/>'),
        'de': svg('<path fill="#000" d="M0 0h190v34H0z"/><path fill="#d00" d="M0 34h190v33H0z"/><path fill="#ffce00" d="M0 67h190v33H0z"/>'),
    }
    stripes = ''.join(f'<rect y="{i*100/13:.3f}" width="190" height="{100/13+0.01:.3f}" fill="{"#b22234" if i%2==0 else "#fff"}"/>' for i in range(13))
    import math
    stars = ''
    for row in range(9):
        for col in range(6 if row%2==0 else 5):
            x = (col+0.5 if row%2==0 else col+1)*76/6
            y = (row+1)*53.85/10
            points = ' '.join(f'{x+(2.7 if k%2==0 else 1.05)*math.cos(-math.pi/2+k*math.pi/5):.2f},{y+(2.7 if k%2==0 else 1.05)*math.sin(-math.pi/2+k*math.pi/5):.2f}' for k in range(10))
            stars += f'<polygon fill="#fff" points="{points}"/>'
    flags['en'] = svg(stripes+'<rect width="76" height="53.85" fill="#3c3b6e"/>'+stars)
    flag_map = '['+','.join("'"+lang+"'=>"+json.dumps(flag) for lang,flag in flags.items())+']'
    prefix += "$fmLanguageSelector=str_replace('FLAG_IMAGE',"+flag_map+"[$fmLang],$fmLanguageSelector);\n"
    if source_title:
        titles={'hu':source_title, **catalog.get(source_title, {'en':source_title,'de':source_title})}
        prefix += '$fmPageTitle=['+','.join("'"+lang+"'=>"+json.dumps(title,ensure_ascii=False) for lang,title in titles.items())+'][$fmLang];\n'
        prefix += '''?>
<script>(()=>{const label=<?=json_encode($fmPageTitle)?>;const host=document.querySelector('div.title > span.left');if(host){const node=Array.from(host.childNodes).find(n=>n.nodeType===3&&n.textContent.trim());if(node)node.nodeValue=label;}document.title=document.title.split('/')[0]+'/'+label;})();</script>
<?php
'''
    variants = []
    for index, lang in enumerate(['en', 'de', 'hu']):
        translated = body
        if lang != 'hu':
            keys = sorted(catalog, key=len, reverse=True)
            translated = re.sub('|'.join(re.escape(k) for k in keys), lambda m: catalog[m[0]][lang], body)
            translated = translated.replace("'hu-HU'", "'en-US'" if lang == 'en' else "'de-DE'")
            if lang == 'en':
                translated = translated.replace(",1,',',' '", ",1,'.',','")
        if 'Dashboard:0' in header:
            translated = translated.replace('<!--FM_LANGUAGE-->', '{$fmLanguageSelector}')
        else:
            translated = translated.replace('<?php\n', '<?php\necho $fmLanguageSelector;\n', 1)
        condition = f"if($fmLang==='{lang}')" if index == 0 else (f"elseif($fmLang==='{lang}')" if index == 1 else 'else')
        variants.append(condition+'{ ?>\n'+translated+'\n<?php } ')
    favicon = ''
    if 'Dashboard:0' not in header:
        uri='data:image/svg+xml;base64,'+base64.b64encode((ROOT/'icon.svg').read_bytes()).decode('ascii')
        favicon='<script>(()=>{document.querySelectorAll(\'link[rel~="icon"]\').forEach(e=>e.remove());const link=document.createElement("link");link.rel="icon";link.type="image/svg+xml";link.href='+json.dumps(uri)+';document.head.appendChild(link);})();</script>\n'
    return header+'---\n'+prefix+''.join(variants)+'?>\n'+favicon
