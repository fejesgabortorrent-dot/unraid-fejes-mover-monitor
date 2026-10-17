# Codex review javítások – 2026. október 17.

Az eredeti #1 PR már merge-elve volt a javítás kezdetén. A javítóág az aktuális
`ada957f` főágból készült. Az öt review-megjegyzés hat érintett pontját kezeli:

- A részletező elérhetőségi jelzőt ad át; a dashboard frissítéskor is megőrzi a
  hiányzó vagy nem olvasható cache „—” állapotát.
- A nulla szabad bájt érvényes mérés: 100% foglaltság és küszöb alatti figyelmeztetés.
- A frissítés közben megnyomott szünet gomb állapota az új tartalom után is megmarad.
- A részletező a `/proc/self/mountinfo` alapján ellenőrzi a cache csatolását.
- A dashboard ugyanezt ellenőrzi; a beállítóoldal is csatolt cache-ből mér.
- A csomagellenőrzés a PLG mellett a SHA256SUMS fájl elavulását is elutasítja,
  és a vizsgálat után mindkét eredeti fájlt visszaállítja.

A PLG és a checksum-fájl újragenerálva. A build UTF-8, LF és POSIX útvonalakat
használ, így Windowson is reprodukálható.

Helyi ellenőrzések: PHP 8.4.26, Python 3.12, Node.js és hordozható Git Bash,
kizárólag ideiglenes fixture fájlokkal:

```
python tools/app_test.py
node tools/refresh_test.js
python tools/check.py
python tools/check_test.py
```

Sikeres: 23 alkalmazásteszt; mindhárom renderelt oldal JavaScript-szintaxisa;
szünet/frissítés versenyhelyzet és újraindítás; dashboard adatállapot-váltások;
PHP lint; XML; reprodukálható csomag és checksumok; elkülönített telepítés,
ismételt telepítés, hibás PHP elutasítása és eltávolítás; elavult PLG és
SHA256SUMS elutasítása az eredeti fájlok megőrzésével.

Az élő NAS nem változott. Unraid WebGUI-, reboot- és valódi Mover-próba ebben
a javítási körben nem történt. A javító PR nem lett automatikusan merge-elve.
