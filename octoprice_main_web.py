# this is the script you run every half hour by cron, best done about 20-30 seconds after the half hour to ensure
# that the right datetime is read in.
# For example --->   */30 * * * * sleep 20; /usr/bin/python3 octoprice_main_inky.py > /home/pi/cron.log

# NOTE - USAGE
# This script *won't work* unless you have run (python3 store_prices.py) at least once in the last 'n' hours
# (n is variable, it updates 4pm every day)
# You also need to update store_prices.py to include your own DNO region.
import os
from reprlib import Repr
from datetime import datetime, timezone, timedelta
from urllib.request import pathname2url
import requests

from nturl2path import pathname2url

import sqlite3
import pytz
import time
from http.server import HTTPServer, BaseHTTPRequestHandler  # Python’s built-in library

import grapher

MAX_RETRIES = 15  # give up once we've tried this many times to get the prices from the API
hostName = os.getenv('HOST', 'localhost')
serverPort = 8080  # You can choose any available port; by default, it is 8000
the_template_obj = {}
refresh_db = False


def get_prices():
    try:
        # connect to the database in rw mode so we can catch the error if it doesn't exist
        DB_URI = 'file:{}?mode=rw'.format(pathname2url('agileprices.sqlite'))
        conn = sqlite3.connect(DB_URI, uri=True)
        cur = conn.cursor()
        print('Connected to database...')
    except sqlite3.OperationalError as error:
        # handle missing database case
        raise SystemExit('Database not found - you need to run store_prices.py first.') from error

    # find current time and convert to year month day etc
    the_now = datetime.now(timezone.utc)
    the_now_local = the_now.astimezone(pytz.timezone('Europe/London'))

    the_year = the_now_local.year
    the_month = the_now_local.month
    the_hour = the_now_local.hour
    the_day = the_now_local.day
    if the_now_local.minute < 30:
        the_segment = 0
    else:
        the_segment = 1

    print('segment:')
    print(the_segment)

    # select from db where record == the above
    cur.execute("SELECT * FROM prices WHERE year=? AND month=? AND day=? AND hour=? AND segment=?",
                (the_year, the_month, the_day, the_hour, the_segment))

    rows = cur.fetchall()

    for row in rows:
        print(row[5])

    # get price
    current_price = row[5]
    # literally this is hardcoded tuple. DONT ADD ANY EXTRA FIELDS TO THAT TABLE on the
    # sqlite db or you'll get something that isn't price.

    # Find Next Price
    # find current time and convert to year month day etc
    the_now = datetime.now(timezone.utc)
    now_plus_10 = the_now + timedelta(minutes=30)
    the_year = now_plus_10.year
    the_month = now_plus_10.month
    the_hour = now_plus_10.hour
    the_day = now_plus_10.day
    if now_plus_10.minute < 30:
        the_segment = 0
    else:
        the_segment = 1

    print('segment+1:')
    print(the_segment)

    # select from db where record == the above
    cur.execute("SELECT * FROM prices WHERE year=? AND month=? AND day=? AND hour=? AND segment=?",
                (the_year, the_month, the_day, the_hour, the_segment))

    rows = cur.fetchall()

    for row in rows:
        print(row[5])

    # get price
    next_price = row[5]  # literally this is peak tuple. DONT ADD ANY EXTRA FIELDS TO THAT TABLE

    # Find Next+1 Price
    # find current time and convert to year month day etc
    the_now = datetime.now(timezone.utc)
    now_plus_10 = the_now + timedelta(minutes=60)
    the_year = now_plus_10.year
    the_month = now_plus_10.month
    the_hour = now_plus_10.hour
    the_day = now_plus_10.day
    if now_plus_10.minute < 30:
        the_segment = 0
    else:
        the_segment = 1

    print('segment:')
    print(the_segment)

    # select from db where record = ^
    cur.execute("SELECT * FROM prices WHERE year=? AND month=? AND day=? AND hour=? AND segment=?",
                (the_year, the_month, the_day, the_hour, the_segment))

    rows = cur.fetchall()

    for row in rows:
        print(row[5])

    # get price
    nextp1_price = row[5]  # literally this is peak tuple. DONT ADD ANY EXTRA FIELDS TO THAT TABLE

    nextp2_price = get_price_at_time(cur, 90)

    # attempt to make an list of the next 42 hours of values
    prices = []
    times = []
    for offset in range(0, 48):  # 24h = 48 segments
        min_offset = 30 * offset
        the_now = datetime.now(timezone.utc)
        now_plus_offset = the_now + timedelta(minutes=min_offset)
        the_year = now_plus_offset.year
        the_month = now_plus_offset.month
        the_hour = now_plus_offset.hour
        the_day = now_plus_offset.day
        if now_plus_offset.minute < 30:
            the_segment = 0
        else:
            the_segment = 1
        cur.execute("SELECT * FROM prices WHERE year=? AND month=? AND day=? AND hour=? AND segment=?",
                    (the_year, the_month, the_day, the_hour, the_segment))
        # rows = cur.fetchall()
        # get price
        row = cur.fetchone()
        if row is None:
            break
           # prices.append(999)  # we don't have that price yet!
        else:
            prices.append(row[5])
        times.append(datetime.strptime(row[6], '%Y-%m-%d %H:%M:%S').strftime('%H:%M'))
    return prices, times


