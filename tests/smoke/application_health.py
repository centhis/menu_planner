from __future__ import annotations

from menu_planner.application.health import health_status, readiness_status


class PassingDatabaseProbe:
    def ping(self) -> None:
        return None


def main() -> None:
    health = health_status("menu-planner-smoke").as_dict()
    readiness = readiness_status(
        "menu-planner-smoke",
        PassingDatabaseProbe(),
        PassingDatabaseProbe(),
        PassingDatabaseProbe(),
    ).as_dict()

    if health != {"status": "ok", "service": "menu-planner-smoke"}:
        raise SystemExit(f"unexpected health payload: {health}")

    if readiness != {
        "status": "ready",
        "service": "menu-planner-smoke",
        "database": "available",
        "migrations": "current",
        "hermes": "available",
    }:
        raise SystemExit(f"unexpected readiness payload: {readiness}")

    print("application health logic ok")


if __name__ == "__main__":
    main()
