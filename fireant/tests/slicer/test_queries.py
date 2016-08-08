# coding: utf-8
import unittest
from collections import OrderedDict
from datetime import date

from pypika import Tables, functions as fn, JoinType
# TODO need to remove Vertica dependency
from fireant.database.vertica import Round
from fireant.slicer.queries import QueryManager


class QueryTests(unittest.TestCase):
    dao = QueryManager()
    maxDiff = None

    test_table, test_join1, test_join2 = Tables('test_table', 'test_join1', 'test_join2')


class ExampleTests(QueryTests):
    def test_full_example(self):
        """
        This is an example using several features of the slicer.  It demonstrates usage of metrics, dimensions, filters,
        references and also joining metrics from additional tables.

        The _build_query function takes a dictionary parameter that expresses all of the options of the slicer aside
        from Operations which are done in a post-processing step.

        Many of the fields are defined as a dict.  In the examples and other tests an OrderedDict is used in many places
        so that the field order is maintained for the assertions.  In a real example, a regular dict can be used.

        The fields in the dictionary are as follows:

        :param 'table':
            The primary table to query data from.  This is the table used for the FROM clause in the query.
        :param 'joins':
            A list or tuple of tuples.  This lists the tables that need to be joined in the query and the criterion to
            use to join them.  The inner tuples must contain two elements, the first element is the table to join and
            the second element is a criterion to join the tables with.
        :param 'metrics':
            A dict containing the SELECT clause.  The values can be strings (as a short cut for a column of the primary
            table), a field instance, or an expression containing functions, arithmetic, or anything else supported by
            pypika.
        :param 'dimensions':
            A dict containing the INDEX of the query.  These fields will be included in the SELECT clause, the GROUP BY
            clause, and the ORDER BY clause.  For comparisons, they are also used to join the nested query.
        :param 'filters':
            A list containing criterion expressions for the WHERE clause.  Multiple filters will be combined with an
            'AND' operator.
        :param 'references':
            A dict containing comparison operators.  The keys of this dict must match a supported comparison operation.
            The value of the key must match the key from the dimensions table.  The dimension must also be of the
            supported type, for example 'yoy' requires a DATE type dimension.
        :param 'rollup':
            A list of dimensions to rollup, or provide the totals across groups.  When multiple dimensions are included,
            rollup works from the last to the first dimension, providing the totals across the dimensions in a tree
            structure.

        See pypika documentation for more examples of query expressions: http://pypika.readthedocs.io/en/latest/
        """
        query = self.dao._build_query(
            table=self.test_table,
            joins=[
                (self.test_join1, self.test_table.join1_id == self.test_join1.id, JoinType.left),
                (self.test_join2, self.test_table.join2_id == self.test_join2.id, JoinType.outer),
            ],
            metrics=OrderedDict([
                # Examples using a field of a table
                ('foo', fn.Sum(self.test_table.foo)),

                # Examples using a field of a table
                ('bar', fn.Avg(self.test_join1.bar)),

                # Example using functions and Arithmetic
                ('ratio', fn.Sum(self.test_table.numerator) / fn.Sum(self.test_table.denominator)),

                # Example using functions and Arithmetic
                ('ratio', fn.Sum(self.test_table.numerator) / fn.Sum(self.test_table.denominator)),
            ]),
            dimensions=OrderedDict([
                # Example of using a continuous datetime dimension, where the values are rounded up to the nearest day
                ('dt', Round(self.test_table.dt, 'DD')),

                # Example of using a categorical dimension from a joined table
                ('fiz', self.test_join2.fiz),
            ]),
            mfilters=[
                fn.Sum(self.test_join2.buz) > 100
            ],
            dfilters=[
                # Example of filtering the query to a date range
                self.test_table.dt[date(2016, 1, 1):date(2016, 12, 31)],

                # Example of filtering the query to certain categories
                self.test_join2.fiz.isin(['a', 'b', 'c']),
            ],
            references=OrderedDict([
                # Example of adding a Week-over-Week comparison to the query
                ('wow', 'dt')
            ]),
            rollup=[],
        )

        self.assertEqual('SELECT '
                         # Dimensions
                         'ROUND("t0"."dt",\'DD\') "dt",'
                         '"t2"."fiz" "fiz",'
                         # Metrics
                         'SUM("t0"."foo") "foo",'
                         'AVG("t1"."bar") "bar",'
                         'SUM("t0"."numerator")/SUM("t0"."denominator") "ratio",'
                         # Comparison Metrics
                         '"t3"."dt" "dt_wow",'
                         '"t3"."fiz" "fiz_wow",'
                         '"t3"."foo" "foo_wow",'
                         '"t3"."bar" "bar_wow",'
                         '"t3"."ratio" "ratio_wow" '
                         'FROM "test_table" "t0" '
                         'JOIN "test_join1" "t1" ON "t0"."join1_id"="t1"."id" '
                         'OUTER JOIN "test_join2" "t2" ON "t0"."join2_id"="t2"."id" '
                         # Comparison join query
                         'JOIN ('
                         'SELECT '
                         'ROUND("t0"."dt",\'DD\') "dt",'
                         '"t2"."fiz" "fiz",'
                         'SUM("t0"."foo") "foo",'
                         'AVG("t1"."bar") "bar",'
                         'SUM("t0"."numerator")/SUM("t0"."denominator") "ratio" '
                         'FROM "test_table" "t0" '
                         'JOIN "test_join1" "t1" ON "t0"."join1_id"="t1"."id" '
                         'OUTER JOIN "test_join2" "t2" ON "t0"."join2_id"="t2"."id" '
                         'GROUP BY ROUND("t0"."dt",\'DD\'),"t2"."fiz"'
                         ') "t3" '
                         'ON ROUND("t0"."dt",\'DD\')="t3"."dt"-INTERVAL 1 WEEK AND "t2"."fiz"="t3"."fiz" '
                         # Filters
                         'WHERE "t0"."dt" BETWEEN \'2016-01-01\' AND \'2016-12-31\' '
                         'AND "t2"."fiz" IN (\'a\',\'b\',\'c\') '
                         'GROUP BY ROUND("t0"."dt",\'DD\'),"t2"."fiz" '
                         'HAVING SUM("t2"."buz")>100 '
                         'ORDER BY ROUND("t0"."dt",\'DD\'),"t2"."fiz"', str(query))