# not required
def get_price_at_time(cur, offset):
    # Find Next+2 Price
    # find current time and convert to year month day etc
    the_now = datetime.now(timezone.utc)
    now_plus_offset = the_now + timedelta(minutes=90)
    the_year = now_plus_offset.year
    the_month = now_plus_offset.month
    the_hour = now_plus_offset.hour
    the_day = now_plus_offset.day
    if now_plus_offset.minute < 30:
        the_segment = 0
    else:
        the_segment = 1
    print('segment:')
    print(the_segment)
    # select from db where record == the above
    cur.execute("SELECT * FROM prices WHERE year=? AND month=? AND day=? AND hour=? AND segment=?",
                (the_year, the_month, the_day, the_hour, the_segment))
    rows = cur.fetchall()
    for row in rows:
        print(row[5])
    # get price
    nextp2_price = row[5]  # literally this is peak tuple. DONT ADD ANY EXTRA FIELDS TO THAT TABLE
    return nextp2_price


def fill_in(the_template_obj):
    substitutor = Substitutor(the_template_obj)

    prices, times = get_prices()
    current_price = prices[0]
    substitutor.set("$PRICE", "{0:.1f}".format(current_price) + "p")

    # find current time and convert to year month day etc
    the_now = datetime.now(timezone.utc)
    the_now_local = the_now.astimezone(pytz.timezone('Europe/London'))
    substitutor.set("$NOW", the_now_local.time().strftime('%l:%M%p'))

    if current_price > 10:
        substitutor.setText("$NUTS", "")
        substitutor.setStyleSheet("background-color:red;")
    else:
        substitutor.setText("$NUTS", "Whoop Whoop\n     go nuts")
        substitutor.setStyleSheet("background-color:green;")

    # NEXT
    substitutor.set("$NEXT_PRICE", "{0:.1f}".format(prices[1]) + "p")
    substitutor.set("$NEXT_TIME", get_segment_time(the_now, 30))

    if prices[1] > 10:
        substitutor.set("$STYLE_NEXT1", "background-color:red;")
    else:
        substitutor.set("$STYLE_NEXT1", "background-color:green;")

    # NEXT
    substitutor.set("$NEXT_NEXT_PRICE", "{0:.1f}".format(prices[2]) + "p")
    substitutor.set("$NEXT_NEXT_TIME", get_segment_time(the_now, 60))
    if prices[2] > 10:
        substitutor.set("$STYLE_NEXT2", "background-color:red;")
    else:
        substitutor.set("$STYLE_NEXT2", "background-color:green;")

    # NEXT

    substitutor.set("$NEXT_NEXT_NEXT_PRICE", "{0:.1f}".format(prices[3]) + "p")
    substitutor.set("$NEXT_NEXT_NEXT_TIME", get_segment_time(the_now, 90))
    if prices[3] > 10:
        substitutor.set("$STYLE_NEXT3", "background-color:red;")
    else:
        substitutor.set("$STYLE_NEXT3", "background-color:green;")

    plot_graph(prices, times)

    return substitutor.asHtml()


def get_segment_time(the_now, offset):
    now_plus_offset = the_now + timedelta(minutes=offset)
    the_hour = now_plus_offset.hour
    if now_plus_offset.minute < 30:
        next_time = str(the_hour) + ":00"
    else:
        next_time = str(the_hour) + ":30"
    return next_time


class Substitutor:
    def __init__(self, file_to_fill):
        self.file_to_fill = file_to_fill

    def set(self, marker, value):
        for i in range(len(self.file_to_fill)):
            self.file_to_fill[i] = self.file_to_fill[i].replace(marker, value)

    def setStyleSheet(self, value):
        self.set("$STYLESHEET", value)

    def setText(self, marker, value):
        self.set(marker, value)

    def asHtml(self):
        return self.file_to_fill


