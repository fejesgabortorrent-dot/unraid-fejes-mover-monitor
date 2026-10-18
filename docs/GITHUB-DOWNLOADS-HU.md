# GitHub-letöltésszámláló, nyilvános NAS-végpont nélkül

A tulajdonos NAS-a kifelé lekéri a GitHub nyilvános Releases API-ját.
Csak a `fejes.mover.monitor.plg` nevű feltöltött kiadási fájlok számait adja
össze, az összes publikált kiadáson, a bétákat is beleértve. Dokumentumok,
ellenőrzőösszegek és forrásarchívumok nem szerepelnek az összegben.

Ez letöltésszám: ismételt letöltés, frissítés és automatizált letöltés is
számíthat. Nem igazolt telepítésszám és nem egyedi felhasználószám.
A raw.githubusercontent.com címen történő telepítéshez nem tartozik ilyen
asset-számláló. A Releases oldalon feltöltött PLG-t használd, ha ezt a
letöltési csatornát szeretnéd számolni. Törölt release/asset csökkentheti az
aktuális összeget; hiányzó régi adatból nem készítünk kitalált történeti számot.

## Tulajdonosi beállítás

Python 3 és Unraid notify szükséges, külső Python csomag és GitHub token nem.
Ez külön tulajdonosi segéd, nem fut a felhasználók plugintelepítésekor.
Az első futás csendben ment alapértéket; további növekedéskor a meglévő
értesítési ügynökökön küld összesített számot és különbséget.
`normal 4`: agent küldés, e-mail és böngészős felugró nélkül. A meglévő agent
beállításokat követi; ha több ügynök aktív, mind érintett lehet.

```
python3 /path/to/github_downloads.py
python3 /path/to/github_downloads.py --test
```

A `--test` egy külön tesztként jelölt üzenetet küld. A számláló titkos kulcsot
nem tárol. A mentett alapérték helye alapból
`/boot/config/plugins/fejes.mover.monitor/github-downloads.json`.
Fájlszintű zárolás és atomikus csere védi a párhuzamos futást. API- vagy
értesítési parancshiba esetén az alapérték megmarad az újrapróbáláshoz.
Az Unraid parancs sikere nem külön Telegram kézbesítési visszaigazolás.

Óránkénti futtatás elegendő. Az ütemezést külön a saját NAS-on állítsd be;
a plugin telepítője nem módosítja a cront. Leállításhoz a saját ütemezést
távolítsd el, a baseline megőrizhető. Bejövő portot és Funnel-t ne nyiss.

Dokumentáció: https://docs.github.com/en/rest/releases/assets
