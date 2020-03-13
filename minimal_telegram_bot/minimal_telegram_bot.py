"""Main module."""

import ast
import os
from io import StringIO

import pandas as pd
import requests
import telegram

# import pickle


MAX_TELEGRAM_MESSAGE_LENGTH = 4096

BASE_REQUEST_URL = "https://pixometer.io/api/v1/"
FIRST_REQUEST_URL = f"{BASE_REQUEST_URL}access-token/"
SECOND_REQUEST_URL = f"{BASE_REQUEST_URL}readings/?format=csv&o="


FIRST_REQUEST_HEADERS = {"Content-Type": "application/json;charset=UTF-8"}
SECOND_REQUEST_HEADERS = {"Cookie": ("access_token=")}


def main(event=None, context=None):  # pylint: disable=unused-argument
    """main docstring"""

    pixometer_email = os.environ["PIXOMETER_EMAIL"]
    pixometer_password = os.environ["pixometer_password"]

    body = (
        '{"email":"'
        + pixometer_email
        + '","password":"'
        + pixometer_password
        + '"}'
    )

    with requests.session() as session:

        first_response = session.post(
            FIRST_REQUEST_URL, data=body, headers=FIRST_REQUEST_HEADERS
        )
        # pickle.dump(first_response, open("first_response.pickle", "wb"))
        # first_response = pickle.load(open("first_response.pickle", "rb"))

        first_response_string = first_response.content.decode("UTF-8")
        first_response_dict = ast.literal_eval(first_response_string)

        access_token = first_response_dict["access_token"]
        SECOND_REQUEST_HEADERS[
            "Cookie"
        ] = f"{SECOND_REQUEST_HEADERS['Cookie']}{access_token}"

        second_response = session.get(
            SECOND_REQUEST_URL, headers=SECOND_REQUEST_HEADERS
        )
        # pickle.dump(second_response, open("second_response.pickle", "wb"))
        # second_response = pickle.load(open("second_response.pickle", "rb"))

        second_response_string = second_response.content.decode("UTF-8")

    tg_msg = interpret_csv(second_response_string)

    send_telegram_message(tg_msg)

    return "OK"


def send_telegram_message(tg_msg):
    """Sending telegram message."""

    telegram_access_token = os.environ["TELEGRAM_ACCESS_TOKEN"]
    telegram_chat_id = os.environ["TELEGRAM_CHAT_ID"]

    bot = telegram.Bot(token=telegram_access_token)

    bot.send_message(
        chat_id=telegram_chat_id, text=tg_msg[:MAX_TELEGRAM_MESSAGE_LENGTH],
    )


def interpret_csv(input_csv):
    """Interpolating data and more"""

    input_csv_f = StringIO(input_csv)

    dataframe = pd.read_csv(input_csv_f)

    dataframe["Reading date"] = pd.to_datetime(
        dataframe["Reading date"], format="%d.%m.%Y %H:%M"
    )
    dataframe["Reading date"] = dataframe["Reading date"].dt.date

    start_date = pd.to_datetime("05.03.2019", format="%d.%m.%Y").date()

    mask = dataframe["Reading date"] > start_date

    dataframe = dataframe.loc[mask]

    output_str = ""

    for meter in ["Power Meter", "Gas Meter"]:

        df_meter = dataframe[dataframe["Location in building"] == meter]

        df_meter = df_meter[["Reading date", "Value"]]

        df_meter["Reading date"] = pd.to_datetime(df_meter["Reading date"])

        df_meter = df_meter.set_index("Reading date")

        df_meter = df_meter.resample("D").interpolate()

        output_str += generate_insights(df_meter, meter)

    return output_str


def generate_insights(dataframe, meter):
    """Making sense of the CSV data"""

    output_str = ""

    # Day

    output_str += f"--- {meter} ---\n"

    output_str += f"\nLast measured day: {str(dataframe.iloc[-1].name)[:10]}\n"

    day_value = dataframe.iloc[-1]["Value"]
    day_min1_value = dataframe.iloc[-2]["Value"]

    day_diff = day_value - day_min1_value

    output_str += (
        f"\nIn the last day, you consumed:"
        f" {kwh_to_euro_string(meter, day_diff)}"
    )

    day_min2_value = dataframe.iloc[-3]["Value"]

    day_min1_diff = day_min1_value - day_min2_value

    output_str += (
        f"\nIn the previous day, you consumed"
        f": {kwh_to_euro_string(meter, day_min1_diff)}"
    )

    day_rel_diff = day_diff / day_min1_diff

    output_str += f"\nIncrease: {int(day_rel_diff * 100 - 100)}%"

    # Week

    day_value = dataframe.iloc[-1]["Value"]
    day_min7_value = dataframe.iloc[-8]["Value"]

    week_diff = day_value - day_min7_value

    output_str += (
        f"\n\nIn the last week, you consumed:"
        f" {kwh_to_euro_string(meter, week_diff)}"
    )

    day_min14_value = dataframe.iloc[-15]["Value"]

    week_min1_diff = day_min7_value - day_min14_value

    output_str += (
        f"\nIn the previous week, you consumed:"
        f" {kwh_to_euro_string(meter, week_min1_diff)}"
    )

    week_rel_diff = week_diff / week_min1_diff

    output_str += f"\nIncrease: {int(week_rel_diff * 100 - 100)}%\n\n"

    return output_str


def kwh_to_euro_string(meter, val):
    """Convert readings into Euro"""

    if meter == "Power Meter":
        val = val * 0.277  # eprimo strompreis €/kwh
    elif meter == "Gas Meter":
        val = val * 18.5  # m3 in kwh
        val = val * 0.0542  # eprimo gaspreis €/kwh

    return f"{round(val, 2)}€"


if __name__ == "__main__":
    main()