def plot_graph(prices, times):
    grapher.plot(prices, times)


class MyServer(BaseHTTPRequestHandler):

    def do_GET(self):  # the do_GET method is inherited from BaseHTTPRequestHandler

        if self.path == "/price_over_time.png":
            png = open("." + self.path, "rb", 1)
            self.send_response(200)
            self.send_header("Content-type", "image/png")
            self.end_headers()
            self.wfile.write(png.read())
            png.close()
        else:
            self.refresh_database()
            template = open("template.html", "r", 1)
            the_template_obj = fill_in(template.readlines())

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            for line in the_template_obj:
                self.wfile.write(bytes(line, "utf-8"))

    def refresh_database(self):
        global refresh_db
        # refresh database
        if datetime.now().hour == 16:
            refresh_db = True
        if datetime.now().hour == 17 and refresh_db:
            create_database()
            refresh_db = False


def get_prices_from_api(request_uri: str) -> dict:
    """using the provided URI, request data from the Octopus API and return a JSON object.
    Try to handle errors gracefully with retries when appropriate."""

    # Try to handle issues with the API - rare but do happen, using an
    # exponential sleep time up to 2**14 (16384) seconds, approx 4.5 hours.
    # We will keep trying for over 9 hours and then give up.

    print('Requesting Agile prices from Octopus API...')
    retry_count = 0
    my_repr = Repr()
    my_repr.maxstring = 80  # let's avoid truncating our error messages too much

    while retry_count <= MAX_RETRIES:

        if retry_count == MAX_RETRIES:
            raise SystemExit('API retry limit exceeded.')

        try:
            success = False
            response = requests.get(request_uri, timeout=5)
            response.raise_for_status()
            if response.status_code // 100 == 2:
                success = True
                return response.json()

        except requests.exceptions.HTTPError as error:
            print(('API HTTP error ' + str(response.status_code) +
                   ',retrying in ' + str(2 ** retry_count) + 's'))
            time.sleep(2 ** retry_count)
            retry_count += 1

        except requests.exceptions.ConnectionError as error:
            print(('API connection error: ' + my_repr.repr(str(error)) +
                   ', retrying in ' + str(2 ** retry_count) + 's'))
            time.sleep(2 ** retry_count)
            retry_count += 1

        except requests.exceptions.Timeout:
            print('API request timeout, retrying in ' + str(2 ** retry_count) + 's')
            time.sleep(2 ** retry_count)
            retry_count += 1

        except requests.exceptions.RequestException as error:
            raise SystemExit('API Request error: ' + str(error)) from error

        if success:
            print('API request successful, status ' + str(response.status_code) + '.')
            break


def insert_data(cursor, data: dict):
    """Insert our data records one by one, keep track of how many were successfully inserted
    and print the results of the insertion."""

    num_prices_inserted = 0
    num_duplicates = 0

    for result in data['results']:

        # do messy pufferfish data mangling to prevent rewriting the inky display code
        mom_price = result['value_inc_vat']
        raw_from = result['valid_from']
        # work out the buckets
        date = datetime.strptime(raw_from,
                                 "%Y-%m-%dT%H:%M:%SZ")  # We need to reformat the date to a python date from a json date
        mom_year = (date.year)
        mom_month = (date.month)
        mom_day = (date.day)
        mom_hour = (date.hour)
        if date.minute == 00:  # We actually don't care about exact minutes, we just mark with a 0 if it's an hour time or a 1 if it's half past the hour.
            mom_offset = 0
        else:
            mom_offset = 1  # half hour

        # insert_record returns false if it was a duplicate record
        # or true if a record was successfully entered.
        if insert_record(cursor, mom_year, mom_month, mom_day, mom_hour, mom_offset, mom_price, result['valid_from']):
            num_prices_inserted += 1
        else:
            num_duplicates += 1

    if num_duplicates > 0:
        print('Ignoring ' + str(num_duplicates) + ' duplicate prices...')

    if num_prices_inserted > 0:
        lastslot = datetime.strftime(datetime.strptime(
            data['results'][0]['valid_to'], "%Y-%m-%dT%H:%M:%SZ"), "%H:%M on %A %d %b")
        print(str(num_prices_inserted) + ' prices were inserted, ending at ' + lastslot + '.')
    else:
        print('No prices were inserted - maybe we have them'
              ' already or octopus are late with their update.')