class MetricsTests(QueryTests):
    def test_metrics(self):
        query = self.dao._build_query(
            table=self.test_table,
            joins=[],
            metrics=OrderedDict([
                ('clicks', fn.Sum(self.test_table.clicks)),
                ('roi', fn.Sum(self.test_table.revenue) / fn.Sum(self.test_table.cost)),
            ]),
            dimensions={},
            mfilters=[],
            dfilters=[],
            references={},
            rollup=[],
        )

        self.assertEqual('SELECT SUM("clicks") "clicks",SUM("revenue")/SUM("cost") "roi" '
                         'FROM "test_table"', str(query))

    def test_metrics_dimensions(self):
        query = self.dao._build_query(
            table=self.test_table,
            joins=[],
            metrics=OrderedDict([
                ('clicks', fn.Sum(self.test_table.clicks)),
                ('roi', fn.Sum(self.test_table.revenue) / fn.Sum(self.test_table.cost)),
            ]),
            dimensions=OrderedDict([
                ('device_type', self.test_table.device_type)
            ]),
            mfilters=[],
            dfilters=[],
            references={},
            rollup=[],
        )

        self.assertEqual(
            'SELECT "device_type" "device_type",SUM("clicks") "clicks",SUM("revenue")/SUM("cost") "roi" '
            'FROM "test_table" '
            'GROUP BY "device_type" '
            'ORDER BY "device_type"', str(query))

    def test_metrics_filters(self):
        query = self.dao._build_query(
            table=self.test_table,
            joins=[],
            metrics=OrderedDict([
                ('clicks', fn.Sum(self.test_table.clicks)),
                ('roi', fn.Sum(self.test_table.revenue) / fn.Sum(self.test_table.cost)),
            ]),
            dimensions=OrderedDict([
                ('device_type', self.test_table.device_type)
            ]),
            mfilters=[],
            dfilters=[
                self.test_table.dt[date(2000, 1, 1):date(2001, 1, 1)]
            ],
            references={},
            rollup=[],
        )

        self.assertEqual(
            'SELECT "device_type" "device_type",SUM("clicks") "clicks",SUM("revenue")/SUM("cost") "roi" '
            'FROM "test_table" '
            'WHERE "dt" BETWEEN \'2000-01-01\' AND \'2001-01-01\' '
            'GROUP BY "device_type" '
            'ORDER BY "device_type"', str(query))

    def test_metrics_dimensions_filters(self):
        query = self.dao._build_query(
            table=self.test_table,
            joins=[],
            metrics=OrderedDict([
                ('clicks', fn.Sum(self.test_table.clicks)),
                ('roi', (fn.Sum(self.test_table.revenue) / fn.Sum(self.test_table.cost))),
            ]),
            dimensions=OrderedDict([
                ('device_type', self.test_table.device_type),
                ('locale', self.test_table.locale),
            ]),
            mfilters=[],
            dfilters=[
                self.test_table.locale.isin(['US', 'CA', 'UK'])
            ],
            references={},
            rollup=[],
        )

        self.assertEqual(
            'SELECT '
            '"device_type" "device_type",'
            '"locale" "locale",'
            'SUM("clicks") "clicks",'
            'SUM("revenue")/SUM("cost") "roi" '
            'FROM "test_table" '
            'WHERE "locale" IN (\'US\',\'CA\',\'UK\') '
            'GROUP BY "device_type","locale" '
            'ORDER BY "device_type","locale"', str(query))


