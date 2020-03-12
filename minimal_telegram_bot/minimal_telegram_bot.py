"""Main module."""

import ast
import os

import requests
import telegram

# import pickle


TELEGRAM_ACCESS_TOKEN = os.environ["TELEGRAM_ACCESS_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
MAX_TELEGRAM_MESSAGE_LENGTH = 4096

BASE_REQUEST_URL = "https://pixometer.io/api/v1/"
FIRST_REQUEST_URL = f"{BASE_REQUEST_URL}access-token/"
SECOND_REQUEST_URL = f"{BASE_REQUEST_URL}readings/?format=csv&o="

PIXOMETER_EMAIL = os.environ["PIXOMETER_EMAIL"]
PIXOMETER_PASSWORD = os.environ["PIXOMETER_PASSWORD"]

BODY = (
    '{"email":"'
    + PIXOMETER_EMAIL
    + '","password":"'
    + PIXOMETER_PASSWORD
    + '"}'
)

FIRST_REQUEST_HEADERS = {"Content-Type": "application/json;charset=UTF-8"}
SECOND_REQUEST_HEADERS = {"Cookie": ("access_token=")}


def main(event=None, context=None):  # pylint: disable=unused-argument
    """main docstring"""

    with requests.session() as session:

        first_response = session.post(
            FIRST_REQUEST_URL, data=BODY, headers=FIRST_REQUEST_HEADERS
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

    bot = telegram.Bot(token=TELEGRAM_ACCESS_TOKEN)

    bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=second_response_string[:MAX_TELEGRAM_MESSAGE_LENGTH],
    )

    return "OK"


if __name__ == "__main__":
    main()
