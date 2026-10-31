# QA: mensa

Pflicht-QA nach Workflow-Schritt 6 (find -> file, keine Codeänderung).

- Datum: 2026-10-31
- Tool: `mensa` 0.1.0
- Commit: `f366ffa134e7257024c0d378ef6d3180089b1f09`
- Installation: `pipx install git+https://github.com/smlfg/mensa-cli` in `scratch/pipx`; Protokoll `scratch/qa/pipx-install.log`. Der installierte Commit laut `direct_url.json` ist `f366ffa…`, also identisch mit dem geprüften Stand.
- Aufruf: ausschließlich über `PATH=$PWD/scratch/pipx/bin:$PATH`, nicht aus `scratch/venv`.
- Fake-Server: `tests/harness/fake_server.py` mit den `ux-routes` aus `docs/UX.md`, `MENSA_HEUTE=2026-11-02`.
- Live: nur lesende GET-Requests auf `https://openmensa.org/api/v2`; keine Logins, keine schreibenden Web-Aktionen.
- Temporäre Dateien und Homes: ausschließlich unter `scratch/qa/s5/`.
- UX-Gate und Harness wurden nicht verändert. `pytest` und `ux_check.py --spec-only` sind grün.

## Ergebnis

**59 OK / 59 Prüfungen, 0 FAIL.** (Nachprüfung FAIL 1 nach Fix `4bd6d6a`.)

