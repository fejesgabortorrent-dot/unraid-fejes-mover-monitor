# Helyi böngészős teszt – 2026. október 18.

A `tools/browser_demo.py` az alkalmazás tényleges, háromnyelvűre fordított
PHP-oldalait szolgálja ki helyi, ideiglenes tesztadatokkal. Nem egy külön rajzolt
makett: ugyanazokat az oldalakat, frissítési kódot és mentési védelmeket használja.
A cache-kapacitás és a Mover-folyamat szimulált.

Indítás PHP-val, Bash-sel és Pythonnal:

```
python tools/browser_demo.py --port 8765
```

Cím: http://127.0.0.1:8765/Tools/FejesMover

Csak a helyi gépről érhető el. A szerver minden éles Unraid elérési utat egy
ideiglenes mappára irányít át; a próba-mentés is kizárólag ebben dolgozik.
Leállításkor az ideiglenes tesztadatok törlődnek. Ez fejlesztői eszköz, a PLG
nem telepíti és a checksum-lista sem tartalmazza.

Böngészőben ténylegesen ellenőrizve:

- Magyar → English (US) → Deutsch nyelvváltás és oldalak közötti megőrzés.
- Megtelt cache: 100% foglaltság, nulla szabad hely, küszöb alatti üzenet.
- Nem csatolt cache: ismeretlen „—” kapacitás a figyelőn és a dashboardon.
- Beállítások élő előnézete: 400 GiB küszöb, 180 perc = 3 óra.
- Próba-mentés: sikeres mentés és ellenőrzött visszaolvasás, biztonsági másolat.
- Futó Mover tesztállapotban a következő módosítás elutasítása, 400 GiB megőrzése.
- Futó folyamat kijelzése és automatikus frissítés szüneteltetése.

Nem történt valódi fájlmozgatás vagy NAS-módosítás. A teszt nem igazolja az
Unraid plugin manager integrációját és az újraindítás utáni működést.
