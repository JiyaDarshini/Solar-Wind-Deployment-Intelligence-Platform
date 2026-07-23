"""
Module 4: Geographic Intelligence Engine - GIS processing workflows

Computes infrastructure proximity (roads, transmission lines, substations,
urban areas, protected zones, water bodies, agricultural land) around a
site using OpenStreetMap (Overpass API) + GeoPandas/Shapely for the
geometry math.
"""
import logging
from typing import Optional

import httpx
from pydantic import BaseModel
from shapely.geometry import Point
from shapely.ops import nearest_points
import geopandas as gpd

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Overpass "way"/"node" tag filters per feature type we care about
OSM_QUERIES = {
    "roads": '["highway"]',
    "transmission_lines": '["power"="line"]',
    "substations": '["power"="substation"]',
    "urban_areas": '["landuse"="residential"]',
    "protected_zones": '["boundary"="protected_area"]',
    "water_bodies": '["natural"="water"]',
    "agricultural_land": '["landuse"="farmland"]',
}


class ProximityResult(BaseModel):
    feature: str
    distance_km: Optional[float]
    found: bool


class GISProcessingService:
    def __init__(self):
        self._client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self._client.aclose()

    async def _overpass_query(self, feature_type: str, lat: float, lon: float, radius_m: int) -> gpd.GeoDataFrame:
        tag_filter = OSM_QUERIES[feature_type]
        ql = f"""
        [out:json][timeout:25];
        (
          node{tag_filter}(around:{radius_m},{lat},{lon});
          way{tag_filter}(around:{radius_m},{lat},{lon});
        );
        out center;
        """
        try:
            resp = await self._client.post(settings.OSM_OVERPASS_URL, data={"data": ql})
            resp.raise_for_status()
            elements = resp.json().get("elements", [])
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Overpass query failed for %s: %s", feature_type, exc)
            elements = []

        points = []
        for el in elements:
            if el["type"] == "node":
                points.append(Point(el["lon"], el["lat"]))
            elif "center" in el:
                points.append(Point(el["center"]["lon"], el["center"]["lat"]))

        if not points:
            return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
        return gpd.GeoDataFrame(geometry=points, crs="EPSG:4326")

    @staticmethod
    def _haversine_km(p1: Point, p2: Point) -> float:
        import math
        lon1, lat1, lon2, lat2 = map(math.radians, [p1.x, p1.y, p2.x, p2.y])
        dlon, dlat = lon2 - lon1, lat2 - lat1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        return 2 * 6371 * math.asin(math.sqrt(a))

    async def nearest_feature_distance(
        self, feature_type: str, latitude: float, longitude: float, search_radius_m: int = 20000
    ) -> ProximityResult:
        site_point = Point(longitude, latitude)
        gdf = await self._overpass_query(feature_type, latitude, longitude, search_radius_m)

        if gdf.empty:
            return ProximityResult(feature=feature_type, distance_km=None, found=False)

        nearest_geom = min(gdf.geometry, key=lambda g: site_point.distance(g))
        _, nearest_pt = nearest_points(site_point, nearest_geom)
        distance_km = round(self._haversine_km(site_point, nearest_pt), 3)
        return ProximityResult(feature=feature_type, distance_km=distance_km, found=True)

    async def infrastructure_proximity_report(self, latitude: float, longitude: float) -> dict[str, ProximityResult]:
        import asyncio

        results = await asyncio.gather(
            *[self.nearest_feature_distance(feat, latitude, longitude) for feat in OSM_QUERIES]
        )
        return {r.feature: r for r in results}

    @staticmethod
    def accessibility_score(proximity: dict[str, ProximityResult]) -> float:
        """0-100 score rewarding closeness to grid infrastructure/roads
        and penalizing overlap risk with protected zones / water bodies."""
        score = 100.0
        weights_km_decay = {
            "roads": 5.0,
            "transmission_lines": 8.0,
            "substations": 10.0,
        }
        penalties_if_close = {
            "protected_zones": 3.0,
            "water_bodies": 1.0,
            "urban_areas": 2.0,
        }

        for feature, weight in weights_km_decay.items():
            r = proximity.get(feature)
            if not r or not r.found or r.distance_km is None:
                score -= weight  # unknown/absent infra nearby -> deduct
                continue
            score -= min(weight, r.distance_km * (weight / 10))

        for feature, penalty_per_km_inverse in penalties_if_close.items():
            r = proximity.get(feature)
            if r and r.found and r.distance_km is not None and r.distance_km < 1.0:
                score -= penalty_per_km_inverse * (1.0 - r.distance_km)

        return round(max(0.0, min(100.0, score)), 2)


_gis_service_singleton: Optional[GISProcessingService] = None


def get_gis_service() -> GISProcessingService:
    global _gis_service_singleton
    if _gis_service_singleton is None:
        _gis_service_singleton = GISProcessingService()
    return _gis_service_singleton
