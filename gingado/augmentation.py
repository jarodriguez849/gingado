# AUTOGENERATED! DO NOT EDIT! File to edit: 00_augmentation.ipynb (unless otherwise specified).

__all__ = ['AugmentSDMX']

# Cell
#export
import pandas as pd
import pandasdmx as sdmx
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.utils.validation import check_is_fitted
from sklearn.feature_selection import VarianceThreshold

class AugmentSDMX(BaseEstimator, TransformerMixin):

    InputIndexMessage = "The dataset to be augmented must have a row index with the date/time information"
    def _format_string(self):
        return "%Y-%m-%d" if self.data_freq_ == 'D' else "%Y-%m" if self.data_freq_ == 'M' else "%Y"

    def _get_dates(self):
        fstr = self._format_string()
        return {
            "startPeriod": min(self.index_).strftime(fstr),
            "endPeriod": max(self.index_).strftime(fstr),
        }

    def _transform(self, X, training=True):
        data_sdmx = {}
        for source in self.sources.keys():
            src_conn = sdmx.Request(source, backend=self.backend, expire_after=1800, use_cache=True)
            src_dflows = src_conn.dataflow()
            if self.sources[source] == 'all':
                dflows = {k: v for k, v in src_dflows.dataflow.items()}
            else:
                dflows = {k: v for k, v in src_dflows.dataflow.items() if k in self.sources[source]}
            for dflow in dflows.keys():
                if self.verbose: print(f"Querying data from {source}'s dataflow '{dflow}' - {dflows[dflow].dict()['name']}...")
                try:
                    data = sdmx.to_pandas(src_conn.data(dflow, key=self.keys_, params=self.params_), datetime='TIME_PERIOD')
                except:
                    if self.verbose: print("this dataflow does not have data in the desired frequency and time period.")
                    continue
                data.columns = ['__'.join(col) for col in data.columns.to_flat_index()]
                data_sdmx[source+"__"+dflow] = data

        if len(data_sdmx.keys()) is None:
            return X

        df = pd.concat(data_sdmx, axis=1)
        df.columns = ['_'.join(col) for col in df.columns.to_flat_index()]

        if training:
            # test that the dataset `X` has the same dimension as the one
            # used during training, which is an evidence they are the same
            n_samples_in_transform, n_features_in_transform = X.shape
            if n_samples_in_transform != self.n_samples_in_ or n_features_in_transform != self.n_features_in_:
                raise ValueError("The X passed to the transform() method must be compatible with the X used by the fit() method.")
            # during testing, we don't want the possibility of a different
            # set of columns being retained by virtue of different dynamics
            # in both datasets. For example, if a feature is included in the
            # training but during the test dates the variable didn't move, it
            # should not be subject to the test below so that it is still
            # included in the fitted data.
            feat_sel = VarianceThreshold() if self.variance_threshold is None else VarianceThreshold(threshold=self.variance_threshold)
            feat_sel.fit(df)
            self.features_stay_ = df.columns[feat_sel.get_support()]
            self.features_removed_ = df.columns[~feat_sel.get_support()]

            df = df.iloc[:, feat_sel.get_support()]
            df.columns = feat_sel.get_feature_names_out()

            df.dropna(axis=0, how='all', inplace=True)
            df.dropna(axis=1, how='all', inplace=True)


        X = pd.merge(left=X, right=df, how='left', left_index=True, right_on='TIME_PERIOD')
        if 'TIME_PERIOD' in X.columns:
            X.drop(columns='TIME_PERIOD', inplace=True)
        if self.propagate_last_known_value:
            X.fillna(method="ffill", inplace=True)
        if training:
            X.index = self.index_
        return X

    def __init__(self, sources={'BIS': 'WS_CBPOL_D'}, variance_threshold=None, backend='memory', propagate_last_known_value=True, verbose=True):
        self.sources = sources
        self.variance_threshold = variance_threshold
        self.backend = backend
        self.propagate_last_known_value = propagate_last_known_value
        self.verbose = verbose

    def fit(self, X, y=None):
        """
        Fits transformer to `X`; `y` is kept as argument for API consistency only.

        Parameters
        ----------
        X : a pandas Series or DataFrame with an index of datetime type
            Input samples.
        y : default=None

        Returns
        -------
        The fitted version of the instance of `AugmentSDMX`, ie after it learned \
        the frequency of the time series in `X`. The possible values fitted on the \
        data are described in: \
        https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.Timedelta.resolution_string.html.
        """
        try:
            self.data_freq_ = X.index.to_series().diff().min().resolution_string
        except AttributeError:
            print(self.InputIndexMessage)
            raise
        self.index_ = X.index
        self.keys_ = {'FREQ': self.data_freq_}
        X = self._validate_data(X)

        # this variable below is only included to test for consistency \
        # if `fit` and `transform` are called separately with the same `X`
        self.n_samples_in_ = X.shape[0]

        return self

    def transform(self, X, y=None, training=False):
        check_is_fitted(self)
        self.params_ = self._get_dates()
        idx = X.index
        transf_X = self._transform(X, training=training)
        transf_X.index = idx
        return transf_X

    def fit_transform(self, X, y=None):
        """
        Fit to data, then transform it.
        Fits transformer to `X` and returns a transformed version of `X`.
        `y` is kept as argument for API consistency only.

        Parameters
        ----------
        X : a pandas Series or DataFrame with an index of datetime type
            Input samples.
        y : default=None
            Target values (None for unsupervised transformations).
        training : True / False. default=False
            The default value ensures that the when this transformer is called \
            by a pipeline
        Returns
        -------
        X_new : ndarray array of shape (n_samples, n_features_new)
            Transformed array.
        """

        self.fit(X)
        self.params_ = self._get_dates()
        return self.transform(X, training=True)