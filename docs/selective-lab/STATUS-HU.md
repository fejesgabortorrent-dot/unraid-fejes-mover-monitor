# Torrentenkénti kihagyás — fejlesztési állapot, 2026-10-22

Fejlesztési prototípus, nem telepíthető kiadás. A kód külön draft PR-ban
ellenőrizhető; a jelenlegi globális Mover-kapu bekötését nem módosítottuk.
A tervező nincs a PLG-be csomagolva.

## Elkészült

A `tools/selective_plan.py` csak olvasható fájlszintű tervet készít a qBittorrent
állapotából, fájllistáiból, Docker mountjaiból és egy fájlleltárból. Nem indít
Movert, nem módosít torrentet, nem küld riasztást és nem szüneteltet letöltést.

- Félkész, ellenőrzött vagy áthelyezett torrent összes felsorolt fájlját kihagyja.
- A kész és nem torrenthez tartozó fájlok külön jelöltek maradnak.
- Közös fájlnál bármely elfoglalt torrent védelme elsőbbséget kap.
- Az ismert ideiglenes `.!qB` fájlnévváltozat is védett.
- Hiányos, üres, ismeretlen vagy bizonytalan pillanatkép nem ad tervet.
- Útvonalbejárás, sortörés, kétértelmű mount és ismételt azonosító elutasítva.
- Symlink, könyvtár és külön nem igazolt hardlink nem lehet mozgatási jelölt.
- A kapacitási döntés külön jelzi a riasztási és az opcionális szüneteltetési
  igényt. Ez még csak döntési függvény; egyik műveletet sem hajtja végre.

A teljes helyi futásban 58 Python-teszt (ebből 8 új szelektív teszt),
64 felületi ellenőrzés és 31 módvédelmi ellenőrzés sikeres.
A célzott tesztparancs: `python3 -m unittest discover -s tools -p selective_plan_test.py`.

## Valódi Unraid-próba

Unraid 7.3.3, binhex-qbittorrentvpn, cache → array irányú Filmek megosztás.
Két saját, privát, tracker nélküli teszttorrent: egy kész 2 MiB fájl és egy
félkész fájl. Nem valódi médiatartalmak.

A tesztterv pontosan egy kész fájlt adott a `/usr/libexec/unraid/move`
programnak. Nem indította a globális `mover start` parancsot.

Megfigyelt eredmény:

- A kész fájl eltűnt a cache-ről, egy array-lemezen megjelent.
- A megosztási útvonalon és az array-példányon a SHA-256 egyezett.
- A félkész/ellenőrzés alatt álló fájl a cache-en változatlan maradt.
- A kész torrent előtte és az utólagos újraellenőrzés után is `stalledUP` állapotú
  volt, készültsége 100%, hátralévő bájt 0.
- Tényleges peer felé történő feltöltést ez a tracker nélküli próba nem igazol.

A nyers jelentést és a képernyőképet a privát tesztkörnyezetben tartjuk.
A teszttorrent-bejegyzéseket a próba után adatfájl-törlés nélkül
eltávolítottuk; a tesztadatokat megtartottuk. Ez a nyilvános összefoglaló
a megfigyelt ellenőrzések eredményét tartalmazza.

## Mi kell még az éles kiváltáshoz és kiadáshoz?

- Teljes futtató: friss API- és fájlrendszer-ellenőrzés minden fájl előtt,
  közös indítási zár, backup/paritás/küszöb/várakozás megőrzése.
- Megosztási beállítások, célhely és stabil user-share seedútvonal ellenőrzése;
  ideiglenes letöltési gyökerek és összetett mountok támogatása.
- Új torrent, újraellenőrzés vagy áthelyezés indulása futás közben;
  kapcsolatvesztés és hiba után az újabb mozgatások leállítása.
- Nyitott seedfájlok, többfájlos torrentek és hardlinkek valódi próbája.
- Riasztás, választható és csak letöltő torrentekre korlátozott szüneteltetés;
  napló és visszaállítási szabályok. Nincs automatikus általános folytatás.
- Valódi API-hiba, alacsony szabadhely és párhuzamos indítás tesztje.
- Megszakítás/újraindítás, csomagolás, telepítés, eltávolítás és rollback.

Az első sikeres fájlmozgatási próba nem jelent teljes éles elfogadást.
A GitHub-megosztás kizárólag fejlesztési áttekintést szolgál.
Éles kiadás és a globális védelem kiváltása még nem történt.
