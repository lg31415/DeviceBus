# -*- coding: utf-8 -*-
# !/usr/bin/env python
import socket
import threading
import time,datetime,json,httplib
DevBusHost="172.13.3.2"
FatApBusPort=9002
FitApBusPort=9003
APStatusSyncUri="/devicebus/getFitAPStatusSync.htm"
APSSIDStatusUri="/devicebus/getFitAPSSIDStatusSync.htm"
NASStatusSyncUri="/devicebus/getNASStatusSync.htm"
TsdbHost='127.0.0.1'
TsdbPort='6060'
TsdbUrl='/api/push'
def InputDataToApi(host, port, url, body):
    try:
        headers = {"Content-type": "application/json",
                   "Connection": "keep-alive",
                   }
        httpClient = httplib.HTTPConnection(host, port, timeout=60)
        httpClient.request("POST", url, body, headers)
        response = httpClient.getresponse()
        return response.read()
    except Exception, e:
        print e
    finally:
        if httpClient:
            httpClient.close()

def GetFatApStatus(cursor,MetricDeviceList,MetricUserList):
    DevBusFatapInfo=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    DevBusFatapInfo.connect((DevBusHost,FatApBusPort))
    DevBusFatapInfo.send('{"platform":"2571","version":"1.0","command":"getOnlineFatAPInfo","cursor":'+str(cursor)+'}\r\n')
    data=DevBusFatapInfo.recv(65536)
    DevBusFatapInfo.close()
    #DeviceStatus数据采集
    # print data
    MetricJsonMesage=""
    timestamp=int(time.mktime(datetime.datetime.now().timetuple()))
    for jsondata in json.loads(data)['data'] :
        for Metric in MetricDeviceList:
            jsonTag='devId='+str(jsondata['devId'])+",ssid="+str(jsondata['ssid'])+",ip="+str(jsondata['ip'])+",status="+str(jsondata['status'])+",wanProto="+str(jsondata['wanProto'])+','
            MetricJsonReport={'endpoint':str(jsondata['devMac']),"metric":"fatapinfo.get.status."+Metric,"value":str(jsondata[Metric]),"step":5,"counterType":"GAUGE","tags":jsonTag,"timestamp":timestamp}
            if MetricJsonMesage <>"":
                MetricJsonMesage= MetricJsonMesage+','+json.dumps(MetricJsonReport)
            elif MetricJsonMesage =="":
                MetricJsonMesage=MetricJsonMesage+json.dumps(MetricJsonReport)
            elif len(MetricJsonMesage)>65536:
                MetricJsonMesage="["+MetricJsonMesage+"]"
                InputDataToApi(TsdbHost,TsdbPort,TsdbUrl,MetricJsonMesage)
                MetricJsonMesage=''
            jsonUserdata = jsondata['userList']
            for MetricUser in MetricUserList:
                if jsonUserdata <> []:
                    for Userdata in json.loads(jsonUserdata):
                        jsonTag=jsonTag+'ip='+str(Userdata['ip']+'token='+str(Userdata['token']))
                        UserJsonReport={'endpoint':str(jsondata['userMac']),"metric":"fatapinfo.get.user."+ MetricUser,"value":str(jsonUserdata[MetricUser]),"step":5,"counterType":"GAUGE","tags":jsonTag,"timestamp":int(time.mktime(datetime.datetime.now().timetuple()))}
                        MetricJsonMesage=  MetricJsonMesage+','+json.dumps(UserJsonReport)
                        if len(MetricJsonMesage)>65536:
                            MetricJsonMesage="["+MetricJsonMesage+"]"
                            InputDataToApi(TsdbHost,TsdbPort,TsdbUrl,MetricJsonMesage)
                            MetricJsonMesage=''

    # print MetricJsonMesage
    MetricJsonMesage="["+MetricJsonMesage+"]"
    print InputDataToApi(TsdbHost,TsdbPort,TsdbUrl,MetricJsonMesage)
    #UserList数据
    return json.loads(data)["cursor"]