class DimensionTests(QueryTests):
    def _test_rounded_timeseries(self, increment):
        rounded_dt = Round(self.test_table.dt, increment)

        return self.dao._build_query(
            table=self.test_table,
            joins=[],
            metrics=OrderedDict([
                ('clicks', fn.Sum(self.test_table.clicks)),
                ('roi', fn.Sum(self.test_table.revenue) / fn.Sum(self.test_table.cost)),
            ]),
            dimensions=OrderedDict([
                ('dt', rounded_dt)
            ]),
            mfilters=[],
            dfilters=[],
            references={},
            rollup=[],
        )

    def test_timeseries_hour(self):
        query = self._test_rounded_timeseries('HH')

        self.assertEqual(
            'SELECT ROUND("dt",\'HH\') "dt",SUM("clicks") "clicks",SUM("revenue")/SUM("cost") "roi" '
            'FROM "test_table" '
            'GROUP BY ROUND("dt",\'HH\') '
            'ORDER BY ROUND("dt",\'HH\')', str(query))

    def test_timeseries_DD(self):
        query = self._test_rounded_timeseries('DD')

        self.assertEqual(
            'SELECT ROUND("dt",\'DD\') "dt",SUM("clicks") "clicks",SUM("revenue")/SUM("cost") "roi" '
            'FROM "test_table" '
            'GROUP BY ROUND("dt",\'DD\') '
            'ORDER BY ROUND("dt",\'DD\')', str(query))

    def test_timeseries_week(self):
        query = self._test_rounded_timeseries('WW')

        self.assertEqual(
            'SELECT ROUND("dt",\'WW\') "dt",SUM("clicks") "clicks",SUM("revenue")/SUM("cost") "roi" '
            'FROM "test_table" '
            'GROUP BY ROUND("dt",\'WW\') '
            'ORDER BY ROUND("dt",\'WW\')', str(query))

    def test_timeseries_month(self):
        query = self._test_rounded_timeseries('MONTH')

        self.assertEqual(
            'SELECT ROUND("dt",\'MONTH\') "dt",SUM("clicks") "clicks",SUM("revenue")/SUM("cost") "roi" '
            'FROM "test_table" '
            'GROUP BY ROUND("dt",\'MONTH\') '
            'ORDER BY ROUND("dt",\'MONTH\')', str(query))

    def test_timeseries_quarter(self):
        query = self._test_rounded_timeseries('Q')

        self.assertEqual(
            'SELECT ROUND("dt",\'Q\') "dt",SUM("clicks") "clicks",SUM("revenue")/SUM("cost") "roi" '
            'FROM "test_table" '
            'GROUP BY ROUND("dt",\'Q\') '
            'ORDER BY ROUND("dt",\'Q\')', str(query))

    def test_timeseries_year(self):
        query = self._test_rounded_timeseries('YEAR')

        self.assertEqual(
            'SELECT ROUND("dt",\'YEAR\') "dt",SUM("clicks") "clicks",SUM("revenue")/SUM("cost") "roi" '
            'FROM "test_table" '
            'GROUP BY ROUND("dt",\'YEAR\') '
            'ORDER BY ROUND("dt",\'YEAR\')', str(query))

    def test_multidimension_categorical(self):
        query = self.dao._build_query(
            table=self.test_table,
            joins=[],
            metrics=OrderedDict([
                ('clicks', fn.Sum(self.test_table.clicks)),
                ('roi', fn.Sum(self.test_table.revenue) / fn.Sum(self.test_table.cost)),
            ]),
            dimensions=OrderedDict([
                ('device_type', self.test_table.device_type),
                ('locale', self.test_table.locale),
            ]),
            mfilters=[],
            dfilters=[],
            references={},
            rollup=[],
        )

        self.assertEqual(
            'SELECT "device_type" "device_type","locale" "locale",'
            'SUM("clicks") "clicks",SUM("revenue")/SUM("cost") "roi" '
            'FROM "test_table" '
            'GROUP BY "device_type","locale" '
            'ORDER BY "device_type","locale"', str(query))

    def test_multidimension_timeseries_categorical(self):
        rounded_dt = Round(self.test_table.dt, 'DD')
        device_type = self.test_table.device_type

        query = self.dao._build_query(
            table=self.test_table,
            joins=[],
            metrics=OrderedDict([
                ('clicks', fn.Sum(self.test_table.clicks)),
                ('roi', fn.Sum(self.test_table.revenue) / fn.Sum(self.test_table.cost)),
            ]),
            dimensions=OrderedDict([
                ('dt', rounded_dt),
                ('device_type', device_type),
            ]),
            mfilters=[],
            dfilters=[],
            references={},
            rollup=[],
        )

        self.assertEqual(
            'SELECT ROUND("dt",\'DD\') "dt","device_type" "device_type",'
            'SUM("clicks") "clicks",SUM("revenue")/SUM("cost") "roi" '
            'FROM "test_table" '
            'GROUP BY ROUND("dt",\'DD\'),"device_type" '
            'ORDER BY ROUND("dt",\'DD\'),"device_type"', str(query))

    def test_metrics_with_joins(self):
        rounded_dt = Round(self.test_table.dt, 'DD')
        locale = self.test_table.locale

        query = self.dao._build_query(
            table=self.test_table,
            joins=[
                (self.test_join1, self.test_table.hotel_id == self.test_join1.hotel_id, JoinType.left),
            ],
            metrics=OrderedDict([
                ('clicks', fn.Sum(self.test_table.clicks)),
                ('roi', fn.Sum(self.test_table.revenue) / fn.Sum(self.test_table.cost)),
                ('hotel_name', self.test_join1.hotel_name),
                ('hotel_address', self.test_join1.address),
                ('city_id', self.test_join1.ctid),
                ('city_name', self.test_join1.city_name),
            ]),
            dimensions=OrderedDict([
                ('dt', rounded_dt),
                ('locale', locale),
            ]),
            mfilters=[],
            dfilters=[],
            references={},
            rollup=[],
        )

        self.assertEqual('SELECT '
                         'ROUND("t0"."dt",\'DD\') "dt","t0"."locale" "locale",'
                         'SUM("t0"."clicks") "clicks",SUM("t0"."revenue")/SUM("t0"."cost") "roi",'
                         '"t1"."hotel_name" "hotel_name","t1"."address" "hotel_address",'
                         '"t1"."ctid" "city_id","t1"."city_name" "city_name" '
                         'FROM "test_table" "t0" '
                         'JOIN "test_join1" "t1" ON "t0"."hotel_id"="t1"."hotel_id" '
                         'GROUP BY ROUND("t0"."dt",\'DD\'),"t0"."locale" '
                         'ORDER BY ROUND("t0"."dt",\'DD\'),"t0"."locale"', str(query))


