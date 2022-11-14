import os
import sys

import pandas

# Solving memory leak problem in pandas

from ctypes import cdll, CDLL

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


def plot(prices, times):
    print("Generating graph for {}".format("price_over_time"))
    target_file = os.path.join(".", "price_over_time.png")
    data = {'time': times, 'price': prices}
    dataframe = pandas.DataFrame(data['price'], index=data['time'])
    plotted = dataframe.plot.bar(ylabel='Price', figsize=(20, 2))
    plotted.get_figure().savefig(target_file, bbox_inches='tight')
    plotted.get_figure().clf()
