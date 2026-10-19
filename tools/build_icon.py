"""Render the code-native Fejes Mover mark (Pillow required only to rebuild PNG)."""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SCALE = 4
im = Image.new('RGB', (256*SCALE, 256*SCALE), '#283747')
d = ImageDraw.Draw(im)
def box(rect, fill, radius=0, outline=None, width=1):
    d.rounded_rectangle(tuple(v*SCALE for v in rect), radius=radius*SCALE,
                        fill=fill, outline=outline, width=width*SCALE)
def poly(points, fill):
    d.polygon([(x*SCALE,y*SCALE) for x,y in points],fill=fill)
def line(points,fill,width):
    d.line([(x*SCALE,y*SCALE) for x,y in points],fill=fill,width=width*SCALE)
box((4,4,252,252),'#334555',40,'#7891a6',2)
# Font-independent FM, shared geometry with the SVG.
fm=[[(46,49),(97,49),(97,63),(62,63),(62,79),(91,79),(91,93),(62,93),(62,119),(46,119)],
    [(111,119),(111,49),(129,49),(151,83),(173,49),(191,49),(191,119),(175,119),(175,76),(151,111),(127,76),(127,119)]]
for points in fm: poly(points,'#f4f7fa')
for x in (32,143):
    box((x,150,x+81,206),'#496074',10,'#afc4d4',2)
    line([(x+12,166),(x+57,166)],'#d2dfe9',3)
    box((x+12,185,x+18,191),'#ff903f',3)
    box((x+24,185,x+30,191),'#d2dfe9',3)
arrow=[(72,134),(155,134),(155,124),(180,141),(155,158),(155,148),(72,148)]
poly(arrow,'#ff903f')
shield=[(198,174),(224,184),(222,211),(214,225),(198,236),(182,225),(174,211),(172,184)]
poly(shield,'#55d6a0')
line([(183,202),(194,213),(213,191)],'#283747',6)
im.resize((256,256),Image.Resampling.LANCZOS).save(ROOT/'icon.png')
path=lambda pts:'M'+' L'.join(f'{x} {y}' for x,y in pts)+' Z'
svg=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" role="img" aria-label="FM — Fejes Mover">',
 '<title>Fejes Mover</title><rect width="256" height="256" fill="#283747"/>',
 '<rect x="4" y="4" width="248" height="248" rx="40" fill="#334555" stroke="#7891a6" stroke-width="2"/>']
svg += [f'<path d="{path(p)}" fill="#f4f7fa"/>' for p in fm]
for x in (32,143):
    svg += [f'<rect x="{x}" y="150" width="81" height="56" rx="10" fill="#496074" stroke="#afc4d4" stroke-width="2"/>',
            f'<path d="M{x+12} 166h45" stroke="#d2dfe9" stroke-width="3"/>',
            f'<circle cx="{x+15}" cy="188" r="3" fill="#ff903f"/><circle cx="{x+27}" cy="188" r="3" fill="#d2dfe9"/>']
svg += [f'<path d="{path(arrow)}" fill="#ff903f"/>',f'<path d="{path(shield)}" fill="#55d6a0"/>',
        '<path d="M183 202l11 11 19-22" fill="none" stroke="#283747" stroke-width="6"/>','</svg>']
(ROOT/'icon.svg').write_text('\n'.join(svg)+'\n',encoding='utf-8',newline='\n')
print('Built icon.png (256 x 256) and editable icon.svg')
