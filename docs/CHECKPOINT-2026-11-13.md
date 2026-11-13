# Fejes Mover Monitor — mentési pont, 2026-11-13

## Ellenőrzött fejlesztési állapot

Ág: `feat/managed-scheduler`, draft PR: #40.
Ellenőrzött GitHub kódcommit: `fd5b43d96f64c65cf8037a7938f6984d46ff1f2c`.
A teljes GitHub Actions ellenőrzés sikeres: #125, run `43449505864`.
A helyi ütemezőtesztek: 24 sikeres teszt.

Elkészült a profilhoz kötött, külön bekapcsolható saját ütemező,
a háromnyelvű beállítóoldal, a mentés előtti biztonsági másolat,
a hibánál kikapcsolva maradó konfigurációmentés és a saját cronbejegyzés
telepítési/eltávolítási kezelése. A főoldal a ténylegesen bejegyzett
ütemezést és a választott időközt mutatja. Hiányzó, hibás vagy duplikált
cronbejegyzést nem igazol aktívként. A kikapcsolt állapot külön látható.

## Kiadási állapot

Az éles karbantartási javítás verziója 2026.11.13.1.
A saját ütemező fejlesztési változata nincs élesítve és nincs a stabil
frissítési csatornába összeolvasztva. Az automatikus verzióemelés teljes
kiadási folyamatának ellenőrzése még hátravan.

## Következő lépések

1. Külön fejlesztési verziószám és frissítési cél a tesztcsomaghoz.
2. Telepítés, frissítés, bekapcsolás/kikapcsolás, eltávolítás és reboot
   elfogadási próbája a FejesMover-Test gépen.
3. Áttérés a korábbi User Scripts ütemezésről, kettős indítás nélkül.
4. A megmaradt cache/Btrfs, scrub és File Integrity előfeltételek kezelése;
   a támogatott környezet egyértelmű leírása.
5. Csak ezek után stabil kiadás és szélesebb telepíthetőség igazolása.

A tesztgép konzolja elérhető, a hostname igazolt: FejesMover-Test.
Ebben a munkaszakaszban az új csomag VM-telepítése és reboot-próbája még
nem történt meg. A konzol egy korábbi sikeres mozgatási és peer-átviteli
próba eredményét mutatta; ez nem az új ütemező elfogadási eredménye.
A VNC szövegbeillesztés nem működött; az egyenkénti billentyűbevitel igen.
