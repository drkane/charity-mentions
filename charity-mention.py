from __future__ import print_function
import random
import json
import os
import time
import tweepy
import configargparse
import re
from datetime import datetime
import requests

FINDTHATCHARITY_URL = 'https://findthatcharity.uk/charity/{}.json'
FINDTHATCHARITY_SEARCH_URL = 'https://findthatcharity.uk/'
FINDTHATCHARITY_RECONCILE_URL = 'https://findthatcharity.uk/reconcile'
TWITTER_USERNAME = 'CharityRandom'

# connect to twitter API and tweet
# from: https://videlais.com/2015/03/02/how-to-create-a-basic-twitterbot-in-python/
class TwitterAPI:
    def __init__(self, cfg):
        auth = tweepy.OAuthHandler(cfg["consumer_key"], cfg["consumer_secret"] )
        auth.set_access_token(cfg["access_token"], cfg["access_token_secret"])
        self.api = tweepy.API(auth)

    def tweet(self, message, reply_to_id=None):
        self.api.update_status(status=message, in_reply_to_status_id=reply_to_id)

    def get_mentions(self):
        return self.api.mentions_timeline()

def test_for_regno(message):
    regno_regex = r'\b([1-9][0-9]{5,6}|SC[O0-9]{5})\b'
    return re.findall(regno_regex, message)

def test_for_search(message):
    search_regex = '@{} search:?\s(.*)'.format(TWITTER_USERNAME)
    match = re.match(search_regex, message)
    if match:
        return match.group(1)

def get_charity(regno):
    regno = regno.replace('SCO', 'SC0')
    r_url = FINDTHATCHARITY_URL.format(regno)
    r = requests.get(r_url)
    if r.status_code == requests.codes.ok:
        result = r.json()
        if result:
            return result

def charity_search(search):
    params = {
        "query": search
    }
    r = requests.get(FINDTHATCHARITY_RECONCILE_URL, params=params)
    if r.status_code == requests.codes.ok:
        result = r.json()
        if len(result.get("result",[]))>0:
            return result["result"][0]["source"]

def make_message(char_data, user):
    char = {
        "title": char_data["known_as"]
    }

    if char_data.get("ccew_number"):
        regno = char_data["ccew_number"]
        char["website"] = 'http://beta.charitycommission.gov.uk/charity-details/?regid={}&subid=0'.format(regno)
        char["title"] = char["title"]
    elif char_data.get("ccni_number"):
        regno = "NIC{}".format(char_data["ccni_number"].replace("NIC", ""))
        char["website"] = char_data["ccni_link"]
    elif char_data.get("oscr_number"):
        regno = char_data["oscr_number"]
        char["website"] = char_data["oscr_link"]

    if char_data["url"] and char_data["url"] != "":
        char["website"] = char_data["url"]

    # correct common misformed URL in websites
    # @todo - make this a bit more robust
    if char["website"][0:4]!="http":
        char["website"] = "http://" + char["website"]
    
    if char_data.get("active"):
        template = '@{username} {name} [{regno}] {website}'
    else:
        template = '@{username} {name} [{regno} removed charity] {website}'

    return template.format(
                           username = user,
                           name=char["title"],
                           regno=regno,
                           website=char["website"]
                           )

if __name__ == "__main__":

    p = configargparse.ArgParser(ignore_unknown_config_file_keys=True)
    p.add('-c', '--my-config', default="example.cfg", is_config_file=True, help='config file path')

    # Twitter connection details
    p.add('--consumer-key', help='Twitter authorisation: consumer key')
    p.add('--consumer-secret', help='Twitter authorisation: consumer secret')
    p.add('--access-token', help='Twitter authorisation: access token')
    p.add('--access-token-secret', help='Twitter authorisation: access token secret')

    # Time to sleep between tweets (in seconds - default is one hour)
    p.add('-s', '--sleep', default=3600, type=int, help='Time to sleep between tweets (in seconds - default is one hour)')

    p.add("--debug", action='store_true', help="Debug mode (doesn't actually tweet)")

    options = p.parse_args()

    last_checked = datetime.now()
    if options.debug:
        last_checked = datetime(2017, 5, 10, 12, 0)

    # connect to Twitter API
    twitter = TwitterAPI(vars(options))
    print("Connected to twitter. User: [{}]".format( twitter.api.me().screen_name ) )
    print("Checking for new tweets every {} seconds".format( options.sleep ))

    while True:
        try:
            mentions = twitter.get_mentions()
        except tweepy.error.RateLimitError:
            time.sleep(180)
            print("<FAILED> Rate limit exceeded")
            continue
        
        for i in mentions:

            messages = []

            # exclude any tweets from before we last checked
            if i.created_at < last_checked:
                continue

            # exclude any tweets from us!
            if i.user.screen_name.lower()==TWITTER_USERNAME.lower():
                continue

            # try and find any registation numbers
            regnos = test_for_regno(i.text)

            for r in regnos:
                # get details about the charity from charitybase
                charity = get_charity(r)
                if not charity:
                    continue

                # construct the message
                message = make_message(charity, i.user.screen_name)
                if message:
                    messages.append(message)

            # try and find any search requests
            search = test_for_search(i.text)
            if search:
                charity = charity_search(search)
                ftc_search = requests.Request('GET', FINDTHATCHARITY_SEARCH_URL, params={"q": search}).prepare()
                if not charity:
                    messages.append("@{} Nothing found I'm afraid. Try {}".format(
                        i.user.screen_name, 
                        ftc_search.url
                    ))

                else:
                    # construct the message
                    message = make_message(charity, i.user.screen_name)
                    if message:
                        message += '. More results: {}'.format(ftc_search.url)
                        messages.append(message)


            # tweet out any tweets we need to
            for message in messages:

                print("<Tweet {} @{} {}>{}".format(i.id, i.user.screen_name, i.created_at, i.text))
                if options.debug:
                    print("<Reply to {}>{}".format(i.id, message))
                else:
                    try:
                        twitter.tweet(message, reply_to_id=i.id)
                        print("<Reply to {}>{}".format(i.id, message))
                    except tweepy.error.TweepError:
                        print("<FAILED Reply to {}>{}".format(i.id, message))
                        continue

        #print("Last checked {:%Y-%m-%d %H:%M:%S}".format(last_checked) )
        last_checked = datetime.now()
        time.sleep(options.sleep)
