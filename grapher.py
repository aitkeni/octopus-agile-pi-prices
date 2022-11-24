import os
import sys
import gc

import pandas
import matplotlib
from matplotlib import pyplot

matplotlib.use('Agg')


# Solving memory leak problem in pandas

from ctypes import cdll, CDLL

#from memory_profiler import profile

try:
    cdll.LoadLibrary("libc.so.6")
    libc = CDLL("libc.so.6")
    libc.malloc_trim(0)
except (OSError, AttributeError):
    libc = None

__old_del = getattr(pandas.DataFrame, '__del__', None)


def __new_del(self):
    if __old_del:
        __old_del(self)
    libc.malloc_trim(0)


if libc:
    print('Applying monkeypatch for pd.DataFrame.__del__', file=sys.stderr)
    pandas.DataFrame.__del__ = __new_del
else:
    print('Skipping monkeypatch for pd.DataFrame.__del__: libc or malloc_trim() not found', file=sys.stderr)

import numpy as np

#@profile
def plot(prices, times):
    print("Generating graph for {}".format("price_over_time"))
    target_file = os.path.join(".", "price_over_time.png")
    data = {'time': times, 'price': prices}
    dataframe = pandas.DataFrame(data['price'], index=data['time'])
    dfstacked = dataframe.stack()

    mask = dfstacked <= 10

    colors = np.array(['r']*len(dfstacked))
    colors[mask.values] = 'g'

# the pandas way
    #plotted = dataframe.plot.bar(ylabel='Price', color=colors, figsize=(20, 2))
    #plotted.get_figure().savefig(target_file, bbox_inches='tight')
    # print("Ref count after is : " + str(sys.getrefcount(plotted) ) )
    #print("Referers: " + str(gc.get_referrers(plotted)))
    #plotted.get_figure().clf()

# the matplotlib way
    plt = pyplot
    plt.bar(data['time'], data['price'], data=dataframe, color=colors, width=0.8)
    plt.rcParams["figure.figsize"] = (20, 3)
    plt.ylabel('Price')
    plt.xticks(rotation=90)
    plt.savefig(target_file, bbox_inches='tight')
    plt.cla()
    plt.clf()
    plt.close('all')
    # print("Ref count after is : " + str(sys.getrefcount(plt) ) )
    # print("Referers: " + str(gc.get_referrers(plt)))

    del plt
    gc.collect()
    del dataframe
    gc.collect()

