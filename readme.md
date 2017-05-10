# Charity Mention bot

A bot that replies to mentions to the @CharityRandom twitter account.

## Interact with the bot

There are two ways to activate it:

### Mention a charity number

Send a tweet to @CharityRandom with a charity number and it will try to find
the charity:

https://twitter.com/kanedr/status/862390264115191809

https://twitter.com/CharityRandom/status/862399729002586114

### Do a search

Send a tweet in the format "@CharityRandom search: <search terms>" and it will
return the largest charity it can find matching the search.



## Data source

The service uses the fabulous [CharityBase](http://charitybase.uk/) to get
charity information. The data in CharityBase is from the Charity Commission
and is opened up under the Open Government Licence. This bot has no connection
to either CharityBase or the Charity Commission.
