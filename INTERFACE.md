# Schnittstelle: mensa

Verbindlicher Vertrag für `mensa`. Maßgeblich sind die Sitzungen in [docs/UX.md](docs/UX.md); Abweichungen sind Fehler.

## Aufruf

- Distribution `mensa-cli`, Console-Script `mensa`.
- Python-Paket `mensa_cli`, aufrufbar als `python -m mensa_cli` (für Tests).
- Python >= 3.10. Abhängigkeiten: `argparse` (Standardbibliothek) und `httpx` oder `requests`.
- Kein Login, keine Zugangsdaten, keine schreibenden Web-Requests.

```text
mensa [--version] [--help]
mensa heute   [MENSA-NAME] [FILTER] [--json]
mensa morgen  [MENSA-NAME] [FILTER] [--json]
mensa woche   [MENSA-NAME] [FILTER] [--json]
mensa tag     DATUM [MENSA-NAME] [FILTER] [--json]
mensa suche   SUCHBEGRIFF [--json]
mensa gericht STICHWORT [--mensa MENSA-NAME] [FILTER] [--json]
mensa standard MENSA-NAME [--json]
```

`--help` und `--version` enden immer mit Exit 0. `--help` ist für jedes Unterkommando verfügbar. Alle Namen und Suchbegriffe sind positional; es gibt keine Pflicht-Optionen und keine IDs in der Bedienung.

## Unterkommandos

### `mensa heute [MENSA-NAME]`

Speiseplan für den heutigen Tag. Ohne `MENSA-NAME` gilt die gespeicherte Standard-Mensa, sonst die Vorgabe Heilbronn, Mensa Bildungscampus/Europaplatz (ID 277).

### `mensa morgen [MENSA-NAME]`

Wie `heute`, aber für den Folgetag.

### `mensa woche [MENSA-NAME]`

Montag bis Sonntag der Woche, in der „heute“ liegt. Jeder Tag wird als eigener Abschnitt ausgegeben; geschlossene Tage und Tage ohne veröffentlichten Plan werden lesbar markiert. Ein Tag außerhalb des veröffentlichten Zeitraums ist kein Fehler.

### `mensa tag DATUM [MENSA-NAME]`

Ein einzelner Tag. `DATUM` ist eines von:

- `heute`, `morgen` (Groß-/Kleinschreibung egal),
- Wochentag `montag` … `sonntag` (nächster Termin ab heute, heute eingeschlossen),
- ISO `JJJJ-MM-TT`,
- deutsch `TT.MM.JJJJ`.

Ungültige oder unvollständige Datumswerte: Exit 2.

### `mensa suche SUCHBEGRIFF [--json]`

Sucht lokal in der Canteen-Liste über `name`, `city` und `address` (Teilstring, Groß-/Kleinschreibung egal) und gibt alle Treffer aus. Die OpenMensa-API hat keine serverseitige Namenssuche; das Tool lädt `/canteens?page=N`, bis eine Seite leer ist, und filtert lokal. Keine Treffer sind kein Fehler (Exit 0). Die Liste wird gecacht (siehe unten).

### `mensa gericht STICHWORT [--mensa MENSA-NAME] [FILTER] [--json]`

Durchsucht die nächsten 7 Tage ab heute (heute eingeschlossen) nach `STICHWORT` in Gerichtname, Kategorie und Hinweisen. Ohne `--mensa` gilt die Standard-Mensa. Keine Treffer: Exit 0.

### `mensa standard MENSA-NAME [--json]`

Löst den Namen auf und speichert die Mensa als Standard. Danach funktionieren `heute`, `morgen`, `woche`, `tag` und `gericht` ohne Namen. Bei mehreren Treffern gilt die Auswahlregel unten. Die Ausgabe nennt die gespeicherte Mensa im Format der UX-Sitzung.

## Auflösung von Mensa-Namen

- Vergleich: `casefold`, normalisierte Leerzeichen, Teilstring in `name`, `city` oder `address`.
- Genau ein Treffer: wird verwendet.
- Kein Treffer: Exit 2, Meldung mit nächstem Schritt `mensa suche SUCHBEGRIFF`.
- Mehrere Treffer und stdin/stdout sind ein TTY: nummerierte Liste, dann Prompt `Auswahl [1-2]:` (Bereich je nach Trefferzahl). Gültige Zahl wählt; ungültige Eingabe wird erneut gefragt. `Strg+C` bricht ohne Traceback mit Exit 1 ab; EOF bricht ohne Traceback mit Exit 2 ab.
- Mehrere Treffer ohne TTY: nummerierte Liste und Exit 2, keine geratene ID.
- `mensa suche` wählt nie aus, sondern listet immer.

