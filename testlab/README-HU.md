# FejesMover elkülönített Unraid tesztlabor

Állapot (2026-10-17): FejesNAS-on létrehozva és sikeresen elindítva, majd leállítva a FejesMover-Test VM. Unraid vendég OS és plugin tesztje még nem futott; külön bootpendrive és licenc hiányzik. Részletek: HOST-RESULTS-HU.md.

## Ami kell

| Tétel | Előkészített választás |
|---|---|
| Gazdagép | FejesNAS, működő KVM és VM Manager szükséges |
| Vendég neve | FejesMover-Test |
| CPU / RAM | 2 vCPU, fix 4096 MiB; szabad kapacitás függvényében |
| Gép / firmware | Q35, OVMF, QEMU XHCI USB 3.0 |
| Virtuális lemezek | SATA RAW: parity 24 GiB, data 16 GiB, cache 8 GiB |
| Szabad tárhely | legalább 50 GiB a domains megosztás mögötti tárhelyen |
| Rendszer | elsőként a gazdagépével azonos Unraid verzió |
| Boot és licenc | külön, egyedi GUID-os pendrive és külön érvényes licenc vagy a szolgáltató által engedélyezett próbalicenc |
| Megjelenítés | VNC; GPU- és HBA-átadás nem szükséges |
| Hálózat | meglévő NAT-hálózat a kezdeti VNC-teszthez; elérhető vendég-WebGUI-hoz ellenőrzött meglévő bridge vagy elkülönített teszthálózat |

A fenti erőforrások tervértékek: a gazdagép aktuális CPU-, RAM- és tárhelyadatait még nem tudtuk ellenőrizni. A 48 GiB virtuális lemez ritkán kiosztott fájlokból készül; a 50 GiB ellenőrzés nem tárhelyfoglalás vagy kvóta.

Hivatalos eszközök és dokumentáció:
- USB Creator Windowsra: https://unraid.net/download (Download for Windows)
- Unraid VM útmutató: https://docs.unraid.net/unraid-os/using-unraid-to/create-virtual-machines/unraid-as-a-vm/
- Bootmédia: https://docs.unraid.net/unraid-os/getting-started/set-up-unraid/create-your-bootable-media/
- Licenc: https://docs.unraid.net/unraid-os/troubleshooting/licensing-faq/

A telepítőt és a licencet nem mellékeljük. A VM-hez a fizikai tesztpendrive-ot kell kiválasztani; virtuális TPM-re nem építjük a licencelést. A dokumentáció a gazdagép bootpendrive-jától eltérő gyártót javasol/ír elő a kiválasztás miatt. Vásárlás nem történt.

## 1. Gazdagép előellenőrzése

A letöltött `testlab` könyvtárból a **gazdagép** terminálján:

```bash
bash prepare-host.sh --check
```

Ez csak olvas: nem indít VM-et, nem hoz létre lemezt, és nem módosítja a VM Managert. Ha a VM Manager ki van kapcsolva, a Settings → VM Manager oldalon ellenőrizni kell a beállításait. Az előellenőrzés nem kapcsolja be.

Sikeres ellenőrzés után:

```bash
bash prepare-host.sh --prepare
```

Ez kizárólag három új virtuális lemezfájlt hoz létre `/mnt/user/domains/FejesMover-Test` alatt. Meglévő célmappánál leáll; nem ír felül. Nem csatol fizikai lemezt és nem definiál/indít VM-et. Sikertelen létrehozásnál a részleges mappa megmarad ellenőrzésre.

### Automatikus VM-létrehozás (egyelőre nem futtatott gazdagépen)

Ha a meglévő libvirt `default` NAT-hálózat aktív, a kézi VM-definíció helyett:

```bash
bash prepare-host.sh --create-vm
```

Ez ugyanazt az előellenőrzést végzi, majd létrehozza a három lemezfájlt és definiál egy **kikapcsolt**, autostart nélküli `FejesMover-Test` VM-et. A script az Unraid ismert OVMF CODE és VARS fájljait ellenőrzi és használja. USB és fizikai lemez nincs hozzárendelve. A hálózatot nem módosítja. Ha lemezek vagy azonos nevű VM már léteznek, leáll; a `--prepare` után ezért ne használd ugyanazon a könyvtáron. Válaszd az egyik módot.

A külön tesztpendrive hozzáadása és bootprioritása még szükséges. A NAT-változat kezdetben VNC-ből, Unraid GUI bootmóddal használható; a vendég WebGUI-jának közvetlen LAN-elérését külön kell megoldani. A FejesNAS Unraid 7.3.3 gazdagépén a létrehozás és a javított OVMF-beállítással az indítás sikerült. Más gazdagépen külön ellenőrzés szükséges. Hiba esetén nem indít automatikus takarítást.

## 2. Tesztpendrive előkészítése Windowson

