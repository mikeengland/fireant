from .query_builder import (
    QueryBuilder,
)
from ..sql_transformer import (
    make_slicer_query,
)


class DataSetSubQueryBuilder(QueryBuilder):
    """
    Slicer sub-queries consist of dimensions, filters, and orders by.
    """

    def __init__(self, dataset):
        super(DataSetSubQueryBuilder, self).__init__(dataset, dataset.table)

    @property
    def sql(self, alias=None):
        """
        Serialize this query builder to a Pypika/SQL query that is meant to be used as a sub-query.

        :param alias: an alias. Defaults to the query builder's table name.
        :return: a Pypika's Query subclass instance.
        """
        query = make_slicer_query(database=self.dataset.database,
                                  base_table=self.table,
                                  joins=self.dataset.joins,
                                  dimensions=self._dimensions,
                                  filters=self._filters) \
            .limit(self._limit) \
            .offset(self._offset)

        return query.as_(alias or self.table._table_name)

    def __str__(self):
        return str(self.sql)

    def __repr__(self):
        return ".".join(["slicer", "data"]
                        + ["dimension({})".format(repr(dimension))
                           for dimension in self._dimensions]
                        + ["filter({}{})".format(repr(f),
                                                 ', apply_filter_to_totals=True' if apply_filter_to_totals else '')
                           for f, apply_filter_to_totals in zip(self._filters, self._apply_filter_to_totals)]
                        + ["orderby({}, {})".format(definition.alias,
                                                    orientation)
                           for (definition, orientation) in self._orders])
