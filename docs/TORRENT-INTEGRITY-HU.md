# Torrent, Mover és File Integrity — 2026-10-18

## Mi derült ki az élő vizsgálatból?

- A qBittorrentben az ideiglenes letöltési mappa ki volt kapcsolva. A félkész
  adatok közvetlenül a végleges médiamegosztásba íródtak.
- Két külön torrent ugyanazt a sorozatmappát használta; az egyik megállított,
  félkész állapotú volt. A leállított torrent tartalma is védendő.
- A megvizsgált Dynamix File Integrity watcher `close_write` és `moved_to`
  eseményekre indította a bunkert. Nem vizsgálta a torrent készültségét.
  Kizárás nem volt beállítva. Az ütemezett ellenőrzés alacsony prioritása nem
  került alkalmazásra a watcherben látott bunkerhívásokra.
- A qBittorrent és az shfs több szála olvasásra várt. Ez terhelési együttállás,
  nem bizonyíték arra, hogy a Mover okozta a korábbi memóriaelfogyást.
- Az ideiglenesen felfüggesztett disk3 watcher később vissza lett engedve.

Ez a dokumentum nem tartalmaz privát médiacímeket, trackercímeket, kulcsokat
vagy konkrét szervernaplókat.

## A repó határa

A Fejes Mover Monitor megfigyelő és opcionális paraméterszerkesztő. A tényleges
`Filmek_Mover_Threshold` script nincs a repóban. A PLG nem vezérli a Mover
fájlválasztását, nem állítja át a qBittorrentet, és nem javítja át más plugin
watcherét. A mostani változás egy önálló indítás előtti ellenőrzést ad hozzá.

## Az ellenőrző használata

Függőségek: Python 3 a NAS-on, Docker CLI; a kijelölt qBittorrent-konténerben
curl és a helyi 8080-as WebAPI olvasási elérése. Nem telepít csomagot és nem
kapcsolja ki a hitelesítést. Ha a helyi API nem érhető el, a kimenet halasztás.
Más port, távoli API vagy bejelentkezési folyamat jelenleg nem támogatott.

```bash
python3 tools/torrent_preflight.py
python3 tools/torrent_preflight.py --container binhex-qbittorrentvpn --json
```

| Kilépési kód | Jelentés | Az indító teendője |
| --- | --- | --- |
| 0 | A pillanatképben nincs torrentoldali akadály | A többi védelem vizsgálata |
| 10 | Félkész, ellenőrző, áthelyező vagy letöltési állapot | Mover-indítás halasztása |
| 20 | Nem igazolható API-, állapot- vagy útvonaladat | Mover-indítás halasztása |

A készültséget pontosan hasonlítja: a kerekítve 100%-os, valójában félkész
torrent továbbra is blokkol. Megállított letöltés is blokkol, és a teljes
torrent ellenőrzés vagy áthelyezés közben szintén blokkol. Hibaállapot, hiányzó
fájl, üres lista és ismeretlen új qBittorrent-állapot nem eredményez engedélyt.

A JSON-kimenet `protected_paths` mezője a félkész vagy elfoglalt tartalom
Docker bind mount alapján feloldott, egyedivé tett hostútvonalait sorolja fel.
A leghosszabb illeszkedő mount számít; nem feltételez konkrét médiamegosztást.
Egy közösen használt mappa akkor is védett, ha másik torrent már késznek jelzi.
A lista diagnosztikai adat: önmagában nem léptet életbe semmilyen kizárást.
Az alap szöveges kimenet nem ír ki fájlneveket; a JSON személyes útvonalakat
tartalmazhat, ezért nyilvános hibajegybe változatlanul ne kerüljön.

### A leállított, közös mappájú torrent korlátja

Az élő felmérésben egy megállított félkész torrent ugyanazt a mappát használta,
mint az aktív változat. Ez a konzervatív ellenőrző mindaddig halasztást ad,
amíg a megállított bejegyzés félkésznek jelzi magát, akkor is, ha a másik
időközben elkészül. Nem szabad változtatás nélkül automatikus indítási kapuként
bekötni olyan rendszeren, ahol ilyen bejegyzés marad: az tartós Mover-halasztást
és szabadhelyhiányt okozhat. A közös tartalom kezelését előbb rendezni kell;
az ellenőrző ezt nem oldja meg automatikus torrent- vagy fájltörléssel.

## Beillesztés a meglévő indítóba

Az élő indítót előbb be kell olvasni és ellenőrizni. Az alábbi csak beillesztési
minta, nem önálló telepítő. Az ellenőrző útvonala a tényleges telepítés helye
legyen; a jelenlegi PLG nem telepíti ezt a Python-fájlt.

