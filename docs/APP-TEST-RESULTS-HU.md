# FejesMover alkalmazásteszt — 2026-10-17

**Eredmény: 15/15 alkalmazásellenőrzés sikeres.**

Futtatás: Ubuntu 24.04, PHP CLI 8.3.6, ctype bővítmény. A PHP az Ubuntu hivatalos csomagjaiból elkülönítve futott; a NAS-ra nem telepítettünk csomagot. Teszt: `python3 tools/app_test.py`. A teszt a forrásoldalak másolatainak adatforrásait ideiglenes helyi fájlokra irányítja. Az eredeti forrás és a NAS állapota változatlan.

| Vizsgálat | Eredmény |
|---|---|
| Inaktív Mover részletoldal PHP-figyelmeztetés nélkül | Sikeres |
| Hiányzó cache kapacitása elérhetetlenként jelenik meg | Sikeres |
| HTML-t tartalmazó syslog szövegként jelenik meg | Sikeres |
| Hiányzó opcionális automatika kezelése | Sikeres |
| Dashboard kártya PHP-futása és előállítása | Sikeres |
| Elavult PID bizonytalanként jelölése | Sikeres |
| Mover felismerése mesterséges /proc adatokból | Sikeres |
| Meglévő script beállítóoldala megjelenik | Sikeres |
| Hibás CSRF-token nem írhatja át a scriptet | Sikeres |
| Ütköző forráshash nem írhatja át a scriptet | Sikeres |
| Érvénytelen érték nem írhatja át a scriptet | Sikeres |
| Mover PID jelenléte blokkolja a módosítást | Sikeres |
| Érvényes módosítás mentése és visszaolvasása | Sikeres |
| Biztonsági másolat pontosan az eredeti scriptet őrzi | Sikeres |
| Változatlan érték nem készít új mentést | Sikeres |

A `tools/check.py` csomagteszt ismét sikeres: reprodukálható build, ellenőrzőösszegek, XML, PHP-szintaxis, elkülönített telepítés/ismételt telepítés, hibás PHP elutasítása, eltávolítás és idegen fájl megőrzése.

## Határok

Ez végrehajtott PHP-alkalmazásteszt tesztadatokkal. Nem ellenőrzi a böngészős JavaScriptet, a vizuális elrendezést, az Unraid WebGUI integrációját, a valódi Mover-t, a flash fájlrendszer sajátosságait vagy az Unraid plugin managerének újraindítás utáni működését. Nem helyettesíti a külön Unraid elfogadási tesztet, és nem jelent Community Applications jóváhagyást.
