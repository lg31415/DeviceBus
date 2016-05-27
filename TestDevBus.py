#!/usr/bin/env python
#-*-coding:utf-8-*-
import socket,thread,time,datetime,json,httplib,os,sqlite3
DevBusHost = "172.30.1.131"
FatApBusPort = 9011
FitApBusPort = 9003
def DevBusRequset(DevBusFatapInfo,cursor):
    DevBusFatapInfo.send('{"platform":"2571","version":"1.0","command":"getOnlineFatAPInfo","cursor":'+str(cursor)+'}\r\n')
    data=b''
    while True:
        buff=DevBusFatapInfo.recv(4096)
        data=data+buff
        if data.endswith('\r\n') :
            break
    for jsondata in json.loads(data)['data'] :
        print  str(jsondata['devId'])+","+str(jsondata['devMac'])
        for MetricUser in jsondata['userList']:
            print "UserMAC="+MetricUser['userMac']
    return json.loads(data)["cursor"]
i=0
while True:
    DevBusFatapInfo = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    DevBusFatapInfo.connect((DevBusHost, FatApBusPort))
    i =DevBusRequset(DevBusFatapInfo,i)
    if i==0:
        DevBusFatapInfo.close()
        break