## Filter

Gültig für `heute`, `morgen`, `woche`, `tag` und `gericht`:

| Flag | Bedeutung |
|---|---|
| `--vegetarisch` | Kategorie, Name oder Hinweise enthalten `vegetarisch`; vegane Gerichte zählen mit. |
| `--vegan` | Kategorie, Name oder Hinweise enthalten `vegan`. Es wird nichts aus Zutaten geraten. |
| `--max-preis BETRAG` | Preis der gewählten Rolle `<= BETRAG`; Dezimalpunkt oder -komma. Fehlt der Preis für die Rolle (`null`), wird das Gericht ausgeschlossen. |
| `--rolle studierende\|bedienstete\|gaeste` | Rolle für `--max-preis`, Vorgabe `studierende`. Die Ausgabe zeigt immer alle drei Preise. |

`--vegetarisch` und `--vegan` dürfen kombiniert werden; dann gilt die strengere Vegan-Prüfung. Die Filter wirken clientseitig auf jedes Gericht. Bleibt nach dem Filtern nichts übrig, ist das kein Fehler: `Keine Gerichte für den Filter.`, Exit 0.

## Ausgabe

### Text (stdout ist ein TTY und kein `--json`)

Einzelner Tag:

```text
Mensa: Heilbronn, Mensa Bildungscampus/Europaplatz (277)
Datum: Montag, 02.11.2026
Preise: Studierende / Bedienstete / Gäste (EUR)
Filter: vegan
  [Dessert] Pudding Creme mit Streusel — 0,90 / 1,40 / 2,00 EUR
```

- Kopfzeilen `Mensa:`, `Datum:` immer; `Preise:` bei Tagesplänen; `Filter:` nur wenn gesetzt (mehrere Filter kommagetrennt, z. B. `Filter: vegan, max 3,00 EUR (Studierende)`).
- Preisformat deutsch mit Komma und zwei Nachkommastellen; fehlender Preis als `–`.
- Gerichtzeile: zwei Leerzeichen, `[Kategorie]`, Name, `—`, drei Preise, `EUR`.
- Geschlossen (`closed: true`): `Geschlossen – kein Speiseplan veröffentlicht.`, Exit 0.
- Offen, aber `/meals` leer: `Kein Speiseplan veröffentlicht.`, Exit 0.
- `/days/{datum}` liefert 404: `Kein Speiseplan veröffentlicht (Datum außerhalb des veröffentlichten Zeitraums).`, Exit 0.
- Woche: Kopf `Mensa:` und `Woche: Montag, 02.11.2026 – Sonntag, 08.11.2026`, danach je Tag `## Montag, 02.11.2026` mit Gerichten oder Geschlossen-Meldung.
- Suche: `Mensen gefunden (N):` und je Treffer `  1) Name (ID) – Adresse`. Keine Treffer: `Keine Mensen gefunden.`
- Standard: `Standard-Mensa gespeichert: Name (ID)`.
- Gericht: `Treffer für "STICHWORT" (N):`, je Treffer Datum, Mensa und Gerichtzeile. Keine Treffer: `Keine Treffer für "STICHWORT" in den nächsten 7 Tagen.`

Farben sind optional und werden bei `NO_COLOR` oder nicht-TTY nicht verwendet. Prompts und Fehlermeldungen gehen an stderr, soweit sie nicht Teil der regulären Textausgabe sind.

### JSON

Mit `--json` oder wenn stdout kein TTY ist, steht auf stdout genau ein JSON-Objekt (auch bei Fehlern), keine weiteren Zeilen. Prompts (Namensauswahl) gehen an stderr.

```json
{"canteen": {"id": 277, "name": "Heilbronn, Mensa Bildungscampus/Europaplatz", "city": "Heilbronn", "address": "Bildungscampus 8, 74076 Heilbronn"},
 "date": "2026-11-02",
 "weekday": "Montag",
 "closed": false,
 "filter": {"vegan": true, "vegetarian": false, "max_price": null, "role": "studierende"},
 "meals": [{"id": 29313654, "name": "Gemüsebolognese mit hausgemachter Pasta", "category": "Vegan",
            "prices": {"students": 0.99, "employees": 1.35, "pupils": null, "others": 2.0},
            "notes": ["Gemüsebolognese mit hausgemachter Pasta"]}]}
```

Weitere Formen:

- `woche`: `{"canteen": {...}, "week": {"start": "2026-11-02", "end": "2026-11-08"}, "days": [{"date": "...", "weekday": "...", "closed": false, "meals": [...]}]}`
- `suche`: `{"query": "Heilbronn", "results": [{"id": 277, "name": "...", "city": "...", "address": "..."}]}`
- `standard`: `{"standard": {"id": 277, "name": "..."}, "config_path": "/home/user/.config/mensa-cli/config.json"}`
- `gericht`: `{"query": "Pasta", "canteen": {...}, "days": 7, "matches": [{"date": "...", "weekday": "...", "canteen": {...}, "meal": {...}}]}`
- Fehler: `{"error": "...", "next": "...", "exit_code": 2}` (zusätzliche Felder erlaubt).

## Exit-Codes

| Code | Bedeutung |
|---|---|
| 0 | Erfolg, auch geschlossener Tag, leerer Plan, keine Suchtreffer bei `suche`/`gericht`. |
| 1 | Sonstiger Fehler: korrupte/unlesbare Config, lokaler Schreibfehler, Abbruch per `Strg+C`. |
| 2 | Usage: unbekanntes Unterkommando, ungültiges Datum, ungültiger Filterwert, unbekannter Mensa-Name, mehrdeutiger Name ohne TTY. |
| 3 | Netzwerk oder Quelle: Timeout, DNS, HTTP 5xx, unerwarteter Status, kaputtes JSON. |
| 4 | Quelle verlangt Login/Zustimmung (HTTP 401/403). Bei `mensa` derzeit nicht verwendet; Meldung nennt, dass es keinen Login gibt. |

Fehler nennen den nächsten Schritt und erzeugen keinen Traceback, auch nicht bei `Strg+C`, EOF oder fehlender optionaler Abhängigkeit.

## Umgebungsvariablen

| Variable | Bedeutung |
|---|---|
| `MENSA_BASE_URL` | Basis-URL der API, Vorgabe `https://openmensa.org/api/v2` (kein abschließender `/` nötig). Für Fake-Server/Tests. |
| `MENSA_HEUTE` | Nur Test/Sitzungen: überschreibt das heutige Datum als `JJJJ-MM-TT`. Ungültig -> Exit 2 mit klarer Meldung. |
| `XDG_CONFIG_HOME` | Basis für die Config, Vorgabe `~/.config`. |
| `XDG_CACHE_HOME` | Basis für den Cache, Vorgabe `~/.cache`. |
| `NO_COLOR` | Deaktiviert Farben. |

## Config und Cache

- Config: `$XDG_CONFIG_HOME/mensa-cli/config.json`, sonst `~/.config/mensa-cli/config.json`.
- Inhalt: `{"canteen_id": 277, "name": "Heilbronn, Mensa Bildungscampus/Europaplatz"}`. Weitere Felder werden ignoriert.
- Schreiben nur durch `mensa standard`; Verzeichnis `0700`, Datei `0600`, atomar (temporäre Datei im selben Verzeichnis, dann `os.replace`). Nie ins Repo oder Arbeitsverzeichnis.
- Fehlt die Datei, gilt ID 277. Ist sie unlesbar oder kein gültiges JSON, Exit 1 mit Hinweis `mensa standard MENSA-NAME`.
- Cache: `$XDG_CACHE_HOME/mensa-cli/canteens.json`, sonst `~/.cache/mensa-cli/canteens.json`. Nur die Canteen-Liste, TTL 24 Stunden. Abgelaufene/unlesbare Caches werden neu geladen; ein nicht schreibbarer Cache ist kein Fehler.

## Datenquelle und Verhalten

- Basis: OpenMensa-API v2, Doku https://docs.openmensa.org/api/v2/.
- Nur GET: `/canteens?page=N`, `/canteens/{id}/days/{datum}`, `/canteens/{id}/days/{datum}/meals`.
- Mensa-Metadaten (Name, Stadt, Adresse) kommen aus der Canteen-Liste, nicht aus einem zusätzlichen `/canteens/{id}`-Request.
- Vor `/meals` wird `/days/{datum}` geprüft. `closed: true` beendet ohne Meals-Request.
- HTTP 404 auf `/days/{datum}` gilt als „kein Plan veröffentlicht“ (Exit 0); HTTP 404 auf eine Canteen-ID ist Exit 2 (unbekannte Mensa). HTTP 401/403 ist Exit 4, alles andere Unerwartete Exit 3.
- Paginierung endet bei leerer Seite oder nach `X-Total-Pages`, falls der Header vorhanden ist. Ein Netzwerkfehler während der Suche ist Exit 3, kein stilles Teilergebnis.
