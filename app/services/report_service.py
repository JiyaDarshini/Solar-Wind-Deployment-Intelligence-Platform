"""
Resource assessment report generation (feeds Module 13: Reports & Export
System later, but the report *object* is produced here at the end of the
Milestone 2 pipeline per the Week 3&4 task list: "Generate resource
assessment reports").

Reports are persisted to MongoDB (the "Secondary Database" from the tech
stack) since they're semi-structured documents, while structured site/
project data stays in PostgreSQL+PostGIS.
"""
import logging
from datetime import datetime
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import get_settings
from app.models.environmental import (
    EnvironmentalProfile,
    ResourceAssessmentReport,
    SiteLocation,
    SolarMetrics,
    WindMetrics,
)

logger = logging.getLogger(__name__)
settings = get_settings()


class ReportService:
    def __init__(self):
        self._client = AsyncIOMotorClient(settings.MONGO_URI)
        self._db = self._client[settings.MONGO_DB_NAME]
        self._collection = self._db["resource_assessment_reports"]

    async def build_report(
        self,
        site: SiteLocation,
        profile: EnvironmentalProfile,
        solar_metrics: Optional[SolarMetrics] = None,
        wind_metrics: Optional[WindMetrics] = None,
    ) -> ResourceAssessmentReport:
        report = ResourceAssessmentReport(
            site=site,
            environmental_profile=profile,
            solar_metrics=solar_metrics,
            wind_metrics=wind_metrics,
            generated_at=datetime.utcnow(),
        )
        await self._persist(report)
        return report

    async def _persist(self, report: ResourceAssessmentReport) -> None:
        try:
            doc = report.model_dump(mode="json")
            await self._collection.update_one(
                {"site.site_id": report.site.site_id},
                {"$set": doc},
                upsert=True,
            )
        except Exception as exc:  # noqa: BLE001 - persistence must never crash the API response
            logger.error("Failed to persist resource assessment report: %s", exc)

    async def get_report(self, site_id: str) -> Optional[dict]:
        return await self._collection.find_one({"site.site_id": site_id}, {"_id": 0})

    async def list_reports(self, limit: int = 50) -> list[dict]:
        cursor = self._collection.find({}, {"_id": 0}).sort("generated_at", -1).limit(limit)
        return [doc async for doc in cursor]


_report_service_singleton: Optional[ReportService] = None


def get_report_service() -> ReportService:
    global _report_service_singleton
    if _report_service_singleton is None:
        _report_service_singleton = ReportService()
    return _report_service_singleton
