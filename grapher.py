import os
import pandas


def plot(prices, times):
    print("Generating graph for {}".format("price_over_time"))
    target_file = os.path.join(".", "price_over_time.png")
    data = {'time': times, 'price': prices}
    dataframe = pandas.DataFrame(data['price'], index=data['time'])
    plotted = dataframe.plot.bar(ylabel='Price', figsize=(20, 2))
    plotted.get_figure().savefig(target_file, bbox_inches='tight')
    plotted.get_figure().clf()
