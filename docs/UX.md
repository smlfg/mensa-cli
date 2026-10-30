# UX-Spec: mensa

Diese Datei beschreibt die wichtigsten Aufgaben eines Menschen mit `mensa`. Das Tool liest ausschließlich den öffentlichen Speiseplan der OpenMensa-API v2. Es gibt keinen Login und keine schreibende Web-Aktion; die einzige lokale Änderung ist die Standard-Mensa in `~/.config/mensa-cli/config.json`.

Alle Befehle sind so abtippbar, wie sie im Terminal eingegeben werden. Die Fixtures unter `tests/fixtures/ux/` sind gekürzte Ausschnitte echter Live-Antworten vom 30.10.2026.

## Meta

Der Befehlsname im PATH ist `mensa`. Die Basis-URL lässt sich für Tests und den Fake-Server über `MENSA_BASE_URL` überschreiben. Es gibt keine Zugangsdaten und deshalb kein `login`-Kommando.

```ux-meta
{"tool": "mensa",
 "install": "pipx install git+https://github.com/smlfg/mensa-cli",
 "base_url_env": "MENSA_BASE_URL"}
```

## Sitzungen

### Installation und erster Speiseplan

Nach der Installation zeigt `mensa tag 2026-11-02` ohne weiteren Namen den Speiseplan der Standard-Mensa (Heilbronn, ID 277). Kategorien und alle drei Preise stehen direkt in der Ausgabe, damit ein Mensch ohne Nachschlagen entscheiden kann.

```ux-session
$ pipx install git+https://github.com/smlfg/mensa-cli
$ mensa tag 2026-11-02
< Mensa: Heilbronn, Mensa Bildungscampus/Europaplatz (277)
< Datum: Montag, 02.11.2026
< Preise: Studierende / Bedienstete / Gäste (EUR)
<   [Dessert] Pudding Creme mit Streusel — 0,90 / 1,40 / 2,00 EUR
<   [Vegan] Gemüsebolognese mit hausgemachter Pasta — 0,99 / 1,35 / 2,00 EUR
! exit 0
```

### Mensen nach Stadt oder Namen suchen

Der Suchbegriff ist positional. Die API hat keine Namenssuche; das Tool lädt die Canteen-Liste seitenweise und filtert lokal. Die Ausgabe nennt Name, ID und Adresse.

```ux-session
$ mensa suche Heilbronn
< Mensen gefunden (2):
<   1) Heilbronn, Mensa Bildungscampus/Europaplatz (277) – Bildungscampus 8, 74076 Heilbronn
<   2) Heilbronn, Mensa Sontheim (278) – Max-Planck-Straße 39, 74081 Heilbronn
! exit 0
```

### Tag für eine Mensa per Name und Filter

Der Mensa-Name ist positional. `--vegan` filtert clientseitig über Kategorie, Name und Hinweise. Die Preise bleiben für alle Rollen sichtbar.

```ux-session
$ mensa tag 2026-11-02 Bildungscampus --vegan
< Mensa: Heilbronn, Mensa Bildungscampus/Europaplatz (277)
< Datum: Montag, 02.11.2026
< Filter: vegan
<   [Dessert vegan] Mandelpudding mit Granola — 0,90 / 1,40 / 2,00 EUR
<   [Foodtruck] Currywurst vegan mit fruchtiger Tomatensauce und Brot — 2,60 / 3,10 / 4,70 EUR
<   [Vegan] Gemüsebolognese mit hausgemachter Pasta — 0,99 / 1,35 / 2,00 EUR
! exit 0
```

### Mehrere Treffer im Terminal auswählen

Ein zu unscharfer Name führt zu einer nummerierten Auswahl. Ohne TTY gibt das Tool die Liste aus und endet mit einem Usage-Fehler, statt eine ID zu erraten.

```ux-session
$ mensa tag 2026-11-02 Heilbronn
< Mehrere Mensen gefunden:
<   1) Heilbronn, Mensa Bildungscampus/Europaplatz (277)
<   2) Heilbronn, Mensa Sontheim (278)
< Auswahl [1-2]:
> 1
< Mensa: Heilbronn, Mensa Bildungscampus/Europaplatz (277)
< Datum: Montag, 02.11.2026
! exit 0
```

### Standard-Mensa speichern

`mensa standard` löst den Namen auf und speichert die Auswahl lokal. Danach funktionieren `mensa heute`, `mensa tag` und `mensa woche` ohne Namen.

```ux-session
$ mensa standard Bildungscampus
< Standard-Mensa gespeichert: Heilbronn, Mensa Bildungscampus/Europaplatz (277)
! exit 0
```

### Geschlossener Tag

Ein geschlossener Tag ist kein Fehler. Das Tool meldet ihn lesbar und endet mit Exit 0.

```ux-session
$ mensa tag 2026-11-01
< Mensa: Heilbronn, Mensa Bildungscampus/Europaplatz (277)
< Datum: Sonntag, 01.11.2026
< Geschlossen – kein Speiseplan veröffentlicht.
! exit 0
```

## Lesende Routen

Alle Requests sind GET. `query_contains` unterscheidet die Seiten der Canteen-Liste. Seite 4 ist leer und beendet die Paginierung. Die Antworten sind JSON.

```ux-routes
[{"method":"GET","path":"/canteens","query_contains":"page=1","response":"tests/fixtures/ux/canteens_page1.json","status":200,"content_type":"application/json; charset=utf-8"},
 {"method":"GET","path":"/canteens","query_contains":"page=2","response":"tests/fixtures/ux/canteens_page2.json","status":200,"content_type":"application/json; charset=utf-8"},
 {"method":"GET","path":"/canteens","query_contains":"page=3","response":"tests/fixtures/ux/canteens_page3.json","status":200,"content_type":"application/json; charset=utf-8"},
 {"method":"GET","path":"/canteens","query_contains":"page=4","response":"tests/fixtures/ux/canteens_page4.json","status":200,"content_type":"application/json; charset=utf-8"},
 {"method":"GET","path":"/canteens/277/days/2026-11-02","response":"tests/fixtures/ux/day_277_2026-11-02.json","status":200,"content_type":"application/json; charset=utf-8"},
 {"method":"GET","path":"/canteens/277/days/2026-11-02/meals","response":"tests/fixtures/ux/meals_277_2026-11-02.json","status":200,"content_type":"application/json; charset=utf-8"},
 {"method":"GET","path":"/canteens/277/days/2026-11-01","response":"tests/fixtures/ux/day_277_2026-11-01.json","status":200,"content_type":"application/json; charset=utf-8"}]
```

## Keine schreibende Aktion

`mensa` verändert keine Daten auf dem Server. Deshalb gibt es weder `ux-formsteps` noch `credential_env` und keine `[j/N]`-Bestätigung. Die einzige lokale Schreibaktion ist die Konfigurationsdatei von `mensa standard`; sie wird mit Rechten 0600 gespeichert und nie ins Repo geschrieben.
