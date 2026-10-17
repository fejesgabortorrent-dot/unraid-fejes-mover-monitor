# Gazdagép-ellenőrzés — 2026-10-17

Gazdagép: FejesNAS, Unraid 7.3.3. A helyi böngészőkapcsolat helyreállt.

- VM Manager engedélyezve; libvirt elindult.
- domains megosztás létrejött a VM Manager indításakor.
- MemAvailable: kb. 16 GiB az ellenőrzéskor.
- Létező default NAT-hálózat aktív; hálózati beállítást nem változtattunk.
- FejesMover-Test létrehozva, 2 vCPU / 4096 MiB.
- Három SATA RAW virtuális lemez: 24 / 16 / 8 GiB; a WebGUI cache mögötti elhelyezést mutatott.
- Autostart kikapcsolva. Fizikai adatlemez és USB nincs átadva.
- Az első scriptfutás hibája: a virsh nem támogatja a net-list --state-active opciót. Javítás: net-list --name, amely alapból aktív hálózatokat listáz.
- Az automatikus EFI firmware-választás hiányzó edk2-i386-vars.fd fájlra mutatott. Javítás: a meglévő Unraid ovmf-x64 OVMF_CODE-pure-efi.fd és OVMF_VARS-pure-efi.fd explicit használata, saját nvram.fd-val.
- A VM indítása sikeres: virsh start sikeres, domstate running. A VM a WebGUI listájában is megjelent.
- Az üres teszt-VM az indításpróba után leállítva, hogy ne foglaljon 4 GiB RAM-ot.

## Ami nem történt meg

Az USB-eszközlistában hub, Logitech receiver és APC UPS látszott, külön tesztpendrive nem. Nincs telepített Unraid vendég, nincs vendéglicenc, nincs Mover/plugin elfogadási teszt. A sikeres VM-indítás csak a virtualizáció működését igazolja; Unraid-bootot nem.

Következő feltétel: külön előkészített Unraid tesztpendrive csatlakoztatása és azonosítása, külön érvényes tesztlicenc/próbalicenc, majd vendégtelepítés és a RESULTS-HU.md szerinti tesztek.