A később beolvasott élő indító szabadhely-küszöböt, backup PID-et, paritásállapotot,
Mover PID-fájlt és percben számolt újrapróbálkozási időt vizsgál. Az indítási
időbélyeget közvetlenül a Mover meghívása előtt írja. Ezeket a bekötésnél meg
kell tartani, a torrent miatti halasztás pedig nem fogyaszthatja el az
újrapróbálkozási időablakot. A beolvasott verzió nem tartalmaz külön scrub-őrt,
folyamatok közötti indítási zárat vagy a cache mount tényleges ellenőrzését;
ezek meglétét a figyelő UI-ja sem állíthatja.

```bash
# A meglévő backup-, paritás-, scrub-, mount- és zárolásellenőrzések megtartandók.
# Közvetlenül a meglévő Mover-indítás előtt, annak zárolásán belül:
if python3 /ABSZOLUT/TELEPITESI/UT/torrent_preflight.py; then
  : # Ezután jönnek a meglévő további ellenőrzések és az eredeti indítóparancs.
else
  logger -t fejes-mover 'Mover halasztva: torrentellenőrzés nem engedte az indítást'
  exit 0
fi
```

Ez konzervatív, teljes Mover-indítást halasztó kapu, nem fájlonkénti kihagyás.
Ne kapcsold úgy élesbe, hogy közben nincs elég szabad hely a félkész adatokhoz.
Nem helyettesíti az Unraid saját Mover-kizárásait, és más úton vagy kézzel
indított Movert sem akadályoz meg. A pillanatkép után új torrent indulhat;
a futás közbeni összehangolás külön fejlesztés és élő teszt feladata.

## File Integrity: még hátralévő élő munka

1. A telepített `update.watcher.php` és `disks_mounted` forrását beolvastuk.
   A `folders` vesszővel elválasztott mappaszűrőket kezel, az `exclude` megosztásokat,
   a `files` fájlmintákat. Ezekből generálódik az `/etc/inotifywait.conf` regexe.
   A `rc.watcher` ezt olvassa; a `disks_mounted` csak hiányzó runtime-konfiguráció
   esetén generálja újra. A GUI mentése watcher-újraindítást és cron-generálást is
   indít. Ez a megvizsgált telepítés viselkedése, nem általános verziógarancia.
2. A kizárásnak a még változó tartalmat kell védenie, nem a teljes médiamegosztást.
   A scheduled verify és az eseményfigyelő külön útvonal, mindkettőt vizsgálni kell.
   A beolvasott bunker külön `-E` (megosztás) és `-F` (mappa) argumentummal fogad
   kizárásokat, míg a megvizsgált ütemezett generátor ezeket nem adta át. A pontos
   argumentumformát a bunker forrásából ellenőriztük: vesszővel elválasztott
   mintákat vesz át, és sed ERE-ként használja őket. A watcher `folders`
   beállításától nem állítható, hogy a cron is védett.
3. A kizárt tartalom befejezése után a kizárást fel kell oldani, a kész adatot
   pedig hash-elni kell. Statikus kizárás nem maradhat elfelejtve.
4. A közös torrentmappákat és a meglévő hashértékeket külön kell kezelni.
   Aktívan változó fájl checksum-eltérése önmagában nem bizonyít sérülést.
5. A külön ideiglenes letöltési mappára váltást kapacitás- és mozgatási vizsgálat
   előzze meg. Nagy, közösen használt félkész tartalmat nem mozgatunk vakon.

Az ellenőrző ezeket **nem automatizálja**, és a jelenlegi watcher-konfigurációt
sem módosítja. A GitHub-változás nem jelent kész NAS-telepítést.

## Az ütemezett ellenőrzés külön előellenőrzője

```bash
python3 tools/integrity_preflight.py --check-only
```

Az új indító beolvassa a meglévő generált `integrity-check.sh` scriptet és a
File Integrity konfigurációját. Az éppen félkész vagy elfoglalt torrentek
bind mounttal feloldott mappaneveit hozzáadja a statikus mappakizárásokhoz.
A bunkernek `-F`, a megosztáskizárásokhoz `-E` argumentumot ad át, idézőjelezve
és a sed reguláris kifejezései számára literálisan escape-elve. Egyszerű
betű/szám/pont/kötőjel/aláhúzás/plusz/szóköz mappaneveket támogat; más mintánál
halaszt. Egyforma nevű mappák más helyen is kimaradhatnak: ez konzervatív
túl-kizárás. Egyedi fájlmaszkot tartalmazó konfigurációt nem támogat.

Csak a megvizsgált generált shell-formátumot fogadja el. Megőrzi az eredeti
paritásfeltételt, heti lemezrotációt, nice/ionice és értesítési argumentumokat.
A kész torrentek nem okoznak globális halasztást; az aktív tartalommappákat
kizárja, a többi lemezterület ellenőrizhető marad. A statikus `folders`
kizárásokat a letöltés elkészülte önmagában nem törli: a korábban átmenetileg
felvett bejegyzéseket külön, ellenőrzötten fel kell oldani.

