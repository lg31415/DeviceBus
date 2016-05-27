# -*- coding: utf-8 -*-
# !/usr/bin/env python
import socket,thread,time,datetime,json,httplib,os,sqlite3
from ipip import IP
DevBusHost = "172.30.1.131"
FatApBusPort = 9011
FitApBusPort = 9003
APStatusSyncUri = "/devicebus/getFitAPStatusSync.htm"
APSSIDStatusUri = "/devicebus/getFitAPSSIDStatusSync.htm"
NASStatusSyncUri = "/devicebus/getNASStatusSync.htm"
TsdbHost = '127.0.0.1'
TsdbPort = '6060'
TsdbUrl = '/api/push'
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
def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d
def GetAreaStr(ip):
    IP.load(os.path.abspath("mydata4vipweek2.dat"))
    Key=['country','province','city','county','isp','ip']
    Area=IP.find(ip).split('\t')
    Area.append(ip)
    ResultStr=''
    CodeValue=''
    Mesage=dict(zip(Key,Area))
    for key in Mesage.keys():
        if  key=='country':
            CodeValue=Get_Area_Code(Mesage[key],'COUNTRY')
        elif key=='province':
            CodeValue=Get_Area_Code(Mesage[key],'PROVINCE')
        elif key=='city':
            CodeValue=Get_Area_Code(Mesage[key],'CITY')
        elif key=='county':
            CodeValue=Get_Area_Code(Mesage[key],'COUNTY')
        elif key=='isp':
            CodeValue=Get_Area_Code(Mesage[key],'ISP')
        elif key=='ip':
            CodeValue=Mesage[key]
        if key in ['province','city']:
             ResultStr=ResultStr+key+"="+str(CodeValue)+ ','
    return ResultStr
def Get_Device_list(Devicetype):
    try:
        conn = sqlite3.connect("db.sqlite3")
        conn.row_factory = dict_factory
        curs = conn.execute("SELECT * FROM queryapi_deviceinfo WHERE status=0 AND devicetype = '%s'" % Devicetype)
        Data = curs.fetchall()
        conn.close()
        return Data
    except:
        return ''
def Get_Area_Code(AreaName,Areatype):
    try:
        conn = sqlite3.connect("db.sqlite3")
        curs = conn.execute("SELECT area_code FROM queryapi_areacode WHERE area_name='%s'" % AreaName + " AND area_type = '%s'" % Areatype)
        Data = curs.fetchone()[0]
        conn.close()
        return Data
    except:
        return 'Unknown'
def GetFatApStatus(DevBusFatapInfo,cursor,timestamp,MetricDeviceList,MetricUserList):
    DevBusFatapInfo.send('{"platform":"2571","version":"1.0","command":"getOnlineFatAPInfo","cursor":'+str(cursor)+'}\r\n')
    data=b''
    while True:
        buff=DevBusFatapInfo.recv(4096)
        data=data+buff
        if data.endswith('\r\n') :
            break    
    MetricJsonMesage=""
    for jsondata in json.loads(data)['data'] :
        for Metric in MetricDeviceList:
            #jsonTag=GetAreaStr(jsondata['ip'])+'devId='+str(jsondata['devId'])+",ssid="+str(jsondata['ssid'])+',ipaddr='+jsondata['ip']+','
            jsonTag=GetAreaStr(jsondata['ip'])+",ssid="+str(jsondata['ssid'])+',ipaddr='+jsondata['ip']+','
            MetricJsonReport={'endpoint':str(jsondata['devMac']),"metric":"fatapinfo.get.status."+Metric,"value":str(jsondata[Metric]),"step":5,"counterType":"GAUGE","tags":jsonTag,"timestamp":timestamp}
