# coding: utf-8

import unittest
from collections import OrderedDict
from datetime import date

import numpy as np
import pandas as pd


def _rollup(data_frame, levels):
    roll = data_frame.groupby(level=levels).sum()
    rolled_levels = [name
                     for i, name in enumerate(data_frame.index.names)
                     if i not in levels]

    for rolled_level in rolled_levels:
        roll[rolled_level] = None

    return data_frame.append(roll.set_index(rolled_levels, append=True)).sort_index()


class BaseTransformerTests(unittest.TestCase):
    maxDiff = None

    cont_dim = {'label': 'Cont'}
    datetime_dim = {'label': 'Date'}
    uni_dim = {'label': 'Uni', 'label_field': 'uni_label'}
    cat1_dim = {'label': 'Cat1', 'label_options': {'a': 'A', 'b': 'B'}}
    cat2_dim = {'label': 'Cat2', 'label_options': {'y': 'Y', 'z': 'Z'}}

    shortcuts = {
        'a': 'A',
        'b': 'B',
        'c': 'C',
        'd': 'D',
        'y': 'Y',
        'z': 'Z',
        np.nan: 'Total',
    }

    cont_idx = pd.Index([0, 1, 2, 3, 4, 5, 6, 7], name='cont')
    cat1_idx = pd.Index([u'a', u'b'], name='cat1')
    cat2_idx = pd.Index([u'y', u'z'], name='cat2')

    uni_idx = pd.MultiIndex.from_tuples([(u'Aa', 1), (u'Bb', 2), (u'Cc', 3)],
                                        names=['uni_label', 'uni'])

    datetime_idx = pd.DatetimeIndex(pd.date_range(start=date(2000, 1, 1), periods=8), name='date')
    cont_cat_idx = pd.MultiIndex.from_product([cont_idx, cat1_idx], names=['cont', 'cat1'])
    cont_uni_idx = pd.MultiIndex.from_product([cont_idx, uni_idx.levels[0]],
                                              names=['cont', 'uni_label'])
    cat_cat_idx = pd.MultiIndex.from_product([cat1_idx, cat2_idx], names=['cat1', 'cat2'])
    cont_cat_cat_idx = pd.MultiIndex.from_product([cont_idx, cat1_idx, cat2_idx], names=['cont', 'cat1', 'cat2'])

    cont_cat_uni_idx = pd.MultiIndex.from_product([cont_idx, cat1_idx, uni_idx.levels[0]],
                                                  names=['cont', 'cat1', 'uni_label'])

    # Mock DF with single continuous dimension and one metric column
    no_dims_multi_metric_df = pd.DataFrame(
        np.array([
            np.arange(8),
        ]),
        columns=['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight'],
    )
    no_dims_multi_metric_schema = {
        'metrics': OrderedDict([('one', 'One'), ('two', 'Two'), ('three', 'Three'), ('four', 'Four'),
                                ('five', 'Five'), ('six', 'Six'), ('seven', 'Seven'), ('eight', 'Eight')]),
        'dimensions': OrderedDict()
    }

    # Mock DF with single continuous dimension and one metric column
    cont_dim_single_metric_df = pd.DataFrame(
        np.array([
            np.arange(8),
        ]).T,
        columns=['one'],
        index=cont_idx
    )
    cont_dim_single_metric_schema = {
        'metrics': OrderedDict([('one', 'One')]),
        'dimensions': OrderedDict([('cont', cont_dim)])
    }

    # Mock DF with single continuous dimension and two metric columns
    cont_dim_multi_metric_df = pd.DataFrame(
        np.array([
            np.arange(8),
            2 * np.arange(8),
        ]).T,
        columns=['one', 'two'],
        index=cont_idx
    )
    cont_dim_multi_metric_schema = {
        'metrics': OrderedDict([('one', 'One'), ('two', 'Two')]),
        'dimensions': OrderedDict([('cont', cont_dim)])
    }

    # Mock DF with single unique dimension and one metric column
    uni_dim_single_metric_df = pd.DataFrame(
        np.array([
            np.arange(3),
        ]).T,
        columns=['one'],
        index=uni_idx
    )
    uni_dim_single_metric_schema = {
        'metrics': OrderedDict([('one', 'One')]),
        'dimensions': OrderedDict([('uni', uni_dim)])
    }

    # Mock DF with single unique dimension and two metric columns
    uni_dim_multi_metric_df = pd.DataFrame(
        np.array([
            np.arange(3),
            2 * np.arange(3),
        ]).T,
        columns=['one', 'two'],
        index=uni_idx
    )
    uni_dim_multi_metric_schema = {
        'metrics': OrderedDict([('one', 'One'), ('two', 'Two')]),
        'dimensions': OrderedDict([('uni', uni_dim)])
    }

    # Mock DF with single categorical dimension and one metric column
    cat_dim_single_metric_df = pd.DataFrame(
        np.array([
            np.arange(2),
        ]).T,
        columns=['one'],
        index=cat1_idx
    )
    cat_dim_single_metric_schema = {
        'metrics': OrderedDict([('one', 'One')]),
        'dimensions': OrderedDict([('cat1', cat1_dim)])
    }

    # Mock DF with single categorical dimension and two metric columns
    cat_dim_multi_metric_df = pd.DataFrame(
        np.array([
            np.arange(2),
            2 * np.arange(2),
        ]).T,
        columns=['one', 'two'],
        index=cat1_idx
    )
    cat_dim_multi_metric_schema = {
        'metrics': OrderedDict([('one', 'One'), ('two', 'Two')]),
        'dimensions': OrderedDict([('cat1', cat1_dim)])
    }

    # Mock DF with single continuous time dimension and one metric column
    time_dim_single_metric_df = pd.DataFrame(
        np.array([
            np.arange(8),
        ]).T,
        columns=['one'],
        index=datetime_idx
    )
    time_dim_single_metric_schema = {
        'metrics': OrderedDict([('one', 'One')]),
        'dimensions': OrderedDict([('date', datetime_dim)])
    }
    time_dim_single_metric_ref_df = pd.DataFrame(
        np.array([
            np.arange(8),
            2 * np.arange(8),
        ]).T,
        columns=[['', 'wow'], ['one', 'one']],
        index=datetime_idx
    )
    time_dim_single_metric_ref_schema = {
        'metrics': OrderedDict([('one', 'One')]),
        'dimensions': OrderedDict([('date', datetime_dim)]),
        'references': {'wow': 'WoW'}
    }

    # Mock DF with continuous and categorical dimensions and one metric column
    cont_cat_dims_single_metric_df = pd.DataFrame(
        np.array([
            np.arange(16),
        ]).T,
        columns=['one'],
        index=cont_cat_idx
    )
    cont_cat_dims_single_metric_schema = {
        'metrics': OrderedDict([('one', 'One')]),
        'dimensions': OrderedDict([('cont', cont_dim), ('cat1', cat1_dim)])
    }

    # Mock DF with continuous and categorical dimensions and two metric columns
    cont_cat_dims_multi_metric_df = pd.DataFrame(
        np.array([
            np.arange(16),
            2 * np.arange(16),
        ]).T,
        columns=['one', 'two'],
        index=cont_cat_idx
    )
    cont_cat_dims_multi_metric_schema = {
        'metrics': OrderedDict([('one', 'One'), ('two', 'Two')]),
        'dimensions': OrderedDict([('cont', cont_dim), ('cat1', cat1_dim)])
    }

    # Mock DF with continuous and unique dimensions and two metric columns
    _cont_uni = pd.DataFrame(
        np.array([np.arange(24), np.arange(100, 124)]).T,
        columns=['one', 'two'],
        index=cont_uni_idx
    )
    _cont_uni['uni'] = None
    for label, uni_id in uni_idx:
        _cont_uni.loc[pd.IndexSlice[:, label], ['uni']] = uni_id

    cont_uni_dims_multi_metric_df = _cont_uni.set_index(['uni'], append=True)
    cont_uni_dims_multi_metric_df = pd.DataFrame(cont_uni_dims_multi_metric_df)
    cont_uni_dims_multi_metric_schema = {
        'metrics': OrderedDict([('one', 'One'), ('two', 'Two')]),
        'dimensions': OrderedDict([('cont', cont_dim), ('uni', uni_dim)])
    }

    # Mock DF with continuous and unique dimensions and one metric column
    cont_uni_dims_single_metric_df = pd.DataFrame(cont_uni_dims_multi_metric_df['one'])
    cont_uni_dims_single_metric_schema = {
        'metrics': OrderedDict([('one', 'One')]),
        'dimensions': OrderedDict([('cont', cont_dim), ('uni', uni_dim)])
    }

    # Mock DF with two categorical dimensions and one metric column
    cat_cat_dims_single_metric_df = pd.DataFrame(
        np.array([
            np.arange(4),
        ]).T,
        columns=['one'],
        index=cat_cat_idx,
    )
    cat_cat_dims_single_metric_schema = {
        'metrics': OrderedDict([('one', 'One')]),
        'dimensions': OrderedDict([('cat1', cat1_dim), ('cat2', cat2_dim)])
    }

    # Mock DF with two categorical dimensions and two metric columns
    cat_cat_dims_multi_metric_df = pd.DataFrame(
        np.array([
            np.arange(4),
            2 * np.arange(4),
        ]).T,
        columns=['one', 'two'],
        index=cat_cat_idx,
    )
    cat_cat_dims_multi_metric_schema = {
        'metrics': OrderedDict([('one', 'One'), ('two', 'Two')]),
        'dimensions': OrderedDict([('cat1', cat1_dim), ('cat2', cat2_dim)])
    }

    # Mock DF with continuous and two categorical dimensions and two metric columns
    cont_cat_cat_dims_multi_metric_df = pd.DataFrame(
        np.array([
            np.arange(32),
            2 * np.arange(32),
        ]).T,
        columns=['one', 'two'],
        index=cont_cat_cat_idx
    )
    cont_cat_cat_dims_multi_metric_schema = {
        'metrics': OrderedDict([('one', 'One'), ('two', 'Two')]),
        'dimensions': OrderedDict([('cont', cont_dim), ('cat1', cat1_dim), ('cat2', cat2_dim)])
    }

    # Mock DF with continuous and two categorical dimensions and two metric columns
    _cont_cat_uni = pd.DataFrame(
        np.array([np.arange(48), np.arange(100, 148)]).T,
        columns=['one', 'two'],
        index=cont_cat_uni_idx
    )
    _cont_cat_uni['uni'] = None
    for label, uni_id in uni_idx:
        _cont_cat_uni.loc[pd.IndexSlice[:, :, label], ['uni']] = uni_id

    cont_cat_uni_dims_multi_metric_df = _cont_cat_uni.set_index('uni', append=True)
    cont_cat_uni_dims_multi_metric_schema = {
        'metrics': OrderedDict([('one', 'One'), ('two', 'Two')]),
        'dimensions': OrderedDict([('cont', cont_dim), ('cat1', cat1_dim), ('uni', uni_dim)])
    }

    # Mock DF with continuous and two categorical dimensions and two metric columns using rollup for totals
    rollup_cont_cat_cat_dims_multi_metric_df = pd.DataFrame(
        np.array([
            np.arange(32),
            2 * np.arange(32),
        ]).T,
        columns=['one', 'two'],
        index=cont_cat_cat_idx
    )
    rollup_cont_cat_cat_dims_multi_metric_df = _rollup(rollup_cont_cat_cat_dims_multi_metric_df, [0, 1])
    rollup_cont_cat_cat_dims_multi_metric_df = _rollup(rollup_cont_cat_cat_dims_multi_metric_df, [0])
    rollup_cont_cat_cat_dims_multi_metric_schema = {
        'metrics': OrderedDict([('one', 'One'), ('two', 'Two')]),
        'dimensions': OrderedDict([('cont', cont_dim), ('cat1', cat1_dim), ('cat2', cat2_dim)])
    }
