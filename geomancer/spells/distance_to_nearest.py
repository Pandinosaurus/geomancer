# -*- coding: utf-8 -*-

# Import modules
from sqlalchemy import func, literal_column
from sqlalchemy.sql import select

from .base import Spell


class DistanceToNearest(Spell):
    """Obtain the distance to the nearest Point-of-Interest or geographic feature"""

    def __init__(self, on, within=10 * 1000, **kwargs):
        """Spell constructor

        Parameters
        ----------
        on : str
            Feature class to compare upon
        within : float, optional
            Look for values within a particular range. Its value is in meters,
            the default is :code:`10,000` meters.
        """
        super(DistanceToNearest, self).__init__(**kwargs)
        self.on = on
        self.within = within

    def query(self, source, target):
        # Get all POIs of fclass `on`
        pois = select(
            [source.c.osm_id, source.c.WKT], source.c.fclass == self.on
        ).cte("pois")
        # Compute the distance from `column` to each POI within given distance
        distance = func.ST_Distance(
            func.ST_GeogFromText(target.c[self.column]), pois.c.WKT
        )
        pairs = (
            select(
                [target, distance.label(self.feature_name)],
                distance < self.within,
            )
            .select_from(pois)
            .cte("pairs")
        )
        # Partition results to get the smallest distance (nearest POI)
        query = select(
            [
                pairs,
                func.row_number()
                .over(
                    partition_by=pairs.c["__index_level_0__"],
                    order_by=pairs.c[self.feature_name].asc(),
                )
                .label("row_number"),
            ]
        ).select_from(pairs)
        query = select(
            [literal_column("* EXCEPT (row_number)")],
            query.c["row_number"] == 1,
        )
        return query
