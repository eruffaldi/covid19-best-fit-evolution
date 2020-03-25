"""Create an animation of the best-fit logistic curve over time."""
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import matplotlib.animation as animation
from sklearn.preprocessing import MinMaxScaler

from src import utils, config
import json
import argparse
import matplotlib
matplotlib.use('TkAgg')

MIN_POINTS = 5
ROLLING_MEAN_WINDOW = 2

plt.style.use('dark_background')
DOTS_COLOR = 'white'

# plt.style.use('seaborn-pastel')
# DOTS_COLOR = 'black'

matplotlib.rc('font', family='sans-serif')
matplotlib.rc('font', serif='Helvetica Neue')
matplotlib.rc('text', usetex='false')


def run(country, region= "", to_plot='confirmed', save=False, path=None,cached=False,repeat=True):
    if to_plot not in ['confirmed', 'deaths']:
        raise ValueError("'to_plot' must be in {'confirmed', 'deaths'}")

    if region == "":
        target = "world.json"
        url = config.DATA_URL
    elif country == "Italy":
        target = "italy.json"
        url = config.ITALYREGION_URL

    if cached:
        if os.path.isfile(target):
            data = json.load(open(target,"r"))
        else:
            data = utils.get_json_from_url(url)
            json.dump(data,open(target,"w"))
    else:
        data = utils.get_json_from_url(url)

    if region == "":
        df = pd.DataFrame(data[country])
    elif country == "Italy":
        df = pd.DataFrame(data)
        df = df.rename(columns=dict(data="date",totale_attualmente_positivi="confirmed",deceduti="deaths",denominazione_regione="region"))
        if region != "all" and region[0] != "m":
            df = df[df["region"] == region]
        else:
            if region[0] == "m":
                print("filtering")
                df = df[df["region"] != region[1:]]
                print(df.describe())
            df = df.groupby(["date"],as_index=False).agg(dict([(to_plot,"sum")]))
            print(df.describe())
    if to_plot == 'confirmed':
        min_cases = config.MIN_CONFIRMED_CASES
    else:
        min_cases = config.MIN_DEATHS

    y_max = df[to_plot].max() * 2
    df = df[df[to_plot] > min_cases]
    df = df.reset_index(drop=True)
    x_max = config.MAX_DAYS_AHEAD + len(df)

    x_future = [float(x) for x in list(np.linspace(0, x_max, num=x_max))]

    fig = plt.figure()
    ax = plt.axes(xlim=(0, len(x_future)), ylim=(0-(y_max*0.05), y_max))
    scatter = ax.scatter([], [], s=15, color=DOTS_COLOR)
    line, = ax.plot([], [], lw=2)
    date = ax.text(x_max - x_max*0.15, y_max + y_max*0.01, '')
    count = ax.text(x_max - x_max*0.23, y_max - y_max*0.05, '')
    if region != "":
        tregion = "Region: " + region
    else:
        tregion = ""
    plt.title(f"Logistic best fit over time, {to_plot} cases\nCountry: {country} {tregion}")
    plt.xlabel(f"Days since {min_cases} {to_plot} cases")
    plt.ylabel(f"# {to_plot}")

    def plot_animation():
        def init():
            line.set_data([], [])
            scatter.set_offsets(np.empty(shape=(0, 2)))
            date.set_text('')
            count.set_text('')
            return [scatter, line, date, count],

        def run_until_index(i):
            x = np.array([float(x) for x in range(len(df))])[:i+MIN_POINTS]

            m = MinMaxScaler()
            confirmed = df[to_plot].iloc[:i+MIN_POINTS]
            confirmed = confirmed.rolling(ROLLING_MEAN_WINDOW, min_periods=1, center=False).mean()

            y = m.fit_transform(confirmed.values.reshape(-1, 1))
            y = y.reshape(1, -1)[0]
            y_pred = utils.fit_predict(x, y, utils.logistic, x_pred=x_future)

            return m.inverse_transform(y_pred.reshape(-1, 1)).reshape(1, -1)[0]

        def get_date(i):
            return df['date'].values[i+MIN_POINTS-1]

        def get_count(i):
            return df[to_plot].values[i+MIN_POINTS-1]

        def get_scatter_values(i):
            x = np.array([float(x) for x in range(len(df))])[:i+MIN_POINTS]

            y = df[to_plot].iloc[:i + MIN_POINTS]

            return x, y

        def animate(i):
            x_s, y_s = get_scatter_values(i)
            scatter_values = np.column_stack((x_s, y_s))
            scatter.set_offsets(scatter_values)

            y = run_until_index(i)
            line.set_data(x_future, y)
            line.label = i

            date.set_text(get_date(i))
            count.set_text(f"# cases: {get_count(i)}")
            return [scatter, line, date, count],

        fig.tight_layout()

        return animation.FuncAnimation(fig, animate,
                                       init_func=init,
                                       frames=len(df)+1-MIN_POINTS,
                                       interval=500,
                                       repeat=repeat, repeat_delay=2)

    anim = plot_animation()
    if save:
        path = path or os.path.join(config.SRC_PATH, f'../examples/{country.lower()}{region.lower()}_animated.gif')
        anim.save(path, writer='imagemagick', fps=1.5)

    plt.show()
    plt.close()


if __name__ == "__main__":


    parser = argparse.ArgumentParser(description='Shows Fitting')
    parser.add_argument('--country',default="Italy")
    parser.add_argument('--region',default="")
    parser.add_argument('--to-plot',default="confirmed",choices=["deaths","confirmed"])
    parser.add_argument('--cached',action="store_true")
    parser.add_argument('--no-repeat',action="store_true")
    args = parser.parse_args()

    run(args.country, region=args.region, to_plot=args.to_plot, save=True,cached=args.cached,repeat=not args.no_repeat)
