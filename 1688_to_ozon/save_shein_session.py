import requests
import json

url='https://www.ebay.com/itm/358165965187'
username = 'papper'
apiKey = 'ybhcFLbr822nL3iNOLXCwKblQ'

apiEndPoint = "http://api.scraping-bot.io/scrape/retail"

options = {
    "useChrome": False,#set to True if you want to use headless chrome for javascript rendering
    "premiumProxy": False, # set to True if you want to use premium proxies Unblock Amazon,Google,Rakuten
    "proxyCountry": "US", # allows you to choose a country proxy (example: proxyCountry:"FR")
    "waitForNetworkRequests":False # wait for most ajax requests to finish until returning the Html content (this option can only be used if useChrome is set to true),
                                   # this can slowdown or fail your scraping if some requests are never ending only use if really needed to get some price loaded asynchronously for example
}

payload = json.dumps({"url":url,"options":options})
headers = {
    'Content-Type': "application/json"
}

response = requests.request("POST", apiEndPoint, data=payload, auth=(username,apiKey), headers=headers)

print(response.text)