#胖AP设备中状态信息采集
            if MetricJsonMesage !="":
                MetricJsonMesage= MetricJsonMesage+','+json.dumps(MetricJsonReport)
            elif MetricJsonMesage =="":
                MetricJsonMesage=MetricJsonMesage+json.dumps(MetricJsonReport)
            elif len(MetricJsonMesage)>65536:
                MetricJsonMesage="["+MetricJsonMesage+"]"
                InputDataToApi(TsdbHost,TsdbPort,TsdbUrl,MetricJsonMesage)
                MetricJsonMesage=''
            jsonUserdata = jsondata['userList']
            MetricJsonReport={'endpoint':str(jsondata['devMac']),"metric":"fatapinfo.get.status.usercount","value" : len(jsonUserdata),"step" : 5,"counterType" : "GAUGE","tags" : jsonTag,"timestamp" : timestamp}
            MetricJsonMesage = MetricJsonMesage + ',' + json.dumps(MetricJsonReport)
            # for MetricUser in MetricUserList:
            #     if jsonUserdata != []:
            #         for Userdata in json.loads(jsonUserdata):
            #             jsonTag=jsonTag+'ip='+str(Userdata['ip']+'token='+str(Userdata['token']))
            #             UserJsonReport={'endpoint':str(jsondata['userMac']),"metric":"fatapinfo.get.user."+ MetricUser,"value":str(jsonUserdata[MetricUser]),"step":5,"counterType":"GAUGE","tags":jsonTag,"timestamp":int(time.mktime(datetime.datetime.now().timetuple()))}
            #             MetricJsonMesage=  MetricJsonMesage+','+json.dumps(UserJsonReport)
            #             if len(MetricJsonMesage)>65536:
            #                 MetricJsonMesage="["+MetricJsonMesage+"]"
            #                 InputDataToApi(TsdbHost,TsdbPort,TsdbUrl,MetricJsonMesage)
            #                 MetricJsonMesage=''
#  胖AP的用户信息采集
    MetricJsonMesage="["+MetricJsonMesage+"]"
    InputDataToApi(TsdbHost,TsdbPort,TsdbUrl,MetricJsonMesage)
    return json.loads(data)["cursor"]


