
import pathlib
import os

HOME_DIR = pathlib.Path.home()

if True:
    BASE_DIR = HOME_DIR / 'devel' / 'covid_sp_stats'

SP_GOV_SOURCE_DATA_CSV_URL = 'https://cnecovid.isciii.es/covid19/resources/agregados.csv'

CACHE_DIR = BASE_DIR / 'cache'
os.makedirs(CACHE_DIR, exist_ok=True)
CACHE_EXPIRE_SECONDS = 3600

GOV_DATA_SEP = ','

DEFAULT_ROLLING_WINDOW_SIZE = 3

PLOTS_DIR = BASE_DIR / 'plots'

NUM_HABS = 100000

BASE_URL = 'https://joseblanca.github.io/covid19'
PLOTS_URL = BASE_URL + '/plots'
