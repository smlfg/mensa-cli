# mensa

Speiseplan deutscher Mensen im Terminal über die offene [OpenMensa-API v2](https://openmensa.org/api/v2). Standard-Mensa ist Heilbronn, Mensa Bildungscampus/Europaplatz (ID 277). Kein Login, keine schreibenden Requests.

## Schnellstart

```bash
pipx install git+https://github.com/smlfg/mensa-cli
mensa heute
mensa suche Heilbronn
mensa heute Bildungscampus --vegan
mensa morgen Heilbronn
mensa standard Bildungscampus
```

`mensa heute` zeigt den Speiseplan der Standard-Mensa für heute, mit Kategorie, Hinweisen und den Preisen für Studierende, Bedienstete und Gäste. `mensa suche Heilbronn` findet Mensen nach Stadt oder Name. `mensa heute Bildungscampus --vegan` filtert den Plan clientseitig. `mensa morgen Heilbronn` fragt bei mehreren Treffern im Terminal nach einer Nummer. `mensa standard Bildungscampus` speichert die Auswahl lokal in `~/.config/mensa-cli/config.json`.

## Befehle

```bash
mensa heute                          # Plan der Standard-Mensa für heute
mensa heute Bildungscampus --vegan   # nur vegane Gerichte
mensa morgen                         # Plan für morgen
mensa woche                          # Montag bis Sonntag
mensa tag 2026-11-01                 # einzelner Tag, auch "morgen" oder "montag"
mensa suche Heilbronn                # Mensen nach Stadt oder Name
mensa gericht Pasta                  # kommende 7 Tage nach Gericht durchsuchen
mensa standard Bildungscampus        # Standard-Mensa speichern
```

Filter: `--vegetarisch`, `--vegan`, `--max-preis 3,00`, `--rolle studierende|bedienstete|gaeste`. Die Filter gelten für `heute`, `morgen`, `woche`, `tag` und `gericht`.

Ein geschlossener Tag ist kein Fehler: Das Tool meldet ihn lesbar und endet mit Exit 0. Mehrere Mensa-Treffer werden im Terminal als nummerierte Auswahl angeboten; ohne Terminal gibt es die Liste und Exit 2 statt einer geratenen ID.

`--json` liefert genau ein JSON-Objekt, auch bei Fehlern. Ohne TTY (Pipe, Agent) ist JSON die Vorgabe.

## Konfiguration

| Einstellung | Pfad / Vorgabe |
|---|---|
| Standard-Mensa | `~/.config/mensa-cli/config.json` (Datei 0600) |
| Cache der Canteen-Liste | `~/.cache/mensa-cli/canteens.json`, TTL 24 Stunden |
| API-Basis | `https://openmensa.org/api/v2`, überschreibbar mit `MENSA_BASE_URL` |
| Datum für Tests | `MENSA_HEUTE=JJJJ-MM-TT` überschreibt „heute“ (nur Test/Sitzungen) |

Ohne gespeicherte Standard-Mensa gilt Heilbronn, Mensa Bildungscampus/Europaplatz (ID 277).

## Exit-Codes

| Code | Bedeutung |
|---|---|
| 0 | Erfolg, auch geschlossener Tag oder keine Treffer |
| 1 | Sonstiger Fehler, z. B. korrupte Config |
| 2 | Usage: unbekanntes Kommando, ungültiges Datum, unbekannter oder mehrdeutiger Name ohne TTY |
| 3 | Netzwerk oder Quelle: Timeout, HTTP 5xx, kaputtes JSON |
| 4 | Quelle verlangt Login/Zustimmung (bei `mensa` derzeit nicht verwendet) |

Die vollständige Schnittstelle steht in [INTERFACE.md](INTERFACE.md), Anforderungen in [ANFORDERUNGEN.md](ANFORDERUNGEN.md), die UX-Spezifikation in [docs/UX.md](docs/UX.md).

## Hinweis

`mensa` ist ein inoffizielles Tool ohne Beziehung zu OpenMensa oder den Betreiberinnen der Mensen. Die Daten stammen aus der OpenMensa-API; Verfügbarkeit, Vollständigkeit und Aktualität liegen beim OpenMensa-Projekt. Alle Live-Zugriffe sind lesende GET-Requests.

## Lizenz

MIT, Copyright smlfg. Siehe [LICENSE](LICENSE).
