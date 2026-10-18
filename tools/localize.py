"""Compile trusted UI literals into three self-contained PHP page branches.

Only source templates are translated: filenames, logs and runtime script contents
never pass through replacement. Runtime language selection is an allowlisted cookie.
"""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]

def compile_page(source):
    catalog = json.loads((ROOT / 'src/translations.json').read_text(encoding='utf-8'))
    for key, values in catalog.items():
        if set(values) != {'en', 'de'} or any(not isinstance(v, str) or any(c in v for c in "\"'\\$<>\r\n") for v in values.values()):
            raise ValueError(f'Unsafe or incomplete source-literal translation: {key}')
    header, body = source.split('---\n', 1)
    # Unraid menu metadata is static; neutral English names work in every locale.
    header = header.replace('Mover figyelő', 'Mover Monitor').replace('Mover beállítások', 'Mover Settings')
    selector = '''<label style="display:inline-block;margin:10px 12px;font-size:14px">🌐 <select aria-label="Language / Nyelv / Sprache" onchange="document.cookie=\x27fejes_mover_lang=\x27+this.value+\x27; Path=/; Max-Age=31536000; SameSite=Lax\x27;location.assign(location.pathname)"><option value="hu" HU_SELECTED>Magyar</option><option value="en" EN_SELECTED>English (US)</option><option value="de" DE_SELECTED>Deutsch</option></select></label>'''
    prefix = '''<?php
$fmCookie=$_COOKIE['fejes_mover_lang']??'hu';
$fmLang=is_string($fmCookie)&&in_array($fmCookie,['hu','en','de'],true)?$fmCookie:'hu';
$fmLanguageSelector=SELECTOR;
$fmLanguageSelector=str_replace(['HU_SELECTED','EN_SELECTED','DE_SELECTED'],[$fmLang==='hu'?'selected':'',$fmLang==='en'?'selected':'',$fmLang==='de'?'selected':''],$fmLanguageSelector);
'''.replace('SELECTOR;', json.dumps(selector, ensure_ascii=False).replace('\\/', '/')+';')
    # JSON double-quoted text is a PHP double-quoted literal; selector has no $.
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
    return header+'---\n'+prefix+''.join(variants)+'?>\n'