1. Válassz külön, üres tesztpendrive-ot; ellenőrizd a kapacitását és azonosítóját. Az USB Creator írása ezt a pendrive-ot törli.
2. A hivatalos letöltőoldalról indítsd az USB Creatort; a gazdagépével azonos Unraid verziót válaszd, EFI boot engedélyezve. Kiszolgálónév: `FejesMover-Test`.
3. A VM-útmutató szerint állíts egyedi bootcímkét, például `UNRAID-VM`; a bootbejegyzések `append` sorában az `unraidlabel=UNRAID-VM` argumentumot használd. Az EFI konfigurációt is igazítsd hozzá. Más kernelargumentumot ne törölj.
4. A dokumentáció szerint szükség esetén a pendrive gyökerében `startup.nsh` tartalma: `\EFI\boot\bootx64.efi`.
5. Dugd a külön tesztpendrive-ot a NAS-ba. A gazdagép saját bootpendrive-ját ne add át.

## 3. VM létrehozása a gazdagép VMs oldalán

Add VM → Slackware, majd a fenti táblázat szerinti értékek. Válaszd a három már létrehozott virtuális lemezfájlt, SATA busszal. USB alatt kizárólag az azonosított tesztpendrive-ot jelöld be. Autostart és Start after creation legyen kikapcsolva.

A hálózati csatlakozást a gazdagép tényleges konfigurációja alapján kell kiválasztani; a NAT-cím általában nem érhető el közvetlenül a Windows gépről. A script nem hoz létre bridge-et vagy porttovábbítást. Az elérhető, meglévő bridge használata előtt ellenőrizd a gazdagép hálózatát; a tesztgépnek külön DHCP-címe legyen.

Indíts VNC-konzollal. A vendégben egyedi root-jelszó és saját licenc/próbalicenc szükséges. A FejesNAS Lifetime kulcsát ne másold át. A licencfeltételeket a tulajdonosnak kell elfogadnia.

## 4. Vendég konfigurálása

A vendég-WebGUI-ban ellenőrizd: a kiszolgálónév **FejesMover-Test** és csak a 24/16/8 GiB-os virtuális lemezek látszanak.

- Parity: 24 GiB; Disk1: 16 GiB; pool neve pontosan `cache`, lemeze 8 GiB.
- Csak ezeknek az új virtuális lemezeknek a formázását végezd el. A bootpendrive nem adatlemez.
- Hozz létre `fejesmover-test` megosztást: Primary storage `cache`, Secondary storage `Array`, Mover action cache → Array. SMB export legyen kikapcsolva.
- Docker, VM Manager és automatikus Mover a vendégben maradjon kikapcsolva; a teszt során kézi Mover-indítás történik.
- A tesztpendrive beállításait és a leállított VM lemezfájljait mentsd el az első plugintelepítés előtt. RAW fájlon nincs automatikus qcow2 snapshot. A RAM-ban lévő vendégállapotot nem mentjük.

## 5. A rögzített pluginjelölt telepítése

A jelölt pontos commitját lásd `candidate.json` fájlban. A vendég Plugins → Install Plugin mezőjébe az ott lévő `plugin_url` kerüljön. A hivatkozás commitra rögzített; a plugin későbbi Update gombja viszont a manifestben megadott main ágat követi, ezért a jelölt frissítési tesztjét ugyanennek a rögzített URL-nek az ismételt telepítésével végezd.

Ez a saját, még nem jóváhagyott fejlesztői csomag: kizárólag a teszt-VM-ben használd. A külön User Scripts automatika nincs benne. A megfigyelés tesztjéhez nem kell telepíteni.

## 6. Tesztadat és ellenőrzés

A **vendég** terminálján másold be/futtasd `make-test-data.sh` tartalmát. Csak a pontos névvel ellátott vendégben és egy előre elkészített, a cache-t használó `fejesmover-test` megosztás mellett fut. Új, egyedi alkönyvtárba készít 256 MiB véletlen adatot és SHA-256 jegyzéket.

Nyisd meg Tools → Mover figyelő és a Dashboard oldalt. Indítsd kézzel a vendég Moverét. A másolás rövid lehet: az aktív állapot és fájlmegfigyelés tesztjét szükség esetén több, külön tesztadattal ismételd. A kész adatot ellenőrizd a script által kiírt `sha256sum -c` paranccsal, és a VM Main/megfelelő lemeznézetében nézd meg a tényleges elhelyezést. Az ellenőrzőösszeg egyezése önmagában nem igazolja az Array-re költözést.

`collect-report.sh` a vendég alapállapotát, a telepített oldalak ellenőrzőösszegét és PHP-szintaxisát írja a terminálra. Nem gyűjt teljes syslogot, licenckulcsot vagy jelszót. A kimenet átirányítható jegyzőkönyvfájlba.

Töltsd ki `RESULTS-HU.md` fájlt. Ténylegesen teszteld az ismételt telepítést, a vendég újraindítását, az eltávolítást és a visszaállítást is. A gazdagépet nem kell újraindítani. A beállítóoldal script nélküli állapotát ellenőrizd; az opcionális szerkesztő mentési tesztje külön, csak a vendégben létrehozott scriptmintával marad elvégzendő.

## Jelenlegi határ

Ez előkészített tesztcsomag, nem futó VM és nem sikeres Unraid-teszt. A szükséges fizikai tesztpendrive, aktuális gazdagép-erőforrások, licenc és hálózati hozzáférés ellenőrzése hátravan.
