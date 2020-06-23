from unittest import TestCase

from pypika import (
    Table,
    functions as fn,
)

import fireant as f
from fireant.tests.dataset.mocks import test_database

test_table = Table("test")
ds = f.DataSet(
    table=test_table,
    database=test_database,
    fields=[
        f.Field("date", definition=test_table.date, data_type=f.DataType.date),
        f.Field("text", definition=test_table.text, data_type=f.DataType.text),
        f.Field("number", definition=test_table.number, data_type=f.DataType.number),
        f.Field("boolean", definition=test_table.boolean, data_type=f.DataType.boolean),
        f.Field(
            "aggr_number",
            definition=fn.Sum(test_table.number),
            data_type=f.DataType.number,
        ),
    ],
)

# noinspection SqlDialectInspection,SqlNoDataSourceInspection
class ResultSetTests(TestCase):
    def test_no_metric_is_removed_when_result_set_metric_filter_is_present(self):
        queries = (
            ds.query.widget(f.Pandas(ds.fields.aggr_number))
            .filter(f.ResultSet(ds.fields.aggr_number > 10))
            .sql
        )

        self.assertEqual(len(queries), 1)
        self.assertEqual(
            "SELECT "
            "CASE WHEN SUM(\"number\")>10 THEN 'set(SUM(number)>10)' ELSE 'complement(SUM(number)>10)' END \"$set(SUM(number)>10)\","
            'SUM("number") "$aggr_number" '
            'FROM "test"',
            str(queries[0]),
        )

    def test_dimension_is_replaced_by_default_when_result_set_filter_is_present(self):
        queries = (
            ds.query.widget(f.Pandas(ds.fields.aggr_number))
            .dimension(ds.fields.text)
            .filter(f.ResultSet(ds.fields.text == "abc"))
            .sql
        )

        self.assertEqual(len(queries), 1)
        self.assertEqual(
            "SELECT "
            "CASE WHEN \"text\"='abc' THEN 'set(text=''abc'')' ELSE 'complement(text=''abc'')' END \"$text\","
            'SUM("number") "$aggr_number" '
            'FROM "test" '
            "GROUP BY \"$text\" "
            "ORDER BY \"$text\"",
            str(queries[0]),
        )

    def test_dimension_is_replaced_by_default_in_the_target_dimension_place_when_result_set_filter_is_present(
        self,
    ):
        queries = (
            ds.query.widget(f.Pandas(ds.fields.aggr_number))
            .dimension(ds.fields.date)
            .dimension(ds.fields.text)
            .dimension(ds.fields.boolean)
            .filter(f.ResultSet(ds.fields.text == "abc"))
            .sql
        )

        self.assertEqual(len(queries), 1)
        self.assertEqual(
            "SELECT "
            '"date" "$date",'
            "CASE WHEN \"text\"='abc' THEN 'set(text=''abc'')' ELSE 'complement(text=''abc'')' END \"$text\","
            '"boolean" "$boolean",'
            'SUM("number") "$aggr_number" '
            'FROM "test" '
            'GROUP BY "$date","$text","$boolean" '
            'ORDER BY "$date","$text","$boolean"',
            str(queries[0]),
        )

    def test_dimension_with_dimension_modifier_is_replaced_by_default_when_result_set_filter_is_present(
        self,
    ):
        queries = (
            ds.query.widget(f.Pandas(ds.fields.aggr_number))
            .dimension(ds.fields.date)
            .dimension(f.Rollup(ds.fields.boolean))
            .filter(f.ResultSet(ds.fields.boolean == True))
            .sql
        )

        self.assertEqual(len(queries), 2)

        with self.subTest('base query is the same as without totals'):
            self.assertEqual(
                "SELECT "
                '"date" "$date",'
                "CASE WHEN \"boolean\"=true THEN 'set(boolean=true)' ELSE 'complement(boolean=true)' END \"$boolean\","
                'SUM("number") "$aggr_number" '
                'FROM "test" '
                'GROUP BY "$date","$boolean" '
                'ORDER BY "$date","$boolean"',
                str(queries[0]),
            )

        with self.subTest('totals dimension is replaced with _FIREANT_ROLLUP_VALUE_'):
            self.assertEqual(
                "SELECT "
                '"date" "$date",'
                '\'_FIREANT_ROLLUP_VALUE_\' "$boolean",'
                'SUM("number") "$aggr_number" '
                'FROM "test" '
                'GROUP BY "$date","$boolean" '
                'ORDER BY "$date","$boolean"',
                str(queries[1]),
            )

    def test_dimension_is_inserted_before_conditional_dimension_when_result_set_filter_wont_ignore_dimensions(
        self,
    ):
        queries = (
            ds.query.widget(f.Pandas(ds.fields.aggr_number))
            .dimension(ds.fields.text)
            .filter(
                f.ResultSet(
                    ds.fields.text == "abc", will_replace_referenced_dimension=False
                )
            )
            .sql
        )

        self.assertEqual(len(queries), 1)
        self.assertEqual(
            "SELECT "
            "CASE WHEN \"text\"='abc' THEN 'set(text=''abc'')' ELSE 'complement(text=''abc'')' END \"$set(text='abc')\","
            '"text" "$text",'
            'SUM("number") "$aggr_number" '
            'FROM "test" '
            'GROUP BY "$set(text=\'abc\')","$text" '
            'ORDER BY "$set(text=\'abc\')","$text"',
            str(queries[0]),
        )

    def test_dimension_breaks_complement_down_when_result_set_filter_wont_group_complement(
        self,
    ):
        queries = (
            ds.query.widget(f.Pandas(ds.fields.aggr_number))
            .dimension(ds.fields.text)
            .filter(f.ResultSet(ds.fields.text == "abc", will_group_complement=False))
            .sql
        )

        self.assertEqual(len(queries), 1)
        self.assertEqual(
            "SELECT "
            "CASE WHEN \"text\"='abc' THEN 'set(text=''abc'')' ELSE \"text\" END \"$text\","
            'SUM("number") "$aggr_number" '
            'FROM "test" '
            "GROUP BY \"$text\" "
            "ORDER BY \"$text\"",
            str(queries[0]),
        )

    def test_dimension_is_inserted_in_dimensions_even_when_not_selected(self):
        queries = (
            ds.query.widget(f.Pandas(ds.fields.aggr_number))
            .filter(f.ResultSet(ds.fields.text == "abc"))
            .sql
        )

        self.assertEqual(len(queries), 1)
        self.assertEqual(
            "SELECT "
            "CASE WHEN \"text\"='abc' THEN 'set(text=''abc'')' ELSE 'complement(text=''abc'')' END \"$text\","
            'SUM("number") "$aggr_number" '
            'FROM "test" '
            "GROUP BY \"$text\" "
            "ORDER BY \"$text\"",
            str(queries[0]),
        )

    def test_dimension_is_inserted_as_last_dimension_when_not_selected(self):
        queries = (
            ds.query.widget(f.Pandas(ds.fields.aggr_number))
            .dimension(ds.fields.date)
            .dimension(ds.fields.boolean)
            .filter(f.ResultSet(ds.fields.text == "abc"))
            .sql
        )

        self.assertEqual(len(queries), 1)
        self.assertEqual(
            "SELECT "
            '"date" "$date",'
            '"boolean" "$boolean",'
            "CASE WHEN \"text\"='abc' THEN 'set(text=''abc'')' ELSE 'complement(text=''abc'')' END \"$text\","
            'SUM("number") "$aggr_number" '
            'FROM "test" '
            'GROUP BY "$date","$boolean","$text" '
            'ORDER BY "$date","$boolean","$text"',
            str(queries[0]),
        )

    def test_dimension_uses_set_label_kwarg_and_None_for_complement(self):
        queries = (
            ds.query.widget(f.Pandas(ds.fields.aggr_number))
            .dimension(ds.fields.text)
            .filter(f.ResultSet(ds.fields.text == "abc", set_label="Text is ABC"))
            .sql
        )

        self.assertEqual(len(queries), 1)
        self.assertEqual(
            "SELECT "
            "CASE WHEN \"text\"='abc' THEN 'Text is ABC' ELSE NULL END "
            "\"$text\","
            'SUM("number") "$aggr_number" '
            'FROM "test" '
            "GROUP BY \"$text\" "
            "ORDER BY \"$text\"",
            str(queries[0]),
        )

    def test_dimension_breaks_complement_down_even_when_set_label_is_set_when_result_set_filter_wont_group_complement(
        self,
    ):
        queries = (
            ds.query.widget(f.Pandas(ds.fields.aggr_number))
            .dimension(ds.fields.text)
            .filter(
                f.ResultSet(
                    ds.fields.text == "abc",
                    set_label="IS ABC",
                    will_group_complement=False,
                )
            )
            .sql
        )

        self.assertEqual(len(queries), 1)
        self.assertEqual(
            "SELECT "
            "CASE WHEN \"text\"='abc' THEN 'IS ABC' ELSE \"text\" END \"$text\","
            'SUM("number") "$aggr_number" '
            'FROM "test" '
            "GROUP BY \"$text\" "
            "ORDER BY \"$text\"",
            str(queries[0]),
        )

    def test_dimension_breaks_complement_down_even_when_both_labels_are_set_but_wont_group_complement(
        self,
    ):
        queries = (
            ds.query.widget(f.Pandas(ds.fields.aggr_number))
            .dimension(ds.fields.text)
            .filter(
                f.ResultSet(
                    ds.fields.text == "abc",
                    set_label="IS ABC",
                    complement_label="OTHERS",
                    will_group_complement=False,
                )
            )
            .sql
        )

        self.assertEqual(len(queries), 1)
        self.assertEqual(
            "SELECT "
            "CASE WHEN \"text\"='abc' THEN 'IS ABC' ELSE \"text\" END \"$text\","
            'SUM("number") "$aggr_number" '
            'FROM "test" '
            "GROUP BY \"$text\" "
            "ORDER BY \"$text\"",
            str(queries[0]),
        )

    def test_dimension_uses_complement_label_kwarg_and_None_for_set(self):
        queries = (
            ds.query.widget(f.Pandas(ds.fields.aggr_number))
            .dimension(ds.fields.text)
            .filter(
                f.ResultSet(ds.fields.text == "abc", complement_label="Text is NOT ABC")
            )
            .sql
        )

        self.assertEqual(len(queries), 1)
        self.assertEqual(
            "SELECT "
            "CASE WHEN \"text\"='abc' THEN NULL ELSE 'Text is NOT ABC' END "
            "\"$text\","
            'SUM("number") "$aggr_number" '
            'FROM "test" '
            "GROUP BY \"$text\" "
            "ORDER BY \"$text\"",
            str(queries[0]),
        )

    def test_dimension_uses_both_set_and_complement_label_kwargs_when_available(self):
        queries = (
            ds.query.widget(f.Pandas(ds.fields.aggr_number))
            .dimension(ds.fields.text)
            .filter(
                f.ResultSet(
                    ds.fields.text == "abc",
                    set_label="Text is ABC",
                    complement_label="Text is NOT ABC",
                )
            )
            .sql
        )

        self.assertEqual(len(queries), 1)
        self.assertEqual(
            "SELECT "
            "CASE WHEN \"text\"='abc' THEN 'Text is ABC' ELSE 'Text is NOT ABC' END "
            "\"$text\","
            'SUM("number") "$aggr_number" '
            'FROM "test" '
            "GROUP BY \"$text\" "
            "ORDER BY \"$text\"",
            str(queries[0]),
        )