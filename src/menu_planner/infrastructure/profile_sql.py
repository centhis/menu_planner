from __future__ import annotations

from menu_planner.application.profile_persistence import (
    ProfileVersionedRecordRepository,
)
from menu_planner.infrastructure.safe_commit_sql import (
    SqlConnection,
    SqlVersionedRecordRepository,
)


class SqlProfileVersionedRecordRepository(ProfileVersionedRecordRepository):
    def __init__(self, connection: SqlConnection) -> None:
        super().__init__(SqlVersionedRecordRepository(connection))