class FilterTests(QueryTests):
    def test_single_dimension_filter(self):
        query = self.dao._build_query(
            table=self.test_table,
            joins=[],
            metrics=OrderedDict([
                ('clicks', fn.Sum(self.test_table.clicks)),
                ('roi', (fn.Sum(self.test_table.revenue) / fn.Sum(self.test_table.cost))),
            ]),
            dimensions=OrderedDict([
                ('locale', self.test_table.locale),
            ]),
            mfilters=[],
            dfilters=[
                self.test_table.locale.isin(['US', 'CA', 'UK'])
            ],
            references={},
            rollup=[],
        )

        self.assertEqual('SELECT '
                         '"locale" "locale",'
                         'SUM("clicks") "clicks",'
                         'SUM("revenue")/SUM("cost") "roi" '
                         'FROM "test_table" '
                         'WHERE "locale" IN (\'US\',\'CA\',\'UK\') '
                         'GROUP BY "locale" '
                         'ORDER BY "locale"', str(query))

    def test_multi_dimension_filter(self):
        query = self.dao._build_query(
            table=self.test_table,
            joins=[],
            metrics=OrderedDict([
                ('clicks', fn.Sum(self.test_table.clicks)),
                ('roi', (fn.Sum(self.test_table.revenue) / fn.Sum(self.test_table.cost))),
            ]),
            dimensions=OrderedDict([
                ('locale', self.test_table.locale),
            ]),
            mfilters=[],
            dfilters=[
                self.test_table.locale.isin(['US', 'CA', 'UK']),
                self.test_table.device_type == 'desktop',
                self.test_table.dt > date(2016, 1, 1),
            ],
            references={},
            rollup=[],
        )

        self.assertEqual('SELECT '
                         '"locale" "locale",'
                         'SUM("clicks") "clicks",'
                         'SUM("revenue")/SUM("cost") "roi" '
                         'FROM "test_table" '
                         'WHERE "locale" IN (\'US\',\'CA\',\'UK\') '
                         'AND "device_type"=\'desktop\' '
                         'AND "dt">\'2016-01-01\' '
                         'GROUP BY "locale" '
                         'ORDER BY "locale"', str(query))

    def test_single_metric_filter(self):
        query = self.dao._build_query(
            table=self.test_table,
            joins=[],
            metrics=OrderedDict([
                ('clicks', fn.Sum(self.test_table.clicks)),
                ('roi', (fn.Sum(self.test_table.revenue) / fn.Sum(self.test_table.cost))),
            ]),
            dimensions=OrderedDict([
                ('locale', self.test_table.locale),
            ]),
            mfilters=[
                fn.Sum(self.test_table.clicks) > 100
            ],
            dfilters=[],
            references={},
            rollup=[],
        )

        self.assertEqual('SELECT '
                         '"locale" "locale",'
                         'SUM("clicks") "clicks",'
                         'SUM("revenue")/SUM("cost") "roi" '
                         'FROM "test_table" '
                         'GROUP BY "locale" '
                         'HAVING SUM("clicks")>100 '
                         'ORDER BY "locale"', str(query))

    def test_multi_metric_filter(self):
        query = self.dao._build_query(
            table=self.test_table,
            joins=[],
            metrics=OrderedDict([
                ('clicks', fn.Sum(self.test_table.clicks)),
                ('roi', (fn.Sum(self.test_table.revenue) / fn.Sum(self.test_table.cost))),
            ]),
            dimensions=OrderedDict([
                ('locale', self.test_table.locale),
            ]),
            mfilters=[
                fn.Sum(self.test_table.clicks) > 100,
                (fn.Sum(self.test_table.revenue) / fn.Sum(self.test_table.cost)) < 0.7,
                fn.Sum(self.test_table.conversions) >= 10,
            ],
            dfilters=[],
            references={},
            rollup=[],
        )

        self.assertEqual('SELECT '
                         '"locale" "locale",'
                         'SUM("clicks") "clicks",'
                         'SUM("revenue")/SUM("cost") "roi" '
                         'FROM "test_table" '
                         'GROUP BY "locale" '
                         'HAVING SUM("clicks")>100 '
                         'AND SUM("revenue")/SUM("cost")<0.7 '
                         'AND SUM("conversions")>=10 '
                         'ORDER BY "locale"', str(query))


