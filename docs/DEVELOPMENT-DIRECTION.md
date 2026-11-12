# Fejes Mover Monitor – elfogadott fejlesztési csapásvonal

Rögzítve: 2026-11-10. Gábor kifejezett döntése alapján.

Ez a dokumentum a következő kiadások sorrendjét és tervezési irányát rögzíti. Terv, nem megvalósítási vagy kompatibilitási igazolás.

## 1. Stabil Unraid 7-es kiadás

Elsőbbséget élvez a jelenlegi plugin befejezése. A kiadás előtt a pontos kiadásjelöltet a külön FejesMover-Test VM-en kell ellenőrizni: telepítés/frissítés, teljes védett mozgatás, valódi korhatár, fájlépség és metaadatok, torrentenkénti kihagyás, seedfolytonosság és peer-adatátvitel, API-kiesés és integritásvizsgálat alatti biztonságos halasztás, valamint újraindítás utáni működés. A komponenspróba nem helyettesíti a teljes futtató elfogadási tesztjét. A korhatárt az igazoláshoz nem kapcsoljuk ki és nem hamisítjuk az időadatokat.

A tesztek az elkülönített VM-en történnek. Az éles NAS módosítása nem része ennek a fejlesztési felhatalmazásnak.

## 2. Docker-alapú változat külön fejlesztési ágon

A stabil 7-es kiadás után külön ágon indul a konténeres változat. Javasolt, elfogadott alapfelépítés:

| Összetevő | Futtatás |
| --- | --- |
| Kezelőfelület, állapotmegjelenítés, naplók, tervezés | Docker-konténer |
| Natív mozgatás, koordinációs zárolások és hiteles rendszerellenőrzések | Kis, korlátozott jogosultságú Unraid-segéd |

A konténer a szükséges műveleteket szűk, ellenőrzött kapcsolaton kéri a segédtől. A segéd minden művelet előtt önállóan ellenőrzi a profilt, útvonalakat és védelmeket. A konténeresítés nem lazíthatja a meglévő fájl-, torrent-, integritás-, paritás-, mentés- és ütközésvédelmeket. A jogosultságok, hitelesítés és a kapcsolat pontos megvalósítását külön műszaki terv és tesztek véglegesítik.

A kiadás része legyen a meglévő beállítások és bizonyítékok megőrzésével végzett, dokumentált migráció és visszaállítás. A jelenlegi plugin lecserélése nem indul el automatikusan e döntés rögzítésével.

## 3. Unraid 8 felkészítés és igazolás

A közös alkalmazáslogikát és az Unraid-verziótól függő kapcsolódást különítjük el. A 8-as rendszerhez a hivatalos pluginrendszerhez/API-khoz és jogosultsági modellhez illő segédet vagy adaptert készítünk. Külön tesztkörnyezetben vizsgáljuk a konténert, a natív mozgatást, az útvonalakat, jogosultságokat, zárolásokat, integritáskapcsolatot, migrációt és újraindítást.

A Dockerre váltás önmagában nem bizonyít Unraid 8-kompatibilitást. A támogatást csak a megfelelő Unraid 8-as rendszeren végrehajtott és közzétett elfogadási eredmények után állítjuk. A 7-es stabil kiadást nem tesszük függővé a még változó 8-as fejlesztői felület elkészültétől.

Hivatalos háttér: https://unraid.net/blog/unraid-8-qa (2026-10-15). A közlemény új pluginrendszert, a meglévő konténersablonok megtartását és natív Docker Compose-támogatást tervez; a részletek változhatnak.

## Kötelező sorrend

1. Stabil, igazolt Unraid 7-es plugin.
2. Külön ágon Docker-felület és korlátozott Unraid-segéd.
3. Valódi Unraid 8-as tesztekkel igazolt támogatás.
