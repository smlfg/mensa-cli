# Projektunabhängige Test-Bausteine

## harness/
Aus smlfg/ilias-cli übernommen, enthält nichts ILIAS-Spezifisches:
- `sitecustomize.py`: Netzwerk-Sandbox. Über `PYTHONPATH` in den Subprozess des Tools laden, dann sind nur Verbindungen zu localhost erlaubt und jeder andere Versuch wird protokolliert.
- `leak_check.py`: Sucht ein Geheimnis (roh, URL- und Base64-kodiert) in Ausgaben und Dateibäumen.

## Später
Contract-Tests, die aus Learnings mit `status: offen` entstehen (z. B. „Login-Erfolg braucht Beweis“ als generischer Test gegen einen Fake-Server).

## UX-Gate

`ux_check.py` prüft ein Repo gegen die UX-Spezifikation in `docs/UX.md`
(Format: `scratch/FORMAT.md`). Es nutzt `ux_spec.py`, `fake_server.py` und
`ux_session.py`; nur Standardbibliothek.

```bash
python tests/harness/ux_check.py <repo_dir> [--venv DIR] [--report FILE]
python tests/harness/ux_check.py <repo_dir> --spec-only
python tests/harness/ux_check.py tests/harness/selftest/good_cli --venv scratch/tmp/ux-venv
pytest -q tests/harness
```

- `UX00`: Mit `ux-routes`/`ux-formsteps` muss während der Sitzungen mindestens ein Request am Fake-Server ankommen (und keiner an einen fremden Host gehen), sonst wirkt `base_url_env` nicht.
- `UX01`: `docs/UX.md` fehlt/ungültig, kein `ux-meta`, weniger als drei `ux-session` oder schreibende Sitzung und `ux-formsteps` passen nicht zusammen.
- `UX02`: Credential-Env-Variablen im Quellcode oder in `meta.credential_env`, aber `<tool> --help` kennt kein Unterkommando `login`.
- `UX03`: `<tool> --help`, `<tool> --version` und `<tool> <sub> --help` für alle gefundenen Unterkommandos enden mit Exit 0.
- `UX04`: Keine Pflicht-Option (`--x WERT` außerhalb `[...]`, bei click `[required]`) in der Subkommando-Usage, außer sie steht in `meta.required_options_ok`.
- `UX05`: Kein JSON am Terminalanfang und kein Traceback in den pty-Sitzungen; zusätzlich `login` + Strg+D ohne Traceback.
- `UX06`: README-Schnellstart (Überschrift in den ersten 40 Zeilen) ohne `#`/`$ `-Zeilen und Platzhalter, mit passender Installationszeile und allen Tool-Befehlen als `$ `-Zeile in einer `ux-session`.
- `UX07`: Schreibende Aktionen fragen im TTY nach `[j/N]`; kein formstep ohne `before_confirm` vor der Bestätigung.
- `UX08`: Alle `ux-formsteps` werden mit allen `sends`-Feldern in Reihenfolge gesendet (nutzt dieselbe Logik wie `ux_session.py`).

Exit-Codes: `0` = kein FAIL (SKIP erlaubt), `1` = mindestens ein FAIL,
`2` = Aufruffehler. `--spec-only` prüft nur `UX01` sowie die statischen Teile
von `UX06` und `UX07` und installiert nichts.

In ein neues Repo kopiert man `tests/harness/` komplett (inklusive
`ux_spec.py`, `fake_server.py`, `ux_session.py`, `ux_check.py`,
`sitecustomize.py` und `selftest/`) und ruft `ux_check.py` dort mit
`docs/UX.md` als Eingabe auf.