class ComparisonTests(QueryTests):
    def _get_compare_query(self, compare_type):
        rounded_dt = Round(self.test_table.dt, 'DD')
        device_type = self.test_table.device_type
        query = self.dao._build_query(
            table=self.test_table,
            joins=[],
            metrics=OrderedDict([
                ('clicks', fn.Sum(self.test_table.clicks)),
                ('roi', fn.Sum(self.test_table.revenue) / fn.Sum(self.test_table.cost)),
            ]),
            dimensions=OrderedDict([
                ('dt', rounded_dt),
                ('device_type', device_type),
            ]),
            mfilters=[],
            dfilters=[
                self.test_table.dt[date(2000, 1, 1):date(2000, 3, 1)]
            ],
            references=OrderedDict([
                (compare_type, 'dt')
            ]),
            rollup=[],
        )
        return query

    def test_metrics_dimensions_filters_references__yoy(self):
        query = self._get_compare_query('yoy')

        self.assertEqual('SELECT '
                         'ROUND("t0"."dt",\'DD\') "dt",'
                         '"t0"."device_type" "device_type",'
                         'SUM("t0"."clicks") "clicks",'
                         'SUM("t0"."revenue")/SUM("t0"."cost") "roi",'
                         '"t1"."dt" "dt_yoy",'
                         '"t1"."device_type" "device_type_yoy",'
                         '"t1"."clicks" "clicks_yoy",'
                         '"t1"."roi" "roi_yoy" '
                         'FROM "test_table" "t0" '
                         'JOIN ('
                         'SELECT '
                         'ROUND("dt",\'DD\') "dt","device_type" "device_type",'
                         'SUM("clicks") "clicks",SUM("revenue")/SUM("cost") "roi" '
                         'FROM "test_table" GROUP BY ROUND("dt",\'DD\'),"device_type"'
                         ') "t1" ON ROUND("t0"."dt",\'DD\')="t1"."dt"-INTERVAL 52 WEEK '
                         'AND "t0"."device_type"="t1"."device_type" '
                         'WHERE "t0"."dt" BETWEEN \'2000-01-01\' AND \'2000-03-01\' '
                         'GROUP BY ROUND("t0"."dt",\'DD\'),"t0"."device_type" '
                         'ORDER BY ROUND("t0"."dt",\'DD\'),"t0"."device_type"', str(query))

    def test_metrics_dimensions_filters_references__qoq(self):
        query = self._get_compare_query('qoq')

        self.assertEqual('SELECT '
                         'ROUND("t0"."dt",\'DD\') "dt",'
                         '"t0"."device_type" "device_type",'
                         'SUM("t0"."clicks") "clicks",'
                         'SUM("t0"."revenue")/SUM("t0"."cost") "roi",'
                         '"t1"."dt" "dt_qoq",'
                         '"t1"."device_type" "device_type_qoq",'
                         '"t1"."clicks" "clicks_qoq",'
                         '"t1"."roi" "roi_qoq" '
                         'FROM "test_table" "t0" '
                         'JOIN ('
                         'SELECT '
                         'ROUND("dt",\'DD\') "dt","device_type" "device_type",'
                         'SUM("clicks") "clicks",SUM("revenue")/SUM("cost") "roi" '
                         'FROM "test_table" GROUP BY ROUND("dt",\'DD\'),"device_type"'
                         ') "t1" ON ROUND("t0"."dt",\'DD\')="t1"."dt"-INTERVAL 1 QUARTER '
                         'AND "t0"."device_type"="t1"."device_type" '
                         'WHERE "t0"."dt" BETWEEN \'2000-01-01\' AND \'2000-03-01\' '
                         'GROUP BY ROUND("t0"."dt",\'DD\'),"t0"."device_type" '
                         'ORDER BY ROUND("t0"."dt",\'DD\'),"t0"."device_type"', str(query))

    def test_metrics_dimensions_filters_references__mom(self):
        query = self._get_compare_query('mom')

        self.assertEqual('SELECT '
                         'ROUND("t0"."dt",\'DD\') "dt",'
                         '"t0"."device_type" "device_type",'
                         'SUM("t0"."clicks") "clicks",'
                         'SUM("t0"."revenue")/SUM("t0"."cost") "roi",'
                         '"t1"."dt" "dt_mom",'
                         '"t1"."device_type" "device_type_mom",'
                         '"t1"."clicks" "clicks_mom",'
                         '"t1"."roi" "roi_mom" '
                         'FROM "test_table" "t0" '
                         'JOIN ('
                         'SELECT '
                         'ROUND("dt",\'DD\') "dt","device_type" "device_type",'
                         'SUM("clicks") "clicks",SUM("revenue")/SUM("cost") "roi" '
                         'FROM "test_table" GROUP BY ROUND("dt",\'DD\'),"device_type"'
                         ') "t1" ON ROUND("t0"."dt",\'DD\')="t1"."dt"-INTERVAL 4 WEEK '
                         'AND "t0"."device_type"="t1"."device_type" '
                         'WHERE "t0"."dt" BETWEEN \'2000-01-01\' AND \'2000-03-01\' '
                         'GROUP BY ROUND("t0"."dt",\'DD\'),"t0"."device_type" '
                         'ORDER BY ROUND("t0"."dt",\'DD\'),"t0"."device_type"', str(query))

    def test_metrics_dimensions_filters_references__wow(self):
        query = self._get_compare_query('wow')

        self.assertEqual('SELECT '
                         'ROUND("t0"."dt",\'DD\') "dt",'
                         '"t0"."device_type" "device_type",'
                         'SUM("t0"."clicks") "clicks",'
                         'SUM("t0"."revenue")/SUM("t0"."cost") "roi",'
                         '"t1"."dt" "dt_wow",'
                         '"t1"."device_type" "device_type_wow",'
                         '"t1"."clicks" "clicks_wow",'
                         '"t1"."roi" "roi_wow" '
                         'FROM "test_table" "t0" '
                         'JOIN ('
                         'SELECT '
                         'ROUND("dt",\'DD\') "dt","device_type" "device_type",'
                         'SUM("clicks") "clicks",SUM("revenue")/SUM("cost") "roi" '
                         'FROM "test_table" GROUP BY ROUND("dt",\'DD\'),"device_type"'
                         ') "t1" ON ROUND("t0"."dt",\'DD\')="t1"."dt"-INTERVAL 1 WEEK '
                         'AND "t0"."device_type"="t1"."device_type" '
                         'WHERE "t0"."dt" BETWEEN \'2000-01-01\' AND \'2000-03-01\' '
                         'GROUP BY ROUND("t0"."dt",\'DD\'),"t0"."device_type" '
                         'ORDER BY ROUND("t0"."dt",\'DD\'),"t0"."device_type"', str(query))

    def test_metrics_dimensions_filters_references__yoy_d(self):
        query = self._get_compare_query('yoy_d')

        self.assertEqual('SELECT '
                         'ROUND("t0"."dt",\'DD\') "dt",'
                         '"t0"."device_type" "device_type",'
                         'SUM("t0"."clicks") "clicks",'
                         'SUM("t0"."revenue")/SUM("t0"."cost") "roi",'
                         '"t1"."dt" "dt_yoy_d",'
                         '"t1"."device_type" "device_type_yoy_d",'
                         'SUM("t0"."clicks")-"t1"."clicks" "clicks_yoy_d",'
                         'SUM("t0"."revenue")/SUM("t0"."cost")-"t1"."roi" "roi_yoy_d" '
                         'FROM "test_table" "t0" '
                         'JOIN ('
                         'SELECT '
                         'ROUND("dt",\'DD\') "dt","device_type" "device_type",'
                         'SUM("clicks") "clicks",SUM("revenue")/SUM("cost") "roi" '
                         'FROM "test_table" GROUP BY ROUND("dt",\'DD\'),"device_type"'
                         ') "t1" ON ROUND("t0"."dt",\'DD\')="t1"."dt"-INTERVAL 52 WEEK '
                         'AND "t0"."device_type"="t1"."device_type" '
                         'WHERE "t0"."dt" BETWEEN \'2000-01-01\' AND \'2000-03-01\' '
                         'GROUP BY ROUND("t0"."dt",\'DD\'),"t0"."device_type" '
                         'ORDER BY ROUND("t0"."dt",\'DD\'),"t0"."device_type"', str(query))

    def test_metrics_dimensions_filters_references__qoq_d(self):
        query = self._get_compare_query('qoq_d')

        self.assertEqual('SELECT '
                         'ROUND("t0"."dt",\'DD\') "dt",'
                         '"t0"."device_type" "device_type",'
                         'SUM("t0"."clicks") "clicks",'
                         'SUM("t0"."revenue")/SUM("t0"."cost") "roi",'
                         '"t1"."dt" "dt_qoq_d",'
                         '"t1"."device_type" "device_type_qoq_d",'
                         'SUM("t0"."clicks")-"t1"."clicks" "clicks_qoq_d",'
                         'SUM("t0"."revenue")/SUM("t0"."cost")-"t1"."roi" "roi_qoq_d" '
                         'FROM "test_table" "t0" '
                         'JOIN ('
                         'SELECT '
                         'ROUND("dt",\'DD\') "dt","device_type" "device_type",'
                         'SUM("clicks") "clicks",SUM("revenue")/SUM("cost") "roi" '
                         'FROM "test_table" GROUP BY ROUND("dt",\'DD\'),"device_type"'
                         ') "t1" ON ROUND("t0"."dt",\'DD\')="t1"."dt"-INTERVAL 1 QUARTER '
                         'AND "t0"."device_type"="t1"."device_type" '
                         'WHERE "t0"."dt" BETWEEN \'2000-01-01\' AND \'2000-03-01\' '
                         'GROUP BY ROUND("t0"."dt",\'DD\'),"t0"."device_type" '
                         'ORDER BY ROUND("t0"."dt",\'DD\'),"t0"."device_type"', str(query))

    def test_metrics_dimensions_filters_references__mom_d(self):
        query = self._get_compare_query('mom_d')

        self.assertEqual('SELECT '
                         'ROUND("t0"."dt",\'DD\') "dt",'
                         '"t0"."device_type" "device_type",'
                         'SUM("t0"."clicks") "clicks",'
                         'SUM("t0"."revenue")/SUM("t0"."cost") "roi",'
                         '"t1"."dt" "dt_mom_d",'
                         '"t1"."device_type" "device_type_mom_d",'
                         'SUM("t0"."clicks")-"t1"."clicks" "clicks_mom_d",'
                         'SUM("t0"."revenue")/SUM("t0"."cost")-"t1"."roi" "roi_mom_d" '
                         'FROM "test_table" "t0" '
                         'JOIN ('
                         'SELECT '
                         'ROUND("dt",\'DD\') "dt","device_type" "device_type",'
                         'SUM("clicks") "clicks",SUM("revenue")/SUM("cost") "roi" '
                         'FROM "test_table" GROUP BY ROUND("dt",\'DD\'),"device_type"'
                         ') "t1" ON ROUND("t0"."dt",\'DD\')="t1"."dt"-INTERVAL 4 WEEK '
                         'AND "t0"."device_type"="t1"."device_type" '
                         'WHERE "t0"."dt" BETWEEN \'2000-01-01\' AND \'2000-03-01\' '
                         'GROUP BY ROUND("t0"."dt",\'DD\'),"t0"."device_type" '
                         'ORDER BY ROUND("t0"."dt",\'DD\'),"t0"."device_type"', str(query))

    def test_metrics_dimensions_filters_references__wow_d(self):
        query = self._get_compare_query('wow_d')

        self.assertEqual('SELECT '
                         'ROUND("t0"."dt",\'DD\') "dt",'
                         '"t0"."device_type" "device_type",'
                         'SUM("t0"."clicks") "clicks",'
                         'SUM("t0"."revenue")/SUM("t0"."cost") "roi",'
                         '"t1"."dt" "dt_wow_d",'
                         '"t1"."device_type" "device_type_wow_d",'
                         'SUM("t0"."clicks")-"t1"."clicks" "clicks_wow_d",'
                         'SUM("t0"."revenue")/SUM("t0"."cost")-"t1"."roi" "roi_wow_d" '
                         'FROM "test_table" "t0" '
                         'JOIN ('
                         'SELECT '
                         'ROUND("dt",\'DD\') "dt","device_type" "device_type",'
                         'SUM("clicks") "clicks",SUM("revenue")/SUM("cost") "roi" '
                         'FROM "test_table" GROUP BY ROUND("dt",\'DD\'),"device_type"'
                         ') "t1" ON ROUND("t0"."dt",\'DD\')="t1"."dt"-INTERVAL 1 WEEK '
                         'AND "t0"."device_type"="t1"."device_type" '
                         'WHERE "t0"."dt" BETWEEN \'2000-01-01\' AND \'2000-03-01\' '
                         'GROUP BY ROUND("t0"."dt",\'DD\'),"t0"."device_type" '
                         'ORDER BY ROUND("t0"."dt",\'DD\'),"t0"."device_type"', str(query))

    def test_metrics_dimensions_filters_references__yoy_p(self):
        query = self._get_compare_query('yoy_p')

        self.assertEqual('SELECT '
                         'ROUND("t0"."dt",\'DD\') "dt",'
                         '"t0"."device_type" "device_type",'
                         'SUM("t0"."clicks") "clicks",'
                         'SUM("t0"."revenue")/SUM("t0"."cost") "roi",'
                         '"t1"."dt" "dt_yoy_p",'
                         '"t1"."device_type" "device_type_yoy_p",'
                         '(SUM("t0"."clicks")-"t1"."clicks")/"t1"."clicks" "clicks_yoy_p",'
                         '(SUM("t0"."revenue")/SUM("t0"."cost")-"t1"."roi")/"t1"."roi" "roi_yoy_p" '
                         'FROM "test_table" "t0" '
                         'JOIN ('
                         'SELECT '
                         'ROUND("dt",\'DD\') "dt","device_type" "device_type",'
                         'SUM("clicks") "clicks",SUM("revenue")/SUM("cost") "roi" '
                         'FROM "test_table" GROUP BY ROUND("dt",\'DD\'),"device_type"'
                         ') "t1" ON ROUND("t0"."dt",\'DD\')="t1"."dt"-INTERVAL 52 WEEK '
                         'AND "t0"."device_type"="t1"."device_type" '
                         'WHERE "t0"."dt" BETWEEN \'2000-01-01\' AND \'2000-03-01\' '
                         'GROUP BY ROUND("t0"."dt",\'DD\'),"t0"."device_type" '
                         'ORDER BY ROUND("t0"."dt",\'DD\'),"t0"."device_type"', str(query))

    def test_metrics_dimensions_filters_references__qoq_p(self):
        query = self._get_compare_query('qoq_p')

        self.assertEqual('SELECT '
                         'ROUND("t0"."dt",\'DD\') "dt",'
                         '"t0"."device_type" "device_type",'
                         'SUM("t0"."clicks") "clicks",'
                         'SUM("t0"."revenue")/SUM("t0"."cost") "roi",'
                         '"t1"."dt" "dt_qoq_p",'
                         '"t1"."device_type" "device_type_qoq_p",'
                         '(SUM("t0"."clicks")-"t1"."clicks")/"t1"."clicks" "clicks_qoq_p",'
                         '(SUM("t0"."revenue")/SUM("t0"."cost")-"t1"."roi")/"t1"."roi" "roi_qoq_p" '
                         'FROM "test_table" "t0" '
                         'JOIN ('
                         'SELECT '
                         'ROUND("dt",\'DD\') "dt","device_type" "device_type",'
                         'SUM("clicks") "clicks",SUM("revenue")/SUM("cost") "roi" '
                         'FROM "test_table" GROUP BY ROUND("dt",\'DD\'),"device_type"'
                         ') "t1" ON ROUND("t0"."dt",\'DD\')="t1"."dt"-INTERVAL 1 QUARTER '
                         'AND "t0"."device_type"="t1"."device_type" '
                         'WHERE "t0"."dt" BETWEEN \'2000-01-01\' AND \'2000-03-01\' '
                         'GROUP BY ROUND("t0"."dt",\'DD\'),"t0"."device_type" '
                         'ORDER BY ROUND("t0"."dt",\'DD\'),"t0"."device_type"', str(query))

    def test_metrics_dimensions_filters_references__mom_p(self):
        query = self._get_compare_query('mom_p')

        self.assertEqual('SELECT '
                         'ROUND("t0"."dt",\'DD\') "dt",'
                         '"t0"."device_type" "device_type",'
                         'SUM("t0"."clicks") "clicks",'
                         'SUM("t0"."revenue")/SUM("t0"."cost") "roi",'
                         '"t1"."dt" "dt_mom_p",'
                         '"t1"."device_type" "device_type_mom_p",'
                         '(SUM("t0"."clicks")-"t1"."clicks")/"t1"."clicks" "clicks_mom_p",'
                         '(SUM("t0"."revenue")/SUM("t0"."cost")-"t1"."roi")/"t1"."roi" "roi_mom_p" '
                         'FROM "test_table" "t0" '
                         'JOIN ('
                         'SELECT '
                         'ROUND("dt",\'DD\') "dt","device_type" "device_type",'
                         'SUM("clicks") "clicks",SUM("revenue")/SUM("cost") "roi" '
                         'FROM "test_table" GROUP BY ROUND("dt",\'DD\'),"device_type"'
                         ') "t1" ON ROUND("t0"."dt",\'DD\')="t1"."dt"-INTERVAL 4 WEEK '
                         'AND "t0"."device_type"="t1"."device_type" '
                         'WHERE "t0"."dt" BETWEEN \'2000-01-01\' AND \'2000-03-01\' '
                         'GROUP BY ROUND("t0"."dt",\'DD\'),"t0"."device_type" '
                         'ORDER BY ROUND("t0"."dt",\'DD\'),"t0"."device_type"', str(query))

    def test_metrics_dimensions_filters_references__wow_p(self):
        query = self._get_compare_query('wow_p')

        self.assertEqual('SELECT '
                         'ROUND("t0"."dt",\'DD\') "dt",'
                         '"t0"."device_type" "device_type",'
                         'SUM("t0"."clicks") "clicks",'
                         'SUM("t0"."revenue")/SUM("t0"."cost") "roi",'
                         '"t1"."dt" "dt_wow_p",'
                         '"t1"."device_type" "device_type_wow_p",'
                         '(SUM("t0"."clicks")-"t1"."clicks")/"t1"."clicks" "clicks_wow_p",'
                         '(SUM("t0"."revenue")/SUM("t0"."cost")-"t1"."roi")/"t1"."roi" "roi_wow_p" '
                         'FROM "test_table" "t0" '
                         'JOIN ('
                         'SELECT '
                         'ROUND("dt",\'DD\') "dt","device_type" "device_type",'
                         'SUM("clicks") "clicks",SUM("revenue")/SUM("cost") "roi" '
                         'FROM "test_table" GROUP BY ROUND("dt",\'DD\'),"device_type"'
                         ') "t1" ON ROUND("t0"."dt",\'DD\')="t1"."dt"-INTERVAL 1 WEEK '
                         'AND "t0"."device_type"="t1"."device_type" '
                         'WHERE "t0"."dt" BETWEEN \'2000-01-01\' AND \'2000-03-01\' '
                         'GROUP BY ROUND("t0"."dt",\'DD\'),"t0"."device_type" '
                         'ORDER BY ROUND("t0"."dt",\'DD\'),"t0"."device_type"', str(query))