def GetFitApStatus(FitApObj,APMetricList,SsidMetricList,NasMetricList):
    timestamp=int(time.mktime(datetime.datetime.now().timetuple()))
    ApiRequest='data='+json.dumps({'platform':FitApObj['platform'],'nasIp':FitApObj['nasip'],'vendor':FitApObj['vendor'],'readCom':FitApObj['readcom']})
    print ApiRequest
    APStatusSyncData=InputDataToApi(DevBusHost,FitApBusPort,APStatusSyncUri,ApiRequest)
    APSSIDStatus=InputDataToApi(DevBusHost,FitApBusPort,APSSIDStatusUri,ApiRequest)
    NASStatusSync=InputDataToApi(DevBusHost,FitApBusPort,NASStatusSyncUri,ApiRequest)
    jsonTag="nasIp="+ FitApObj['nasip']+",vendor="+FitApObj['vendor']+",province="+FitApObj['province']+",city="+FitApObj['city'] +","
    jsondata=json.loads(APStatusSyncData)['data']
    MetricJsonMesage=''
    if jsondata:
        for devmac in  jsondata.keys():
            for ApMetric in APMetricList:
                APjsonTag=jsonTag+"fitapmac="+devmac+","
                ApJsonReport={"endpoint":devmac,"metric":"fitapinfo.get.apdevice."+ ApMetric,"value":str(jsondata[devmac][ApMetric]),"step":5,"counterType":"GAUGE","tags":APjsonTag,"timestamp":timestamp}
                if MetricJsonMesage !="":
                    MetricJsonMesage= MetricJsonMesage+','+json.dumps(ApJsonReport)
                elif MetricJsonMesage =="":
                    MetricJsonMesage=MetricJsonMesage+json.dumps(ApJsonReport)
                elif len(MetricJsonMesage)>65536:
                    MetricJsonMesage="["+MetricJsonMesage+"]"
                    InputDataToApi(TsdbHost,TsdbPort,TsdbUrl,MetricJsonMesage)
                    MetricJsonMesage=''
    jsondata=json.loads(APSSIDStatus)['data']
    if jsondata:
        for devmac in  jsondata.keys():
            for apssid in jsondata[devmac].keys():
                for SsidMetric in SsidMetricList:
                    SsidjsonTag=jsonTag+"fitapmac="+devmac+",fitapssid="+apssid+","
                    ApJsonReport={"endpoint":apssid,"metric":"fitapinfo.get.ssidinfo."+ SsidMetric,"value":str(jsondata[devmac][apssid][SsidMetric]),"step":5 ,"counterType":"GAUGE","tags":SsidjsonTag,"timestamp":timestamp}
                    if MetricJsonMesage !="":
                        MetricJsonMesage= MetricJsonMesage+','+json.dumps(ApJsonReport)
                    elif MetricJsonMesage =="":
                        MetricJsonMesage=MetricJsonMesage+json.dumps(ApJsonReport)
                    elif len(MetricJsonMesage)>65536:
                        MetricJsonMesage="["+MetricJsonMesage+"]"
                        InputDataToApi(TsdbHost,TsdbPort,TsdbUrl,MetricJsonMesage)
                        MetricJsonMesage=''

    jsondata=json.loads(NASStatusSync)['data']
    if jsondata:
        for NasMetric in NasMetricList:
            NasjsonTag=jsonTag
            ApJsonReport={"endpoint":FitApObj['nasip'],"metric":"fitapinfo.get.nasdevice."+ NasMetric,"value":str(jsondata[NasMetric]),"step" :5,"counterType" : "GAUGE","tags": NasjsonTag,"timestamp":timestamp}
            if MetricJsonMesage !="":
                MetricJsonMesage= MetricJsonMesage+','+json.dumps(ApJsonReport)
            elif MetricJsonMesage =="":
                MetricJsonMesage=MetricJsonMesage+json.dumps(ApJsonReport)
            elif len(MetricJsonMesage)>65536:
                MetricJsonMesage="["+MetricJsonMesage+"]"
                InputDataToApi(TsdbHost,TsdbPort,TsdbUrl,MetricJsonMesage)
                MetricJsonMesage=''
        MetricJsonMesage="["+MetricJsonMesage+"]"
        #print InputDataToApi(TsdbHost,TsdbPort,TsdbUrl,MetricJsonMesage)
        print InputDataToApi(TsdbHost,TsdbPort,TsdbUrl,MetricJsonMesage)
def FatApQuery():
    try:
    	DevBusFatapInfo=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    	DevBusFatapInfo.connect((DevBusHost,FatApBusPort))
        i=0
        timestamp=int(time.mktime(datetime.datetime.now().timetuple()))
        while True:
            i=GetFatApStatus(DevBusFatapInfo,i,timestamp,['memfree'],['downFlow'])
            if i==0:
		#break
		time.sleep(600)
    		timestamp=int(time.mktime(datetime.datetime.now().timetuple()))
		continue
    except Exception as e:
        print e
	DevBusFatapInfo.close()
        time.sleep(600)
#    thread.exit_thread()
def FitApQuery():
    try:
        FitApList = Get_Device_list('NAS')
        for FitAp in FitApList:
            try:
                GetFitApStatus(FitAp,['downFlow','upFlow','userOnlineNum','userConnSum'],['downFlow','upFlow','userOnlineNum','userConnSum'],['downFlow','upFlow','apOnlineNum'])
            except:
                continue
        	time.sleep(600)
    except Exception as e:
        print e
        time.sleep(600)
#    thread.exit_thread()
#def StartQuery():
#    thread.start_new_thread(FatApQuery, ())
#    thread.start_new_thread(FitApQuery, ())
# FitApQuery()
#GetFatApStatus(0,['cpu','memfree'],['upFlow','downFlow'])
#i=0
#while True:
#    i=GetFat(i)
#    print i
#    if i==0:
#	time.sleep (600)
