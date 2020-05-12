
import config

import requests
import pickle, gzip, hashlib
import os
import time
import io
import datetime
import tempfile

import pandas
import numpy

import rpy2.robjects as robjects
from rpy2.robjects.conversion import localconverter
from rpy2.robjects import pandas2ri
from rpy2.robjects.packages import importr
eps = importr("EpiEstim")

DFRAME_COL_NAMES_BY_STAT_NAME = {'pcr': 'PCR+',
                                 'anticuerpo': 'TestAc+',
                                 'hospitalizados': 'Hospitalizados',
                                 'uci': 'UCI',
                                 'fallecidos': 'Fallecidos',
                                 'recuperados': 'Recuperados'}


POP_PER_REGION = {
    'AN': 8446561,
'AR': 1324397,
'AS': 1019993,
'CB': 581949,
'CE': 84434,
'CL': 2402877,
'CM': 2038440,
'CN': 2220270,
'CT': 7609499,
'EX': 1062797,
'GA': 2698764,
'IB': 1198576,
'MC': 1494442,
'MD': 6685471,
'ML': 84286,
'NC': 652526,
'PV': 2181919,
'RI': 314487,
'VC': 4998711,
}

def get_cache(cache_path, cache_expire_seconds=None):

    if cache_path is None or not cache_path.exists():
        return False

    if cache_expire_seconds is None:
        return True

    file_creation_time = os.path.getctime(cache_path)
    now = time.time()
    if now - file_creation_time < cache_expire_seconds:
        return True
    return False


def get_goverment_csv(cache_dir=None, cache_expire_seconds=None):

    url = config.SP_GOV_SOURCE_DATA_CSV_URL

    if cache_dir:
        cache_path = cache_dir / (url.split('/')[-1] + '.gz')
        if get_cache(cache_path=cache_path,
                     cache_expire_seconds=cache_expire_seconds):
            return pickle.load(gzip.open(cache_path, 'rb'))
    else:
        cache_path = None

    url = config.SP_GOV_SOURCE_DATA_CSV_URL
    response = requests.get(url)
    if response.status_code != 200:
        raise RuntimeError(f'Error downloading the data from: {url}')

    content = response.text

    if cache_path:
        pickle.dump(content, gzip.open(cache_path, 'wb'))

    return content


def date_parser(date_str):
    return datetime.datetime.strptime(date_str, '%d/%m/%Y')


def _get_dframe_with_goverment_data(cache_dir=None, cache_expire_seconds=None):
    csv_content = get_goverment_csv(cache_dir=cache_dir, cache_expire_seconds=cache_expire_seconds)

    if not csv_content.startswith('CCAA'):
        csv_content = csv_content[csv_content.index('CCAA'):]

    lines = csv_content.splitlines()

    lines = list(filter(lambda x: not (x.startswith('"*') or x.startswith('"N') or x.startswith('N') or x.startswith('*')), lines))
    csv_content = '\n'.join(lines)

    fhand = io.StringIO(csv_content)

    dframe = pandas.read_csv(fhand, sep=config.GOV_DATA_SEP,
                             index_col='FECHA', parse_dates=['FECHA'],
                             date_parser=date_parser,
                             header=0)

    return dframe.sort_index(axis=0)


class GovermentCovidData:
    def __init__(self, cache_dir=None, cache_expire_seconds=None):
        self._dframe = _get_dframe_with_goverment_data(cache_dir=cache_dir,
                                                       cache_expire_seconds=cache_expire_seconds)

    @property
    def regions(self):
        regions = sorted(numpy.unique(self._dframe.loc[:, 'CCAA'].values))
        return regions

    def calculate_r(self, region):
        dframe = self._dframe
        col_name = DFRAME_COL_NAMES_BY_STAT_NAME['pcr']
        cumul_cases = dframe[dframe['CCAA'] == region].loc[:, col_name]
        daily_cases = cumul_cases.iloc[1:].values - cumul_cases.iloc[:-1].values
        dates = cumul_cases.index[1:]

        if numpy.any(daily_cases < 0):
            print('The number of cases from some days are negative, fix it')
            daily_cases[daily_cases < 0] = 0

        cases_dframe = pandas.DataFrame({"dates": dates, "cases": daily_cases})

        with localconverter(robjects.default_converter + pandas2ri.converter):
            r_dframe = robjects.conversion.py2rpy(cases_dframe)

        results = eps.estimate_R(r_dframe[1], method="parametric_si", config=eps.make_config(mean_si=5, std_si=1))
        results = dict(results.items())

        with localconverter(robjects.default_converter + pandas2ri.converter):
            rhat = robjects.conversion.rpy2py(results["R"])

        mean_r = numpy.array(rhat['Mean(R)'])
        time_end = dates[int(rhat['t_end'][0]) - 1: int(rhat['t_end'][-1])]
        return {'mean_r': pandas.Series(mean_r, index=time_end)}

    def get_time_series_stat(self, stat_name, region, data_type='daily',
                             rolling_window_size=3, relative_to_pop=True):

        if region not in self.regions:
            raise ValueError(f'Unnkown region: {region}')

        dframe = self._dframe

        col_name = DFRAME_COL_NAMES_BY_STAT_NAME[stat_name]
        time_cumul_data = dframe[dframe['CCAA'] == region].loc[:, col_name]
    
        if relative_to_pop:
            time_cumul_data = time_cumul_data / POP_PER_REGION[region] * config.NUM_HABS

        if data_type == 'daily' or  data_type == 'rolling':
            values = time_cumul_data.iloc[1:].values - time_cumul_data.iloc[:-1].values
            index = time_cumul_data.index[1:]
            time_series = pandas.Series(values, index=index)
        elif data_type == 'cumulative':
            time_series = time_cumul_data.iloc[1:]

        if data_type == 'rolling':
            time_series = time_series.rolling(window=rolling_window_size).mean().iloc[rolling_window_size - 1:]

        time_series.name = stat_name
        return time_series

    @property
    def most_recent_date(self):
        return sorted(self._dframe.index)[-1]


if __name__ == '__main__':

    covid_data = GovermentCovidData(cache_dir=config.CACHE_DIR,
                                    cache_expire_seconds=config.CACHE_EXPIRE_SECONDS)

    daily = covid_data.calculate_r('CT')
    print(daily['mean_r'])
    a
    daily = covid_data.calculate_r('CT')
    print(daily['mean_r'])

    daily = covid_data.get_time_series_stat('pcr', 'VC')
    cumulative = covid_data.get_time_series_stat('pcr', 'VC', data_type='cumulative')
    rolling = covid_data.get_time_series_stat('pcr', 'VC', data_type='rolling')

    assert numpy.allclose(daily.cumsum(), cumulative)
