# Fejes Mover – kétirányú seed-cache terv

Állapot: fejlesztési terv és csak olvasó döntési prototípus. A cache → tömb
irányból egy éles, korlátozott tulajdonosi próba sikeres. A tömb → cache
végrehajtó és annak felülete még nincs kész és nincs bekapcsolva.

## Cél

Egy Filmek megosztás, változatlan qBittorrent-útvonal. A rendszer a visszatérően
keresett kész tartalmat mérlegelheti a cache-re, a ritkán használt tartalmat a
lemeztömbön tartja. Az SSD önmagában nem garantál gyorsabb feltöltést: a hálózat,
VPN, peeroldal és az aktuális lemezterhelés is korlátozhat. A bevezetés előtt
méréssel kell igazolni, hogy a mozgatás előnye meghaladja annak költségét.

## Kereslet felismerése

A teljes életútra számolt arány helyett feltöltött bájtok különbségeit mérjük.
A prototípus két, 5–60 perc különbségű mintát és 64 MiB forgalmat vizsgál.
A végleges vezérlőhöz ez önmagában kevés: javasolt alapbeállítás legalább két
pozitív, egymást nem átfedő 30 perces ablak az elmúlt 24 órában. Ezek javasolt,
még hangolandó értékek. Egyetlen rövid kiugrás ne indítson nagy fájlmozgatást.

Mintavételkor rögzíteni kell a számláló eredetét és a kliens futási generációját.
Újraindítás, számlálócsökkenés, hiányzó minták vagy API-hiba esetén nincs
keresletbecslés. Torrentenkénti forgalom nem bizonyítja, hogy egy többfájlos
csomag melyik részét kérik: ilyen esetben ne jelöljük automatikusan minden
fájlt forrónak. A kliens adapterének ezt tisztáznia kell.

## Állítható korlátok

| Beállítás | Javasolt induló érték | Jelentés |
| --- | --- | --- |
| Seed-cache bekapcsolva | Nem | Külön engedélyezhető funkció |
| Visszahozott tartalom összesen | 100 GiB | Teljes kezelt seed-cache keret |
| Minimum szabad cache | 300 GiB | Letöltések és rendszer tartaléka |
| Visszahozás körönként | 32 GiB, 2 fájl | Műveleti korlát |
| Minimum tartózkodás | 24 óra | Ide-oda mozgatás elleni védelem |
| Kihűlés | 72 óra kereslet nélkül | Javasolt visszaengedési feltétel |

A visszahozási keret:

`min(körkorlát, szabad hely − tartalék, összlimit − jelenlegi seed-cache)`

Negatív eredmény esetén nulla. A meglévő kezelt tartalmat és a futó műveletek
helyfoglalását is bele kell számítani; ismeretlen leltár esetén nincs indítás.
Az összlimit túllépése nem törölhet tartalmat és nem indíthat vak visszamozgatást.
A limitben fizikai fájlonként egyszer számolunk, akkor is, ha több torrent
hivatkozik rá. A kézi fájlmozgatást és a hiányzó fájlokat egyeztetni kell a
nyilvántartással. A prototípus megköveteli a hiteles összesített foglaltságot;
a helyi leltáradapter még megvalósítandó.

## Döntési sorrend

1. Mentés, paritás, scrub, másik mozgató, lemezállapot és zárolások ellenőrzése.
2. Kevés szabad helynél a kifelé mozgatás kap elsőbbséget; nincs visszahozás.
3. Kereslet és fizikai elhelyezés hitelesítése, minden érintett torrent vizsgálata.
4. Csak kész, stabil, éppen nem nyitott és nem aktívan használt fájl jelölhető.
5. Tartózkodási idő, összkeret és körkorlát ellenőrzése.
6. Végrehajtás előtt minden feltétel újbóli ellenőrzése.
7. Tartós másolat, checksum és metaadatellenőrzés, helyreállítható átállás.
8. Kliensútvonal, teljesség és seedállapot vizsgálata; külön valódi peerfeltöltési próba.

A forróként cache-re hozott fájlra a kifelé mozgatónak is ismernie kell a
védett tartózkodási időt, különben a meglévő koralapú szabály visszavinné a
tömbre. Helyhiány esetén a vészhelyzeti feloldás külön, naplózott szabály legyen.
E két irány közös állapotgépe és zárolása a bekapcsolás előfeltétele.

## Felület

Külön „Seed-cache” panel: kikapcsolva / megfigyelés / engedélyezve állapot,
kezelt GiB és összlimit, szabad tartalék, pozitív keresleti ablakok, utolsó
mozgatás és fájlonkénti indok. A kereslet, a teljes arány és a tracker által
igazolt seedkötelezettség külön fogalom. Trackeradat hiányában „nem ismert”
jelzés kell. A jelenlegi prototípus nem kérdezi le a tracker kötelezettségét.

## Bevezetés és elfogadási feltételek

1. Csak olvasó élő adapter és 24–72 órás mintagyűjtés. Fájlmozgatás nélkül.
2. Az előnézet magyarázza a jelöléseket és a kihagyásokat, keretelszámolása
   hibátlan ismert és hiányos minták mellett is.
3. Elkülönített Unraid-tesztadat: mindkét irány, megszakítás és visszaállítás.
4. Ütköző cél, megtelt cache, API-kiesés, kliensrestart, hardlink, többfájlos és
   megosztott tulajdonú torrentek, párhuzamos Mover tesztje.
5. Egyetlen kész torrenttel éles visszahozás és tényleges peerfeltöltés mérése.
6. Opt-in béta, majd hosszabb felügyeleti időszak. Stabil kiadás csak az
   elfogadási bizonyítékok után. Az uninstall kapcsolja le a funkció saját
   ütemezését, és őrizze meg a helyreállításhoz szükséges tranzakciós állapotot.

Jelenleg a 300 GiB tartalék alatt nincs hely visszahozásra. Először a kifelé
mozgatásnak kell elegendő szabad helyet biztosítania. A jelenlegi 6 órás várakozás
és a sok apró fájl által elfoglalt 8-fájlos körkorlát külön hangolást igényel;
ez a seed-cache terv nem oldja meg automatikusan a helyfelszabadítás ütemét.