| # | Prüfung | Befehl | Erwartet | Ergebnis | Beleg (gekürzt) |
|---|---|---|---|---|---|
| 1 | Frische pipx-Installation | `pipx install git+https://github.com/smlfg/mensa-cli` | `mensa` im PATH, Commit = HEAD | OK | `scratch/qa/pipx-install.log`; `direct_url.json` = `f366ffa…` |
| 2 | Version | `mensa --version` | `mensa 0.1.0`, Exit 0 | OK | `scratch/qa/s5/version.txt` |
| 3 | Hilfe Hauptbefehl | `mensa --help` | Exit 0, alle 7 Befehle | OK | `scratch/qa/s5/help-main.txt` |
| 4 | Hilfe aller Unterbefehle | `mensa <befehl> --help` für alle 7 | alle Exit 0 | OK | `scratch/qa/s5/help-subcommands.txt` |
| 5 | README-Schnellstart: heute | `mensa heute` (PTY, Fake) | Text, Standard-Mensa 277, 02.11.2026 | OK | `scratch/qa/s5/1.log` |
| 6 | README-Schnellstart: Suche | `mensa suche Heilbronn` (PTY, Fake) | 2 Treffer | OK | `scratch/qa/s5/2.log` |
| 7 | README-Schnellstart: Filter | `mensa heute Bildungscampus --vegan` (PTY, Fake) | nur vegane Gerichte | OK | `scratch/qa/s5/3.log` |
| 8 | README-Schnellstart: Morgen + Auswahl | `mensa morgen Heilbronn`, Eingabe `1` (PTY, Fake) | nummerierte Auswahl, dann 03.11.2026 | OK | `scratch/qa/s5/4.log` |
| 9 | README-Schnellstart: Standard | `mensa standard Bildungscampus` (PTY, Fake) | Standard gespeichert | OK | `scratch/qa/s5/5.log` |
| 10 | Text statt JSON im TTY | `mensa heute` (PTY) | lesbarer Text, kein JSON | OK | `scratch/qa/s5/1.log` |
| 11 | JSON im TTY | `mensa heute --json` (PTY, Fake) | genau ein JSON-Objekt | OK | `scratch/qa/s5/json-tty.log` |
| 12 | Config-Rechte | nach `mensa standard` | Datei 0600, Verzeichnis 0700 | OK | `scratch/qa/s5/home-live/.config/mensa-cli/` |
| 13 | Live: heute | `mensa heute` | Samstag, 31.10.2026, 6 Gerichte | OK | `scratch/qa/s5/live-heute.log` |
| 14 | Live: Suche | `mensa suche Heilbronn` | 2 Treffer | OK | `scratch/qa/s5/live-suche.log` |
| 15 | Live: Vegan-Filter | `mensa heute Bildungscampus --vegan` | 3 Treffer, alle vegan | OK | `scratch/qa/s5/live-vegan.log` |
| 16 | Live: geschlossener Tag | `mensa morgen` | Sonntag, 01.11.2026, geschlossen, Exit 0 | OK | `scratch/qa/s5/live-morgen.log` |
| 17 | Live: Woche | `mensa woche` | 26.10.–01.11.2026, 7 Tagesabschnitte | OK | `scratch/qa/s5/live-woche.log` |
| 18 | Live: Wochentag | `mensa tag montag` | Montag, 02.11.2026 | OK | `scratch/qa/s5/live-montag.log` |
| 19 | Live: geschlossener Einzeltag | `mensa tag 2026-11-01` | geschlossen, Exit 0 | OK | `scratch/qa/s5/live-tag-closed.log` |
| 20 | Live: Gerichtssuche | `mensa gericht Pasta` | 2 Treffer in den nächsten 7 Tagen | OK | `scratch/qa/s5/live-gericht.log` |
| 21 | Live: Standard speichern und nutzen | `mensa standard Bildungscampus`; `mensa heute` | gespeichert, danach ohne Namen 277 | OK | `scratch/qa/s5/live-standard.log`, `live-heute-nach-standard.log` |
| 22 | Live: Umlaut exakt | `mensa suche Münster` | Treffer, u. a. 48149 Münster | OK | `scratch/qa/s5/live-suche-muenster.log` |
| 23 | Live: ASCII-Tippvariante | `mensa suche munster` | 0 Treffer; laut INTERFACE nur casefold/Teilstring, daher Hinweis | OK (Hinweis) | `scratch/qa/s5/live-suche-munster.log` |
| 24 | Live: leere Suche | `mensa suche xyzzy` | „Keine Mensen gefunden.“, Exit 0 | OK | `scratch/qa/s5/live-suche-xyzzy.log` |
| 25 | Live: Paginierung, späte Seite | `mensa suche Boku` | ID 2077 gefunden (späte Seite) | OK | `scratch/qa/s5/search-boku.json` |
| 26 | Live: Paginierung, alle Seiten | `mensa suche Mensa` | 378 Treffer, nicht nur Seite 1 | OK | `scratch/qa/s5/search-mensa.json` |
| 27 | Live: Datumsauflösung | `mensa tag samstag/sonntag/montag` | 31.10. / 01.11. / 02.11.2026 | OK | `scratch/qa/s5/date-live.out` |
| 28 | Fake: Basisplan | `mensa heute --json` | 9 Gerichte, 02.11.2026, ID 277 | OK | `scratch/qa/s5/json-base.json` |
| 29 | Fake: `--vegan` vollständig | `mensa heute --vegan --json` | 3 Treffer, jeder mit vegan-Merkmal | OK | `scratch/qa/s5/json-vegan.json`, `check_filters.out` |
| 30 | Fake: `--vegetarisch` vollständig | `mensa heute --vegetarisch --json` | 4 Treffer, jeder vegetarisch/vegan | OK | `scratch/qa/s5/json-vegetarisch.json`, `check_filters.out` |
| 31 | Fake: `--max-preis` je Rolle | `--max-preis 1,00` / `1,40 --rolle bedienstete` / `4,00 --rolle gaeste` | 5 / 5 / 6 Treffer, kein Preis über Grenze | OK | `scratch/qa/s5/json-max-*.json`, `check_filters.out` |
| 32 | Fake: kombinierte Filter | `mensa heute --vegan --vegetarisch --json` | identisch mit `--vegan` | OK | `scratch/qa/s5/json-vegan-und-vegetarisch.json`, `check_more_filters.out` |
| 33 | Fake: Filter über mehrere Tage | `woche/tag montag/morgen --vegan --json` | 6 / 3 / 3 Treffer, alle vegan | OK | `scratch/qa/s5/json-woche-vegan.json`, `json-tag-montag-vegan.json`, `json-morgen-vegan.json` |
| 34 | Live: Basisplan als JSON | `mensa heute --json` | 6 Gerichte, 31.10.2026 | OK | `scratch/qa/s5/live-json-base.json` |
| 35 | Live: `--vegan` vollständig | `mensa heute --vegan --json` | 3 Treffer, jeder vegan, vollständig | OK | `scratch/qa/s5/live-json-vegan.json`, `check_live_filters.out` |
| 36 | Live: `--vegetarisch` vollständig | `mensa heute --vegetarisch --json` | 3 Treffer, jeder vegetarisch/vegan | OK | `scratch/qa/s5/live-json-vegetarisch.json`, `check_live_filters.out` |
| 37 | Live: `--max-preis` je Rolle | `1,00` / `1,40 --rolle bedienstete` / `4,00 --rolle gaeste` | 0 / 0 / 1 Treffer, kein Preis über Grenze | OK | `scratch/qa/s5/live-json-max-*.json`, `check_live_filters.out` |
| 38 | Live: Woche mit Filter | `mensa woche --vegan --json` | 18 Treffer über 7 Tage, alle vegan | OK | `scratch/qa/s5/live-json-woche-vegan.json`, `check_live_week.out` |
| 39 | Fake: Gericht + Filter | `mensa gericht Pasta --vegan --json` | 1 Treffer, im 7-Tage-Fenster, Pasta + vegan | OK | `scratch/qa/s5/json-gericht-vegan.json`, `check_filters.out` |
| 40 | Fake: Gericht ohne Treffer | `mensa gericht xyzzy --json` | 0 Treffer, Exit 0 | OK | `scratch/qa/s5/json-gericht-leer.json` |
| 41 | Leerer Filter | `mensa heute Bildungscampus --vegan --max-preis 0,10` | „Keine Gerichte für den Filter.“, Exit 0 | OK | `scratch/qa/s5/empty-filter.log` |
| 42 | Ungültiges Datum | `mensa tag 31.13.2026` | Exit 2, nächster Schritt, kein Traceback | OK | `scratch/qa/s5/err-date-pty.log` |
| 43 | Ungültiges `MENSA_HEUTE` | `MENSA_HEUTE=2026-13-99 mensa heute` | Exit 2, klare Meldung | OK | `scratch/qa/s5/err-heute-pty.log` |
| 44 | Ungültiger Preis | `mensa heute --max-preis abc` | Exit 2, nächster Schritt | OK | `scratch/qa/s5/err-price-pty.log` |
| 45 | Usage-Fehler | `--rolle student`, `mensa foo`, `mensa tag` | jeweils Exit 2, nächster Schritt | OK | `scratch/qa/s5/err-role-pty.log`, `err-command-pty.log`, `err-missing-date-pty.log` |
| 46 | Unbekannter Mensa-Name | `mensa heute xyzzy` | Exit 2, nächster Schritt `mensa suche` | OK | `scratch/qa/s5/err-name-pty.log` |
| 47 | Mehrdeutiger Name ohne TTY | `mensa heute Heilbronn --json` | Liste + JSON-Fehler, Exit 2 | OK | `scratch/qa/s5/err-ambiguous-json.out`, `.err` |
| 48 | Mehrdeutiger Name im TTY | `mensa morgen Heilbronn`, Eingabe `9`, dann `1` | erneute Frage, dann Auswahl | OK | `scratch/qa/s5/tty-invalid.log` |
| 49 | Strg+C bei Auswahl | `mensa morgen Heilbronn`, SIGINT | Exit 1, „Abgebrochen.“, kein Traceback | OK | `scratch/qa/s5/tty-sigint.out` |
| 50 | EOF bei Auswahl | `mensa morgen Heilbronn`, stdin EOF | Exit 2, nächster Schritt, kein Traceback | OK | `scratch/qa/s5/tty-eof.log` |
| 51 | Netzfehler | `MENSA_BASE_URL=http://127.0.0.1:9 mensa heute` | Exit 3, nächster Schritt, kein Traceback | OK | `scratch/qa/s5/err-net-pty.log` |
| 52 | Ungültige Basis-URL | `MENSA_BASE_URL=foo mensa heute` | Exit 3, nächster Schritt | OK | `scratch/qa/s5/err-baseurl-pty.log` |
| 53 | Korrupte Config | kaputtes `config.json`, `mensa heute` | Exit 1, Hinweis auf `mensa standard` | OK | `scratch/qa/s5/err-config.log` |
| 54 | JSON-Fehler bei Usage | `mensa foo --json`, `mensa tag --json`, `--max-preis abc --json` | genau ein JSON-Objekt, Exit 2 | OK | `scratch/qa/s5/err-command-json.out`, `err-missing-date-json.out`, `err-price-json.out` |
| 55 | Unbekannte Canteen-ID in Config | Config `canteen_id: 999999`, `mensa heute` | Exit 2 „unbekannte Mensa“ | OK (nach Fix `4bd6d6a`) | `scratch/qa/s6/unknown-id-live.log`, `unknown-id-live.json` |
| 56 | JSON-Validity | `python3 -m json.tool` über alle frischen JSON-Dateien | alle valide | OK | `scratch/qa/s5/*.json` |
| 57 | Keine Tracebacks | `grep -RIn "Traceback"` über alle Sitzungslogs | keine Treffer | OK | `scratch/qa/s5/`, `scratch/qa/*.log` |
| 58 | Testsuite | `scratch/venv/bin/pytest -q` | grün | OK | `scratch/qa/s6/pytest.txt` (86 passed, nach Fix) |
| 59 | UX-Gate Spec | `python3 tests/harness/ux_check.py . --spec-only` | PASS, Exit 0 | OK | `scratch/qa/s6/ux-spec-only.txt` |

