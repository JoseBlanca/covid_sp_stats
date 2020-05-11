
import config

import os
from pathlib import Path
from pprint import pprint

from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure

from data_source import GovermentCovidData


def plot_stat(covid_data, stat_name, data_type, rolling_window_size=config.DEFAULT_ROLLING_WINDOW_SIZE,
              relative_to_pop=True, out_dir=config.PLOTS_DIR):

    os.makedirs(out_dir, exist_ok=True)

    plot_paths = []
    for region in covid_data.regions:
        plot_path = out_dir / f'{region}.svg'
        series = covid_data.get_time_series_stat(stat_name,
                                                 region=region,
                                                 data_type=data_type,
                                                 rolling_window_size=rolling_window_size,
                                                 relative_to_pop=relative_to_pop)

        fig = Figure()
        axes = fig.add_subplot(111)
        axes.plot(series.index, series.values, linestyle='-', marker='.')

        if relative_to_pop:
            stat_name_for_y_label = f'{stat_name} (por {config.NUM_HABS} hab.)'
        else:
            stat_name_for_y_label = stat_name

        if data_type == 'rolling':
            y_label = f'{region} {stat_name_for_y_label} (Media {rolling_window_size} días)'
        elif data_type == 'daily':
            y_label = f'{region} {stat_name_for_y_label} diarios'
        elif data_type == 'cumulative':
            y_label = f'{region} {stat_name_for_y_label} acumulados'
        axes.set_ylabel(y_label)
        axes.xaxis.set_tick_params(rotation=45)
        fig.set_tight_layout(True)
        fig.savefig(plot_path)
        axes.cla()
        fig.clf()
        del axes
        del fig
        plot_paths.append(plot_path)

    return {'out_dir': out_dir, 'plot_paths': plot_paths}


def _build_url_from_path(path, base_path):
    return config.PLOTS_URL + '/' + str(path.relative_to(base_path))


def generate_html_index(out_dir, paths, base_out_dir):
    index_path = out_dir / 'index.html'

    html = ''
    html += '<html>\n'

    html += '<ul>\n'
    for path in paths:
        fname = path.name.split('.')[0]
        url = _build_url_from_path(path, base_out_dir)

        html += f'<li><a href="{url}">{fname}</a></li>\n'
    html += '</ul>\n'

    html += '</html>\n'

    index_path.open('wt').write(html)


if __name__ == '__main__':

    out_dir = Path('/Users/jose/devel/JoseBlanca.github.io/covid19/plots')
    stats = ['hospitalizados', 'fallecidos', 'uci', 'pcr', 'anticuerpo']
    data_types = ['daily', 'cumulative', 'rolling']
    relative_to_pop = True

    covid_data = GovermentCovidData(cache_dir=config.CACHE_DIR,
                                    cache_expire_seconds=config.CACHE_EXPIRE_SECONDS)

    print(covid_data.most_recent_date)

    cumulative_out_dir = out_dir / f'por_{config.NUM_HABS}_habs' if relative_to_pop else 'absoluto'

    out_dirs = []
    for data_type in data_types:
        data_type_out_dir = cumulative_out_dir / data_type
        data_type_out_dirs = []
        for stat in stats:
            stat_out_dir = data_type_out_dir / stat
            res = plot_stat(covid_data, stat, data_type=data_type, relative_to_pop=relative_to_pop, out_dir=stat_out_dir)
            generate_html_index(res['out_dir'], res['plot_paths'], base_out_dir=out_dir)
            data_type_out_dirs.append(res['out_dir'])
        generate_html_index(data_type_out_dir, data_type_out_dirs, base_out_dir=out_dir)
        out_dirs.append(data_type_out_dir)
    generate_html_index(cumulative_out_dir, out_dirs, base_out_dir=out_dir)
    generate_html_index(out_dir, [cumulative_out_dir], base_out_dir=out_dir)