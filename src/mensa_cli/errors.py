"""Fehlerklassen mit festem Exit-Code und nächstem Schritt."""

from __future__ import annotations


class MensaError(Exception):
    """Basisfehler für alle erwartbaren Fehler."""

    exit_code = 3

    def __init__(
        self,
        message: str,
        next_step: str | None = None,
        extra: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.next_step = next_step
        self.extra = extra or {}

    def as_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "error": self.message,
            "exit_code": self.exit_code,
        }
        if self.next_step:
            data["next"] = self.next_step
        data.update(self.extra)
        return data


class UsageError(MensaError):
    """Ungültige Eingabe oder mehrdeutiger Name."""

    exit_code = 2


class ConfigError(MensaError):
    """Lokale Konfiguration oder lokaler Schreibfehler."""

    exit_code = 1


class SourceError(MensaError):
    """Netzwerk-, HTTP- oder Parserfehler der Datenquelle."""

    exit_code = 3


class AuthError(MensaError):
    """Die Quelle verlangt Login oder Zustimmung."""

    exit_code = 4

    def __init__(
        self,
        message: str,
        next_step: str | None = None,
        extra: dict[str, object] | None = None,
    ) -> None:
        super().__init__(
            message,
            next_step
            or "mensa kennt keinen Login; später erneut versuchen oder OpenMensa informieren.",
            extra,
        )