`--check-only` esetén csak API-olvasás és `bash -n` történik; nincs hash-elés,
konfiguráció- vagy időzítésmódosítás. Enélkül az eredeti ütemezett script
módosított példányát adja a bash stdin-jére; az eredeti scriptet nem írja át.
Ez a funkció nem fájltörlés, nem új checksum-baseline írása, és nem automatikus
korrupciójavítás. A meglévő ütemezés és értesítések mögöttes bunker-viselkedését
nem változtatja meg. Az eredeti script háttérfeladatai tovább futhatnak az
indító kilépése után, ugyanúgy, mint a plugin generált scriptjénél.

Telepítéskor a két Python-fájlt egy mappába kell tenni. A cron bekötés külön
lépés: egy már létező ütemezés mellé nem szabad másodikat engedélyezni.
Az eredeti ütemezést és generált scriptet menteni kell. Ha később az ütemezés,
lemezkiosztás vagy plugin formátuma változik, az integrációt újra ellenőrizni
kell. A wrapper nem tudja megakadályozni, hogy a pillanatkép után új írás
kezdődjön; az eseményfigyelő és az ideiglenes letöltési hely továbbra is külön
kezelendő. Az élő ütemezés bekötésének eredménye alább szerepel.

### A meglévő cron-bejegyzés bekötése

A két előellenőrző telepítése és sikeres élő `--check-only` teszt után a
`tools/wire_integrity_cron.py` a meglévő egyetlen cron-sort irányítja a helperre.
Nem hoz létre második ütemezést, nem módosítja a plugin PHP-forrását, és nem
indít azonnali hash-elést. A cron időmezői és kimeneti átirányítása megmaradnak.
Módosítás előtt újabb check-only teszt és kis `.txt` konfigurációs mentés készül;
a mentés szándékosan nem `.cron` végű, így nem lesz belőle második feladat.
Az `update_cron` hibája esetén az eredeti bejegyzést visszaállítja és újratölti.

Az élő gépen az `update_cron` első sora nem érvényes shebang volt (`#/bin/bash`),
ezért az eszköz kifejezetten `bash /usr/local/sbin/update_cron` formában hívja.
A segéd a plugincronokat `crontab -c /etc/cron.d -` paranccsal tölti be; a sima
`crontab -l` ezért nem megfelelő igazolás ezen a rendszeren. Az aktív
`/etc/cron.d/root` bejegyzést külön ellenőriztük.

### Élő próba eredménye — 2026-10-18

- A két segédfájl rögzített commitból, SHA-256 ellenőrzéssel lett telepítve.
- A NAS-os `--check-only` sikeres, öt mappakizárással; nem indított hash-elést.
- Az eseményfigyelőben öt átmeneti mappakizárás van, kis konfigurációs mentéssel.
- A meglévő vasárnap 05:00-s bejegyzés már az előellenőrzőt hívja;
  az `/etc/cron.d/root` aktív sora ezt igazolta. Második feladat nem lett hozzáadva.
- Teljes ütemezett hashfutás, pluginbeállítás-mentés utáni újrabekötés és reboot
  még nem lett tesztelve. Ez nem teljes Unraid-elfogadási teszt.
- Az öt statikus átmeneti kizárás befejezés utáni feloldása még hátravan.
- A Mover globális indítási kapuja nincs bekötve. Ehhez a cache kapacitását,
  a hátralévő letöltést és a megállított félkész bejegyzéseket fel kell mérni,
  nehogy a halasztás miatt a cache megteljen.

Ez a bejegyzés a plugin által generált fájlban él. A File Integrity GUI-ban
végzett későbbi mentés vagy pluginváltozás felülírhatja: akkor a bekötést újra
ellenőrizni és szükség esetén ezzel az idempotens eszközzel újra alkalmazni kell.
Nem állítunk be ennek elfedésére háttérben ismétlődő fájlátírást. A bekötés nem
jelent GUI-módosításokat is túlélő, teljes pluginintegrációt.

## Ellenőrzés

```bash
python3 tools/torrent_preflight_test.py
python3 tools/integrity_preflight_test.py
python3 tools/wire_integrity_cron_test.py
```

A tesztek hálózat és NAS-módosítás nélkül futnak. Lefedik a kész seedeket,
megállított és közel kész letöltést, ellenőrzést/áthelyezést, közös tartalomutat,
mountfeloldást, hibás adatot, időtúllépést és a privát kimenet elkerülését.
Teljes Unraid-, Mover- és File Integrity-elfogadási teszt még szükséges.
Az ütemezett indító további 8 tesztje ellenőrzi a sed-kizárások tényleges
illeszkedését, a meglévő parancsok megőrzését, hibánál a végrehajtás tiltását,
és hogy az ellenőrző mód nem indít hash-elést vagy ír át konfigurációt.
A cron-bekötés további 4 tesztje ellenőrzi az idempotens átirányítást,
formátumelutasítást, atomi fájlcserét és a bash-sal történő cron-újratöltést.