def GetFitApStatus(DeviceInfo,APMetricList,SsidMetricList,NasMetricList):
    timestamp=int(time.mktime(datetime.datetime.now().timetuple()))
    ApiParameter={'platform':DeviceInfo['platform'],'nasIp':DeviceInfo['nasip'],'vendor':DeviceInfo['vendor'],'readCom':DeviceInfo['readCom']}
    ApiRequest='data='+json.dumps(ApiParameter)
    print ApiRequest
    APStatusSyncData=InputDataToApi(DevBusHost,FitApBusPort,APStatusSyncUri,ApiRequest)
    APSSIDStatus=InputDataToApi(DevBusHost,FitApBusPort,APSSIDStatusUri,ApiRequest)
    NASStatusSync=InputDataToApi(DevBusHost,FitApBusPort,NASStatusSyncUri,ApiRequest)
    jsonTag='nasip='+DeviceInfo['nasip']+",vendor="+DeviceInfo['vendor']+",provice="+DeviceInfo['provice']+",city="+DeviceInfo['city']+","
    jsondata=""
    jsondata=json.loads(APStatusSyncData)['data']
    MetricJsonMesage=''
    if len(jsondata)>2:
        for devmac in  jsondata.keys():
            for ApMetric in APMetricList:
                APjsonTag=jsonTag+"fitapmac="+devmac+","
                ApJsonReport={"endpoint":devmac,"metric":"fitapinfo.get.apdevice."+ ApMetric,"value":str(jsondata[devmac][ApMetric]),"step":5,"counterType":"GAUGE","tags":APjsonTag,"timestamp":timestamp}
                if MetricJsonMesage <>"":
                    MetricJsonMesage= MetricJsonMesage+','+json.dumps(ApJsonReport)
                elif MetricJsonMesage =="":
                    MetricJsonMesage=MetricJsonMesage+json.dumps(ApJsonReport)
                elif len(MetricJsonMesage)>65536:
                    MetricJsonMesage="["+MetricJsonMesage+"]"
                    InputDataToApi(TsdbHost,TsdbPort,TsdbUrl,MetricJsonMesage)
                    MetricJsonMesage=''
    jsondata=""
    jsondata=json.loads(APSSIDStatus)['data']
    if len(jsondata)>2:
        for devmac in  jsondata.keys():
            for apssid in jsondata[devmac].keys():
                for SsidMetric in SsidMetricList:
                    SsidjsonTag=jsonTag+"fitapmac="+devmac+",fitssid="+apssid+","
                    ApJsonReport={"endpoint":apssid,"metric":"fitapinfo.get.ssidinfo."+ SsidMetric,"value":str(jsondata[devmac][apssid][SsidMetric]),"step":5 ,"counterType":"GAUGE","tags":SsidjsonTag,"timestamp":timestamp}
                    if MetricJsonMesage <>"":
                        MetricJsonMesage= MetricJsonMesage+','+json.dumps(ApJsonReport)
                    elif MetricJsonMesage =="":
                        MetricJsonMesage=MetricJsonMesage+json.dumps(ApJsonReport)
                    elif len(MetricJsonMesage)>65536:
                        MetricJsonMesage="["+MetricJsonMesage+"]"
                        InputDataToApi(TsdbHost,TsdbPort,TsdbUrl,MetricJsonMesage)
                        MetricJsonMesage=''

    jsondata=""
    jsondata=json.loads(NASStatusSync)['data']
    if len(jsondata)>2:
        for NasMetric in NasMetricList:
            NasjsonTag=jsonTag
            ApJsonReport={"endpoint":DeviceInfo["nasip"],"metric":"fitapinfo.get.nasdevice."+ NasMetric,"value":str(jsondata[NasMetric]),"step" :5,"counterType" : "GAUGE","tags": NasjsonTag,"timestamp":timestamp}
            if MetricJsonMesage <>"":
                MetricJsonMesage= MetricJsonMesage+','+json.dumps(ApJsonReport)
            elif MetricJsonMesage =="":
                MetricJsonMesage=MetricJsonMesage+json.dumps(ApJsonReport)
            elif len(MetricJsonMesage)>65536:
                MetricJsonMesage="["+MetricJsonMesage+"]"
                InputDataToApi(TsdbHost,TsdbPort,TsdbUrl,MetricJsonMesage)
                MetricJsonMesage=''
        MetricJsonMesage="["+MetricJsonMesage+"]"
        print InputDataToApi(TsdbHost,TsdbPort,TsdbUrl,MetricJsonMesage)
while True:
    try:
        FitApList = open("FitAp.list","r")
        for FitAp in FitApList:
            try:
                DeviceInfo=eval(FitAp)
                GetFitApStatus(DeviceInfo,['downFlow','upFlow','userOnlineNum','userConnSum'],['downFlow','upFlow','userOnlineNum','userConnSum'],['downFlow','upFlow','apOnlineNum'])
            except:
                DeviceInfo=eval(FitAp)
                GetFitApStatus(DeviceInfo,['downFlow','upFlow','userOnlineNum','userConnSum'],['downFlow','upFlow','userOnlineNum','userConnSum'],['downFlow','upFlow','apOnlineNum'])
                continue        
	FitApList.close()
        time.sleep(1200)
    except Exception as e:
        FitApList.close()
	print e
        time.sleep(1200)
'''
while True:
    FitApList = open("FitAp.list","r")
    for FitAp in FitApList:
        API=eval(FitAp)
        GetFitApStatus(API,['downFlow','upFlow'],['downFlow','upFlow'],['downFlow','upFlow'])
    FitApList.close()
    time.sleep(1200)
'''