class TotalsQueryTests(QueryTests):
    def test_add_rollup_one_dimension(self):
        rounded_dt = Round(self.test_table.dt, 'DD')
        locale = self.test_table.locale

        query = self.dao._build_query(
            table=self.test_table,
            joins=[],
            metrics=OrderedDict([
                ('clicks', fn.Sum(self.test_table.clicks)),
                ('roi', fn.Sum(self.test_table.revenue) / fn.Sum(self.test_table.cost)),
            ]),
            dimensions=OrderedDict([
                ('dt', rounded_dt),
                ('locale', locale),
            ]),
            mfilters=[],
            dfilters=[],
            references={},
            rollup=['locale'],
        )

        self.assertEqual('SELECT '
                         'ROUND("dt",\'DD\') "dt","locale" "locale",'
                         'SUM("clicks") "clicks",SUM("revenue")/SUM("cost") "roi" '
                         'FROM "test_table" '
                         'GROUP BY ROUND("dt",\'DD\'),ROLLUP("locale") '
                         'ORDER BY ROUND("dt",\'DD\'),"locale"', str(query))

    def test_add_rollup_two_dimensions(self):
        rounded_dt = Round(self.test_table.dt, 'DD')
        locale = self.test_table.locale
        device_type = self.test_table.device_type

        query = self.dao._build_query(
            table=self.test_table,
            joins=[],
            metrics=OrderedDict([
                ('clicks', fn.Sum(self.test_table.clicks)),
                ('roi', fn.Sum(self.test_table.revenue) / fn.Sum(self.test_table.cost)),
            ]),
            dimensions=OrderedDict([
                ('dt', rounded_dt),
                ('locale', locale),
                ('device_type', device_type),
            ]),
            mfilters=[],
            dfilters=[],
            references={},
            rollup=['locale', 'device_type'],
        )

        self.assertEqual('SELECT '
                         'ROUND("dt",\'DD\') "dt",'
                         '"locale" "locale",'
                         '"device_type" "device_type",'
                         'SUM("clicks") "clicks",SUM("revenue")/SUM("cost") "roi" '
                         'FROM "test_table" '
                         'GROUP BY ROUND("dt",\'DD\'),ROLLUP("locale","device_type") '
                         'ORDER BY ROUND("dt",\'DD\'),"locale","device_type"', str(query))

    def test_add_rollup_two_dimensions_partial(self):
        rounded_dt = Round(self.test_table.dt, 'DD')
        locale = self.test_table.locale
        device_type = self.test_table.device_type

        query = self.dao._build_query(
            table=self.test_table,
            joins=[],
            metrics=OrderedDict([
                ('clicks', fn.Sum(self.test_table.clicks)),
                ('roi', fn.Sum(self.test_table.revenue) / fn.Sum(self.test_table.cost)),
            ]),
            dimensions=OrderedDict([
                ('dt', rounded_dt),
                ('locale', locale),
                ('device_type', device_type),
            ]),
            mfilters=[],
            dfilters=[],
            references={},
            rollup=['locale'],
        )
        self.assertEqual('SELECT '
                         'ROUND("dt",\'DD\') "dt",'
                         '"device_type" "device_type",'
                         '"locale" "locale",'  # Order is changed, rollup dims move to end
                         'SUM("clicks") "clicks",SUM("revenue")/SUM("cost") "roi" '
                         'FROM "test_table" '
                         'GROUP BY ROUND("dt",\'DD\'),"device_type",ROLLUP("locale") '
                         'ORDER BY ROUND("dt",\'DD\'),"device_type","locale"', str(query))
