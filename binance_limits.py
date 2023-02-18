
"""
https://www.binance.com/en/support/faq/rate-limits-on-binance-futures-281596e222414cdd9051664ea621cdc3
https://binance-docs.github.io/apidocs/spot/en/#general-api-information
https://www.binance.com/en/support/faq/api-frequently-asked-questions-360004492232


When a 429 is received,
it's your obligation as an API to back off and not spam the API.
Repeatedly violating rate limits and/or failing to back off after
receiving 429s will result in an automated IP ban (HTTP status 418).

Order Rate Limits
Every order response will contain a X-MBX-ORDER-COUNT-(intervalNum)(intervalLetter)
header which has the current order count for the account for all order
rate limiters defined.

Hard-Limits:
1,200 request weight per minute (keep in mind that this is not necessarily the same as 1,200 requests)
50 orders per 10 seconds
160,000 orders per 24 hours
Our hard-limits are listed on the [/api/v3/exchangeInfo] endpoint.
"""



# REQUESTS LIMIT
MINUTE_LIMIT = 1_200

# ORDERS LIMIT
DAY_LIMIT = 160_000
SEC_10_LIMIT = 50

base_url = "https://fapi.binance.com"
symbol = 'XRPUSDT'

red_ch = '\u001b[31m'
yellow_ch = '\u001b[38;5;11m'
reset_ch = '\u001b[0m'