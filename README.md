# cli-mcp-template
Project template for CLIs and MCP servers with the shared test suite

## Schritt 0: UX-Spec zuerst

Der komplette Ablauf steht in [agent-learnings/WORKFLOW.md](https://github.com/smlfg/agent-learnings/blob/main/WORKFLOW.md).

1. Vor jeder Codezeile `docs/UX.md` ausfüllen (Vorlage liegt hier): die 3 wichtigsten Nutzer-Aufgaben als abtippbare Terminal-Sitzungen (pipx-Installation, `<tool> login`, Suche per Name, schreibende Aktion bis zur letzten Seite mit `[j/N]`), dazu alle live erkundeten Formularschritte und Fixtures unter `tests/fixtures/ux/`.
2. Spec prüfen: `python3 tests/harness/ux_spec.py docs/UX.md`
3. Gate nach dem Bau (beide müssen grün sein, sonst ist der Build nicht fertig):
   - `python3 tests/harness/ux_check.py .` (UX-Lint UX01–UX08)
   - `python3 tests/harness/ux_session.py .` (spielt die Sitzungen im Pseudo-Terminal gegen einen Fake-Server durch und prüft, dass ALLE Formularschritte gesendet werden)

`tests/harness/` wird unverändert aus agent-learnings übernommen.

## Pflichtregel: Bedienbarkeit für Menschen

Jede CLI muss für Menschen bedienbar sein: `login`-Kommando statt nur Env, Namen statt IDs, interaktive Bestätigung im TTY, `--confirm` nur für Agenten, README-Schnellstart.

- `login` fragt im Terminal interaktiv (Passwort per getpass) und speichert im Schlüsselbund oder in einer Config-Datei mit 0600; dazu `logout` und `whoami`/`status` ohne Passwort-Ausgabe. Env-Variablen überschreiben die Config (für Agenten).
- Namen/Freitext positional (`tool book volleyball`, `tool search fahrrad`); mehrere Treffer → nummerierte Auswahl im TTY, ohne TTY Liste + Exit Usage.
- Schreibende Aktionen: im TTY „… verbindlich? [j/N]“; `--confirm`/`--yes` nur für Agenten; ohne TTY und ohne Flag kein Request.
- Terminal-Ausgabe lesbar; JSON mit `--json` oder wenn stdout kein Terminal ist.
- Fehler nennen den nächsten Schritt, keine Tracebacks bei EOF/Strg+C/fehlender optionaler Abhängigkeit.
- README beginnt mit „Schnellstart“: `pipx install git+https://github.com/smlfg/<repo>`, Login, ein typischer Befehl.

### Pflicht-QA-Prüfpunkt „Bedienbarkeit für Menschen“

1. Frisch per `pipx install git+…` installieren, Befehl direkt im PATH aufrufen.
2. Haupt-Use-Case nur mit `--help` im Pseudo-Terminal (`script -qc "…" /dev/null`) durchspielen: `login` interaktiv, Suche per Name, Bestätigungsfrage mit „N“ → nichts gesendet.
3. Ohne Login: Fehlermeldung nennt `tool login`.
4. FAIL, wenn eine Kernaktion nur über Env-Variablen, interne IDs oder `--confirm` erreichbar ist.
