from pymarketcap import Pymarketcap
import json, decimal
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import logging
import tasks
import time
import simplejson as simplejson
import pickle
from pathlib import Path
import ccxt



class coinmarkets(object):
    def __init__(self,app):
        self.app = app
        self.webhook = "YOUR SLACK WEBHOOK"
        self.coinmarketcap = Pymarketcap()
        self.bittrex = ccxt.bittrex()
        self.poloniex = ccxt.poloniex()
        self.quadraigacx = ccxt.poloniex()
        self.exchanges = {'bittrex':self.bittrex,'poloniex':self.poloniex,'quadraigacx':self.quadraigacx,'coinmarketcap':self.coinmarketcap}
        self.loadMarkets()
        self.dispatch_map = {'showalert':self.showAlert,'removealert':self.removeAlert,'alert' : self.createAlert, 'topten' : self.topten, 'updatecoin' : self.updatecoin, 'gainers': self.gainers, 'losers': self.losers,'symbols':self.symbols}
        alertFile = Path("alert.p")
        if alertFile.is_file():
            self.alerts = pickle.load(open('alert.p', "rb"))
        else:
            self.alerts = []
        self.symbols = []
        self.timeframe = ['7d', '24h', '1h']
        self.symbols = self.coinmarketcap.symbols
        self.coinmarket_latestinfo = [] 
        self.bittrex_latestinfo = []
        self.poloniex_latestinfo = []
        self.quadraigacx_latestinfo = []
        scheduler = BackgroundScheduler()
        scheduler.add_job(self.refreshinfo, 'interval', seconds=20)
        logging.basicConfig()
        scheduler.start()

    def parseCommand(self,command,text,responseUrl,username):
        args = tuple(text.split())
        #method = getattr(self, method_name, lambda: "nothing")
        print (text)
        print (args)
        print (command)
        if args:
            self.dispatch_map[command](args, responseUrl, username)
        else:
            self.dispatch_map[command](["empty"], responseUrl, username)
        return "processing request"
    def loadMarkets(self):
        self.bittrex.loadMarkets()
        self.poloniex.loadMarkets()
        self.quadraigacx.loadMarkets()

    def showAlert(self,args,responseUrl,username):
        if args[0] == "empty":
            results = tasks.search(self.alerts,'username',username)
            if not results:
                tasks.sendTextResponse(responseUrl, "no alerts found for " + username , "ephemeral")
            else:
                data = simplejson.dumps(self.alerts, use_decimal=True)
                tasks.sendTextResponse(responseUrl, data, "ephemeral")
        else:
            if args[0] == "all":
                data = simplejson.dumps(self.alerts, use_decimal=True)
                tasks.sendTextResponse(responseUrl, data, "ephemeral")
                #tasks.sendJsonResponse(responseUrl, "all alerts" , data, "ephemeral")
            else:
                tasks.sendTextResponse(responseUrl, "invalid command", "ephemeral")


    def createAlert(self,args,responseUrl,username):
        # args = [cointype,price,market]
        btcUSD = 0
        timestamp = str(int(time.time()))
        if len(args) < 3:
            return "invalid command"
        else:
            market = args[2]

        if args[0] in self.symbols:
            symbol = str(args[0])
            if(symbol == "BTC"):
                pair = "BTC/USDT"
                exchange = self.exchanges[args[2]]
                currentPrice = exchange.fetch_ticker(pair)['last']
            else:
                pair = symbol + "/BTC"
                exchange =  self.exchanges[args[2]]
                results = exchange.fetch_ticker(pair)
                if not results:
                    return tasks.sendTextResponse(responseUrl, "currency not found in " + market, "ephemeral")
                else:
                    btcUSD = exchange.fetch_ticker('BTC/USDT')['last']
                    currentPrice = float(results['last'] * btcUSD)

            if('%' in args[1]):
                change = args[1].replace('%', ' ')
                if('-' in change):
                    change = float(change.replace('-', ' '))
                    percentage = float((100 - change) / 100)
                    setPrice = float(percentage * float(currentPrice))
                else:
                    percentage = float((100 + float(change)) / 100)
                    setPrice = float(percentage * float(currentPrice))
            else:
                setPrice = float(args[1])
            if float(currentPrice) < setPrice:
                    alertType = "high"
            elif float(currentPrice) > setPrice:
                    alertType = 'low' #alert when the price is lower than the setPrice
            else:
                return tasks.sendTextResponse(responseUrl,"error: current price == set price","ephemeral")

            alert = {'symbol':symbol,'setPrice':setPrice,'market':market,'originalPrice':currentPrice,'type':alertType,'username':username,"timestamp":timestamp}
            self.alerts.append(alert)
            pickle.dump(self.alerts,open( "alert.p", "wb" ))
            tasks.createAlertResponse(alert, str(currentPrice),"Alert Created", responseUrl)
            return tasks.sendTextResponse(responseUrl,"command received","ephemeral")
        else:
            return tasks.sendTextResponse(responseUrl,"invalid command","ephemeral")

    def topten(self,args1,responseUrl,username):
        results = self.coinmarketcap.ticker(limit=10)
        results = results[0]
        print (results)
        return json.dumps(results,default=decimal_default)

    def updatecoin(self,args,responseUrl,username):
        if len(args) < 2:
            market = self.coinmarketcap.ticker(args[0], convert='USD')
            percentChange = " | 1h: " +  str(market['percent_change_1h']) + " % " + " | 24h: " + str(market['percent_change_24h']) + " % " + " | 7d: " + str(market['percent_change_7d']) + " % "
            text = str("Current Price for " + str(args[0]) + ": " + str(market['price_usd']) +  percentChange + " | " + "coinmarketcap")
            return tasks.sendTextResponse(responseUrl,text,"in_channel")
        elif args[1] == "all":
            data = self.coinmarketcap.markets(args[0])
            tasks.updateAllCoinHelper.delay(args, data, responseUrl)
        else:
            #data = self.coinmarketcap.exchange(args[1])
            exchange = self.exchanges[args[1]]
            tasks.updateCoinHelper(args,exchange,responseUrl,)
            return tasks.sendTextResponse(responseUrl,"updatecoin received","ephemeral")

        return "command received"

    def symbols(self,args1,responseUrl,username):
        print (args1)
        print (self.coinmarketcap.symbols)

        return json.dumps(self.coinmarketcap.symbols)

    def gainers(self,args,responseUrl,username):
        if args[0] == "empty" or args[0] not in self.timeframe or args[0] == "1h":
            args[0] = '1h'
            json_data = (self.coinmarketcap.ranks('gainers',args[0])[args[0]])
        elif args[0] == '24h':
            json_data = (self.coinmarketcap.ranks('gainers',args[0])[args[0]])
        elif args[0] == '7d':
            json_data = (self.coinmarketcap.ranks('gainers',args[0])[args[0]])
        else:
            return tasks.sendTextResponse(responseUrl,"invalid timeframe","ephemeral")
        tasks.gainerLoserHelper.delay(args,responseUrl,json_data,"gainers")  
        return tasks.sendTextResponse(responseUrl,"top gainers received","ephemeral")

    def losers(self,args,responseUrl,username):
        if args[0] == "empty" or args[0] not in self.timeframe or args[0] == "1h":
            json_data = (self.coinmarketcap.ranks('losers','1h')['1h'])
        elif args[0] == '24h':
            json_data = (self.coinmarketcap.ranks('losers',args[0])[args[0]])
        elif args[0] == '7d':
            json_data = (self.coinmarketcap.ranks('losers',args[0])[args[0]])
        else:     
            return tasks.sendTextResponse(responseUrl,"invalid timeframe","ephemeral")
        tasks.gainerLoserHelper.delay(args,responseUrl,json_data,"losers")  
        return tasks.sendTextResponse(responseUrl,"top losers received","ephemeral")


    def refreshinfo(self):
        #self.coinmarket_latestinfo = self.coinmarketcap.ticker(limit=20)
        self.bittrex_latestinfo = self.bittrex.fetch_tickers()
        self.poloniex_latestinfo = self.poloniex.fetch_tickers()
        self.quadrigacx_latestinfo = self.quadraigacx.fetch_tickers()
        self.evaluateAlert(self.alerts)

    def removeAlert(self,args,responseUrl,username):
        for i,alert in enumerate(self.alerts):
            if alert['timestamp'] == args[0]:
                self.alerts.pop(i)
                pickle.dump(self.alerts, open("alert.p", "wb"))
                print("alerts list")
                print(*self.alerts)
                if responseUrl != "empty":
                    return tasks.sendTextResponse(responseUrl,"alert "+ alert['timestamp'] + " removed","ephemeral")
                return "alert "+ alert['timestamp'] + " removed"
        if responseUrl != "empty":
            return tasks.sendTextResponse(responseUrl,"alert not found","ephemeral")
        return "alert not found"

    def evaluateAlert(self,alerts):
        if not alerts:
            return
        else:
            for i,alert in enumerate(alerts):
                alertType = alert["type"]
                if alert['market'] == 'coinmarketcap':
                    currentPrice = float(self.coinmarketcap.ticker(alert['symbol'], convert='USD')['price_usd'])
                    if alertType == 'low':
                        if(currentPrice <= float(alert['setPrice'])):
                            data = tasks.createAlertResponse(alert,currentPrice,"Price reached",self.webhook)
                            requests.post(self.webhook, json=data)
                            alerts.pop(i)
                    elif alertType == 'high':
                        if(currentPrice >= float(alert['setPrice'])):
                            data = tasks.createAlertResponse(alert,currentPrice,"Price reached",self.webhook)
                            requests.post(self.webhook, json=data)
                            alerts.pop(i)
                elif alert['market'] == 'bittrex':
                    tasks.sendAlert.delay(alerts,alert,self.webhook,self.bittrex_latestinfo)
                elif alert['market'] == 'quadrigacx':
                    tasks.sendAlert.delay(alerts,alert,self.webhook,self.quadrigacx_latestinfo)
                elif alert['market'] == 'poloniex':
                    tasks.sendAlert.delay(alerts,alert,self.webhook,self.poloniex_latestinfo)



def decimal_default(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    raise TypeError

