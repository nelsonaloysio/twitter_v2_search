#!/usr/bin/env python3

import json
import logging as log
from argparse import ArgumentParser
from collections import defaultdict
from os import environ, mkdir
from os.path import dirname, isdir, splitext
from time import sleep, time

import requests

log.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=log.INFO,
)

BEARER_TOKEN = environ.get("BEARER_TOKEN")

ENDPOINT_DEFAULT = "https://api.twitter.com/2/tweets/{}/all"


class Twitter():

    def __init__(self):
        ''' Initializes class. '''

    def request(self, endpoint, bearer_token=BEARER_TOKEN, **params):
        headers = self.__create_headers(bearer_token)
        json_response = self.__connect_to_endpoint(endpoint, headers, **params)
        return json_response

    @staticmethod
    def __connect_to_endpoint(endpoint, headers, **params):
        response = requests.request(
            "GET", endpoint, headers=headers, params=params)
        if response.status_code != 200:
            log.error(f"{response.status_code}: {response.text}")
        return response.json()

    @staticmethod
    def __create_headers(bearer_token) -> dict:
        return {"Authorization": f"Bearer {bearer_token}"}


class TwitterSearch(Twitter):

    def search(self, interval=1, limit=None, output_file=None, **params) -> dict:
        '''
        Returns tweet data, loops until finished.
        '''
        params.pop("granularity", None)
        responses = defaultdict(list)
        time_to_print = time()
        total = 0

        while True:
            json_response = self.request(
                endpoint=ENDPOINT_DEFAULT.format("search"),
                **self.__params(**params),
            )

            responses["data"] += json_response.get("data", [])
            responses["errors"] += json_response.get("errors", [])
            for key, values in json_response.get("includes", {}).items():
                responses[key] += values

            total += json_response.get("meta", {}).get("result_count", 0)
            params["next_token"] = json_response.get("meta").get("next_token", None)

            if output_file is not None:
                self.__write_json(json_response, output_file, mode="a" if total else "w")

            if (params["next_token"] is None) or (limit and total >= limit):
                break

            if (time() - time_to_print) > 10:
                log.info(f"Captured {total} tweets.")
                time_to_print = time()

            sleep(int(interval)) if interval and int(interval) > 0 else None

        log.info(f"Captured {total} total tweets.")
        return dict(responses)

    def counts(self, max_results=None, **params) -> list:
        '''
        Returns tweet count, ignores `max_results`.
        '''
        json_response = self.request(
            endpoint=ENDPOINT_DEFAULT.format("counts"),
            granularity=params.pop("granularity", "day"),
            **self.__params(**params),
        )
        log.info("Returned %s tweets." % json_response.get(
            "meta", {}).get("total_tweet_count", 0)
        )
        return json_response

    @staticmethod
    def __params(interval=None, limit=None, output_file=None, **params):
        '''
        Returns valid parameters only.
        '''
        return {key: value for key, value in params.items() if value is not None}

    @staticmethod
    def __write_json(json_response, output_file, mode="w"):
        '''
        Dumps responses to file, one record per line.
        '''
        absname = splitext(output_file)[0]
        folder = dirname(output_file)

        if folder and not isdir(folder):
            mkdir(folder)

        with open(f"{absname}.json", mode) as j:
            for response in json_response.get("data", []):
                json.dump(response, j)
                j.write('\n')

        for key, values in json_response.get("includes", {}).items():
            with open(f"{absname}_{key}.json", mode) as j:
                for response in values:
                    json.dump(response, j)
                    j.write('\n')

def args() -> dict:
    argparser = ArgumentParser()
    argparser.add_argument("query", help="Required (leave parameter as blank to ignore)")
    argparser.add_argument("-o", "--output-file", dest="output_file", help="Write returned data to JSON file")
    argparser.add_argument("--days", action="store_const", const="day", dest="granularity", help='Returns daily tweet count')
    argparser.add_argument("--hours", action="store_const", const="hour", dest="granularity", help='Returns hourly tweet count')
    argparser.add_argument("--minutes", action="store_const", const="minute", dest="granularity", help='Returns tweet count per minute')
    argparser.add_argument("--start-time", help='Timestamp format "YYYY-MM-DDTHH:MM:SS+00:00:00"')
    argparser.add_argument("--end-time", help='Timestamp format "YYYY-MM-DDTHH:MM:SS+00:00:00"')
    argparser.add_argument("--since-id", help="First tweet ID to capture")
    argparser.add_argument("--until-id", help="Last tweet ID to capture")
    argparser.add_argument("--max-results", default=100, type=int, help="Maximum results (API default is 10, customly set to 100)")
    argparser.add_argument("--expansions", help="Specified expansions results in full objects in the 'includes' response object")
    argparser.add_argument("--tweet-fields", help='Tweet JSON attributes to include in endpoint responses (default: "id, text")')
    argparser.add_argument("--media-fields", help='Media JSON attributes to include in endpoint responses (default: "id")')
    argparser.add_argument("--poll-fields", help='Twitter Poll JSON attributes to include in endpoint responses (default: "id")')
    argparser.add_argument("--place-fields", help='Twitter Place JSON attributes to include in endpoint responses (default: "id")')
    argparser.add_argument("--user-fields", help='User JSON attributes to include in endpoint responses (default: "id")')
    argparser.add_argument("--extra-headers", help="JSON-formatted str representing a dict of additional HTTP request headers")
    argparser.add_argument("--interval", default=1, type=int, help="Request interval (seconds, default: 1)")
    argparser.add_argument("--limit", default=None, type=int, help="Maximum number of tweets to capture")
    return vars(argparser.parse_args())


def main(**args) -> None:
    twitter = TwitterSearch()
    return twitter.search(**args)\
           if args.get("granularity") is None\
           else twitter.counts(**args)


if __name__ == "__main__":
    main(**args())