def insert_record(cursor, year: int, month: int, day: int, hour: int, segment: int, price: float,
                  valid_from: str) -> bool:
    """Assuming we still have a cursor, take a tuple and stick it into the database.
       Return False if it was a duplicate record (not inserted) and True if a record
       was successfully inserted."""
    if not cursor:
        raise SystemExit('Database connection lost!')

    # make the date/time work for SQLite, it's picky about the format,
    # easier to use the built in SQLite datetime functions
    # when figuring out what records we want rather than trying to roll our own
    valid_from_formatted = datetime.strftime(
        datetime.strptime(valid_from, "%Y-%m-%dT%H:%M:%SZ"), "%Y-%m-%d %H:%M:%S")

    data_tuple = (year, month, day, hour, segment, price, valid_from_formatted)

    try:
        cursor.execute("INSERT INTO 'prices' "
                       "('year', 'month', 'day', 'hour', 'segment', 'price', 'valid_from')"
                       "VALUES (?, ?, ?, ?, ?, ?, ?);", data_tuple)

    except sqlite3.Error as error:
        # ignore expected UNIQUE constraint errors when trying to duplicate prices
        # this will only raise SystemExit if it's **not** a 'UNIQUE' error
        if str.find(str(error), 'UNIQUE') == -1:
            raise SystemExit('Database error: ' + str(error)) from error

        return False  # it was a duplicate record and wasn't inserted

    else:
        return True  # the record was inserted


def remove_old_prices(cursor, age: str):
    """Delete old prices from the database, we don't want to display those and we don't want it
    to grow too big. 'age' must be a string that SQLite understands"""
    if not cursor:
        raise SystemExit('Database connection lost before pruning prices!')
    try:
        cursor.execute("SELECT COUNT(*) FROM prices "
                       "WHERE valid_from < datetime('now', '-" + age + "')")
        selected_rows = cursor.fetchall()
        num_old_rows = selected_rows[0][0]
        # I don't know why this doesn't just return an int rather than a list of a list of an int
        if num_old_rows > 0:
            cursor.execute("DELETE FROM prices WHERE valid_from < datetime('now', '-" + age + "')")
            print(str(num_old_rows) + ' unneeded prices from the past were deleted.')
        else:
            print('There were no old prices to delete.')
    except sqlite3.Error as error:
        print('Failed while trying to remove old prices from database: ', error)


def create_database():
    # hopefully these won't ever change
    AGILE_TARIFF_BASE = (
        'https://api.octopus.energy/v1/products/AGILE-VAR-22-10-19/electricity-tariffs/E-1R-AGILE-VAR-22-10-19-')
    AGILE_TARIFF_TAIL = "/standard-unit-rates/"

    # Build the API for the request - public API so no authentication required
    agile_tariff_region = "F"  # yorkshire
    AGILE_TARIFF_URI = (AGILE_TARIFF_BASE + agile_tariff_region + AGILE_TARIFF_TAIL)

    data_rows = get_prices_from_api(AGILE_TARIFF_URI)

    try:
        # connect to the database in rw mode so we can catch the error if it doesn't exist
        DB_URI = 'file:{}?mode=rw'.format(pathname2url('agileprices.sqlite'))
        conn = sqlite3.connect(DB_URI, uri=True)
        cursor = conn.cursor()
        print('Connected to database...')

    except sqlite3.OperationalError:
        # handle missing database case
        print('No database found. Creating a new one...')
        conn = sqlite3.connect('agileprices.sqlite')
        cursor = conn.cursor()
        # UNIQUE constraint prevents duplication of data on multiple runs of this script
        # ON CONFLICT FAIL allows us to count how many times this happens
        cursor.execute("CREATE TABLE prices (year INTEGER, month INTEGER, day INTEGER, hour INTEGER, "
                       "segment INTEGER, price REAL, valid_from STRING UNIQUE ON CONFLICT FAIL)")
        conn.commit()
        print('Database created... ')

    insert_data(cursor, data_rows)

    remove_old_prices(cursor, '2 days')

    # finish up the database operation
    if conn:
        conn.commit()
        conn.close()


if __name__ == '__main__':
    # window()
    create_database()
    webServer = HTTPServer((hostName, serverPort), MyServer)
    print("Server started http://%s:%s" % (hostName, serverPort))  # Server starts
    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass
    webServer.server_close()  # Executes when you hit a keyboard interrupt, closing the server
    print("Server stopped.")
