# Anforderungen: mensa-cli

## Zweck

`mensa` (Repo `smlfg/mensa-cli`) zeigt den Speiseplan deutscher Mensen im Terminal über die offene [OpenMensa-API v2](https://openmensa.org/api/v2). Standard-Mensa ist Heilbronn, Mensa Bildungscampus/Europaplatz (ID 277). Das Tool löst `smlfg/mensa-agent` (imensa-Notifier) ab: statt Benachrichtigungen liefert es den Plan lesbar auf Abruf. Kein Login, keine schreibenden Web-Aktionen; die einzige lokale Änderung ist die Standard-Mensa in `~/.config/mensa-cli/config.json`.

## Nutzer-Aufgaben

Abgeleitet aus den UX-Sitzungen in `docs/UX.md` (jede Aufgabe hat dort eine abtippbare Sitzung):

1. **Speiseplan heute anzeigen** – `mensa heute` ohne weiteren Namen, mit Kategorie, Hinweisen und allen drei Preisen (Studierende / Bedienstete / Gäste).
2. **Mensen nach Stadt oder Namen suchen** – `mensa suche Heilbronn`; die API hat keine Namenssuche, das Tool lädt die Canteen-Liste seitenweise und filtert lokal.
3. **Plan für eine bestimmte Mensa mit Filtern** – `mensa heute Bildungscampus --vegan` u. ä.; Filter `--vegetarisch`, `--vegan`, `--max-preis`, `--rolle` greifen clientseitig auf Kategorie, Name und Hinweisen.
4. **Mehrere Treffer auflösen** – zu unscharfer Name führt im TTY zu einer nummerierten Auswahl; ohne TTY Liste + Usage-Fehler statt geratener ID.
5. **Standard-Mensa speichern** – `mensa standard Bildungscampus` schreibt die Auswahl lokal; danach funktionieren `mensa heute`, `mensa morgen`, `mensa woche`, `mensa tag` und `mensa gericht` ohne Namen.
6. **Weitere Tage und Gerichte** – `mensa morgen`, `mensa woche`, `mensa tag DATUM|WOCHENTAG`, `mensa gericht STICHWORT` (durchsucht die kommenden Tage).
7. **Geschlossene Tage lesbar melden** – kein Fehler, Exit 0, klare Meldung.

## Nachfrage

- Quelle: `./scratch/ref/NEXT20.md` (Nachfrage-Check der täglichen CLI-Routine, demand-first-gate).
- Datum: 30.10.2026.
- Ergebnis: **GO** (Platz 3). Kein vergleichbares CLI/MCP für OpenMensa gefunden (Belege: gh-Suche, Glama, modelcontextprotocol/servers-Issues, Web/Reddit). Eigenbedarf HHN; 0 Server-Request-Issues in modelcontextprotocol/servers.

## Datenquelle

- OpenMensa-API v2, Basis-URL `https://openmensa.org/api/v2` (Doku: https://docs.openmensa.org/api/v2/).
- Nur lesende GET-Requests: `/canteens` (seitenweise), `/canteens/{id}`, `/canteens/{id}/days`, `/canteens/{id}/days/{datum}`, `/canteens/{id}/days/{datum}/meals`.
- Keine Authentifizierung. Basis-URL über `MENSA_BASE_URL` überschreibbar (Fake-Server in Tests).
- Live erkundet am 30.10.2026; Fixtures unter `tests/fixtures/ux/` sind gekürzte Ausschnitte dieser Antworten.

## Grenzen

- **Inoffizielles Tool**: ohne Beziehung zu OpenMensa oder den Betreiberinnen der Mensen; Datenqualität und Veröffentlichungszeitpunkt liegen beim OpenMensa-Projekt.
- **Nur lesend live getestet**: alle Live-Schritte der Erkundung waren GET-Requests auf öffentliche Seiten; es gibt keine schreibende Aktion und keinen Login.
- Pläne erscheinen erst, wenn sie veröffentlicht werden; „kein Plan“ und „geschlossene“ sind bei fehlendem `/days`-Eintrag nicht unterscheidbar und werden lesbar gemeldet.
- Preise und Gerichte sind Momentaufnahmen; das Tool schreibt nichts zurück und ändert nichts auf dem Server.
- Die Canteen-Liste wird lokal gecacht (`~/.cache/mensa-cli`); Suchtreffer können bis zum Ablauf der Cache-TTL veralten.

## Nicht-Ziele

- Keine Benachrichtigungen (z. B. „X ist heute vegan“) – war Aufgabe von `mensa-agent`; für spätere Iterationen vorgesehen, nicht in diesem Schritt.
- Kein Login, keine Konten, keine schreibenden Requests, keine Bestellungen.
- Keine Pflicht-Optionen, keine IDs in der Bedienung – immer Namen/Suchbegriffe positional.
