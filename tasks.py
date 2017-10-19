import requests
import matplotlib.pyplot as plt
from pandas.tools.plotting import table
import pandas as pd
import json
import numpy as np
import six
from celery import Celery
import time
from datetime import datetime


host = "https://YOURPUBLICIP:7000/"

celery = Celery('tasks', broker='pyamqp://guest@localhost//')

@celery.task
def sendTextResponse(responseUrl, text,response_type):
    data = {
        # Uncomment the line below for the response to be visible to everyone
        'response_type': response_type,
        'text': text
    }
    requests.post(responseUrl, json=data)


def createAlertResponse(alert,currentPrice,text,responseUrl):
#def createAlertResponse(symbol,setPrice,currentPrice,exchange,text,responseUrl,username):
    data = {
        # Uncomment the line below for the response to be visible to everyone
        'response_type': 'in_channel',
        'text': text + " | " + str(alert['symbol']) + " | original: " + str(alert['originalPrice']) +" | set: "  + str(alert['setPrice']) + " | current: " + str(currentPrice) + " | " + str(alert['market']) + " | " + str(alert['username']) + " | " + str(alert['timestamp'])
    }
    requests.post(responseUrl, json=data)

def removeAlertRequest(timestamp):
    requests.get(host + "removealert/" + timestamp)

@celery.task
def sendAlert(alerts,alert,webhook,marketinfo):
    btcUSD = marketinfo['BTC/USDT']['last']
    if(alert['symbol'] == "BTC"):
        currentPrice = float(btcUSD)
    else:
        pair = str(alert['symbol'] + '/BTC')
        currentPrice = marketinfo[pair]['last'] * btcUSD
    if(alert['type'] == 'low'):
        if(currentPrice <= float(alert['setPrice'])):
            createAlertResponse(alert,currentPrice,"Price reached",webhook)
            removeAlertRequest(alert['timestamp'])
    elif(alert['type'] == 'high'):
        if(currentPrice >= float(alert['setPrice'])):
            createAlertResponse(alert,currentPrice,"Price reached",webhook)
            removeAlertRequest(alert['timestamp'])
            

@celery.task
def updateAllCoinHelper(args,json_data,responseUrl):
    series = []
    pair = args[0] + "-USD"
    pair2 = args[0] + "-BTC"
    unix_timestamp = str(int(time.time()))
    timestamp = str(datetime.now())
    filename = args[0]  + unix_timestamp + ".png"
    text ="update " + args[0] + " " + timestamp
    for market in json_data:
        if market['pair'] == pair or market['pair'] == pair2:
            series.append(pd.Series(market))
    df = pd.DataFrame(series)
    df.sort_values(by='exchange')
    drawTable(df,filename,header_columns=0, col_width=3)
    jsonImageSend(str(text),filename,responseUrl)

@celery.task
def updateCoinHelper(args,exchange,responseUrl):
    print("updatecoinhelper")
    if(args[0] == 'BTC'):
        #index = next(index for (index, d) in enumerate(data) if d['market'] == str(args[0] + "-USDT"))
        pair = 'BTC/USDT'
        data = exchange.fetch_ticker(pair)
        currentPrice = data['last']
        bid = data['bid']
        ask = data['ask']
        high = data['high']
        low = data['low']
    else:
        #index = next(index for (index, d) in enumerate(data) if d['market'] == str(args[0] + "-BTC"))
        pair = args[0] + '/BTC'
        btcUSD = exchange.fetch_ticker('BTC/USDT')['last']
        data = exchange.fetch_ticker(pair)
        currentPrice = float(data['last'] * btcUSD)
        bid = float(data['bid']) * float(btcUSD)
        ask = float(data['ask']) * float(btcUSD)
        high = float(data['high']) * float(btcUSD)
        low = float(data['low']) * float(btcUSD)
    vol = data['quoteVolume']
    sell = data['info']['OpenSellOrders']
    buy = data['info']['OpenBuyOrders']
    response = str(currentPrice) + " | bid: " + str(bid) + " | ask: " + str(ask) + " | high 24h: " + str(high) + " | low 24h:" + str(low) + " | sellorders: " + str(sell) + " | buyorders: " + str(buy) + " | volume: " + str(vol)
    requests.post(responseUrl, json={
        # Uncomment the line below for the response to be visible to everyone
        'response_type': 'in_channel',
        'text': "Last Price " + args[0] + ": " + response +  " | " + args[1]
    })

@celery.task
def gainerLoserHelper(args,responseUrl,json_data,query):
    series = []
    unix_timestamp = str(int(time.time()))
    timestamp = str(datetime.now())
    filename = query  + args[0]  + unix_timestamp + ".png"
    text ="top " + query + " " + args[0] + " " + timestamp
    for coins in json_data:
        series.append(pd.Series(coins))
    df = pd.DataFrame(series).set_index("symbol")
    drawTable(df,filename,header_columns=0, col_width=2.5)
    jsonImageSend(str(text),filename,responseUrl)


def drawTable(data,filename,col_width=3.0, row_height=0.625, font_size=14,
                     header_color='#40466e', row_colors=['#f1f1f2', 'w'], edge_color='w',
                     bbox=[0, 0, 1, 1], header_columns=0,
                     ax=None, **kwargs):
    if ax is None:
        size = (np.array(data.shape[::-1]) + np.array([0, 1])) * np.array([col_width, row_height])
        print (size)
        fig, ax = plt.subplots(figsize=size)
        ax.axis('off')

    mpl_table = ax.table(cellText=data.values, bbox=bbox, colLabels=data.columns, **kwargs)

    mpl_table.auto_set_font_size(False)
    mpl_table.set_fontsize(font_size)

    for k, cell in six.iteritems(mpl_table._cells):
        cell.set_edgecolor(edge_color)
        if k[0] == 0 or k[1] < header_columns:
            cell.set_text_props(weight='bold', color='w')
            cell.set_facecolor(header_color)
        else:
            cell.set_facecolor(row_colors[k[0]%len(row_colors) ])
    plt.savefig( "images/" + filename , transparent=True)

def jsonImageSend(text,filename,responseUrl):
    print("Sending image")
    imgPath = str(host + "images/" + filename)
    print(imgPath)
    return requests.post(responseUrl, json={
        # Uncomment the line below for the response to be visible to everyone
        'response_type': 'in_channel',
        'text': text,
        'attachments': [
            {
            	"title": text,
                "image_url": imgPath
            }
        ]
    })

def findindex(lst, key, value):
    for i, dic in enumerate(lst):
        if dic[key] == value:
            return i
    return -1

def search(list,key,value):
    return [element for element in list if element[key] == value]