## Nachprüfung FAIL 1 (behoben)

### FAIL 1: Unbekannte Canteen-ID in der Config wird als „kein Plan“ ausgegeben

- Ursprüngliche Reproduktion: `HOME=scratch/qa/s5/home-unknown`, Config `{"canteen_id": 999999, "name": "Unbekannte Mensa"}`, dann `mensa heute` (live und Fake).
- Erwartet laut `INTERFACE.md`: „HTTP 404 auf eine Canteen-ID ist Exit 2 (unbekannte Mensa).“ Eine unbekannte Mensa ist ein Usage-Fehler mit Hinweis auf `mensa suche`.
- Ursprünglich tatsächlich: Exit 0, Ausgabe „Kein Speiseplan veröffentlicht (Datum außerhalb des veröffentlichten Zeitraums).“, JSON `no_plan: true`.
- Beleg vor dem Fix: `scratch/qa/s5/unknown-id-live.log` und `scratch/qa/s5/unknown-id-live.json`; mit Fake-Server identisch in `unknown-id-fake.log` und `unknown-id-fake.json`.
- Einordnung: echter Betriebsfehler, kein False Positive des UX-Gates. Der Harness wurde nicht verändert.
- Fix: `4bd6d6a` prüft beim Auflösen der Config, ob `canteen_id` in der geladenen Canteen-Liste existiert; sonst `UsageError` mit Exit 2 und `mensa suche SUCHBEGRIFF` als nächstem Schritt. Regressionstest: `tests/test_commands.py::test_unbekannte_canteen_id_in_config_ist_usage`.
- Nachprüfung live (pipx-Installation aus dem Repo, `scratch/qa/s6/home-unknown`, `mensa heute`): Exit 2, Meldung „Unbekannte Mensa in der Konfiguration: Unbekannte Mensa (999999).“, nächster Schritt `mensa suche SUCHBEGRIFF`. Beleg: `scratch/qa/s6/unknown-id-live.log` (PTY) und `scratch/qa/s6/unknown-id-live.json`.

## Hinweise (kein FAIL)

- `mensa suche munster` findet „Münster“ nicht, `mensa suche Münster` schon. `INTERFACE.md` sagt nur `casefold` und Teilstring zu, keine Umlaut-Transliteration. Für Menschen wäre `ue`/`u`-Faltung eine Verbesserung, ist aber keine zugesagte Schnittstelle.
- Die argparse-Meldungen für `--rolle`, unbekanntes Kommando und fehlendes `DATUM` sind englisch („invalid choice“, „the following arguments are required“). Sie nennen jeweils den nächsten Schritt und enden ohne Traceback; nur die Sprache ist gemischt.
- Die Kombination `--vegan --vegetarisch` wird korrekt als strengere Vegan-Prüfung behandelt. In der Textkopfzeile erscheint dann nur `Filter: vegan`, was der veganen Semantik entspricht.

## Nicht geprüft / bewusst offen

- Keine schreibenden Aktionen vorhanden; es gab daher keinen Login-, Bestätigungs- oder Formstep-Test.
- Cache-TTL (24 h), nicht schreibbarer Cache und `X-Total-Pages`-Sonderfälle wurden nicht separat provoziert; die normale Paginierung wurde live über späte Seiten geprüft.
