# mensa

Speiseplan deutscher Mensen über die offene [OpenMensa-API v2](https://openmensa.org/api/v2). Standard-Mensa ist Heilbronn, Mensa Bildungscampus/Europaplatz (ID 277). Kein Login, keine schreibenden Requests.

## Schnellstart

```bash
pipx install git+https://github.com/smlfg/mensa-cli
mensa heute
mensa suche Heilbronn
mensa standard Bildungscampus
```

`mensa heute` zeigt den Speiseplan der Standard-Mensa für heute. `mensa suche Heilbronn` findet Mensen nach Stadt oder Name. `mensa standard Bildungscampus` speichert die Standard-Mensa lokal in `~/.config/mensa-cli/config.json`.

Weitere Befehle: `mensa heute`, `mensa woche`, `mensa gericht STICHWORT`. Filter: `--vegetarisch`, `--vegan`, `--max-preis`, `--rolle studierende|bedienstete|gaeste`.

Die UX-Spezifikation steht in [docs/UX.md](docs/UX.md).

## Lizenz

MIT, Copyright smlfg.
