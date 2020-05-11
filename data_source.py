
import config

import requests
import pickle, gzip, hashlib
import os
import time
import io
import datetime

import pandas
import numpy

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

    def get_time_series_stat(self, stat_name, region, data_type='daily',
                             rolling_window_size=3, relative_to_pop=True):

        if region not in self.regions:
            raise ValueError(f'Unnkown region: {region}')

        col_name = DFRAME_COL_NAMES_BY_STAT_NAME[stat_name]
        dframe = self._dframe

        time_cumul_data = dframe[dframe['CCAA'] == region].loc[:, col_name]
        #print(dframe.loc[:,col_name])
    
        #print(time_cumul_data)
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
    daily = covid_data.get_time_series_stat('casos', 'VC')
    cumulative = covid_data.get_time_series_stat('casos', 'VC', data_type='cumulative')
    rolling = covid_data.get_time_series_stat('casos', 'VC', data_type='rolling')

    assert numpy.allclose(daily.cumsum(), cumulative)
