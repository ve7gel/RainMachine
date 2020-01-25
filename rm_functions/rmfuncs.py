#!/usr/bin/env python3
"""
This is a NodeServer for Green Electronics Rainmachine for Polyglot v2 written in Python3
by Gordon Larsen
MIT License

"""
import json
import requests
from polyinterface import LOGGER

def getRainmachineToken(password, top_level_url):
    # request an access token from the RainMachine, to be used in subsequent calls
    api_request = "api/4/auth/login"
    data = {
        "pwd": password,
        "remember": 1
    }

    headers = {
        'Content-Type': 'application/json'
    }

    r = requests.post(top_level_url + api_request, data=json.dumps(data), headers=headers, verify=False)
    rmdata = r.content
    access_token = json.loads(rmdata)['access_token']

    return access_token

def getRmZones(url, access_token):
    try:
        response = requests.get(url + 'api/4/zone' + access_token, verify=False)
        rm_zone_data = json.loads(response.content)

    except:
        LOGGER.error("Can't get zone update")

    return rm_zone_data

def rmHeartBeat(url, access_token):
    try:
        response = requests.get(url + 'api/4/diag' + access_token, verify=False)
        #LOGGER.debug(response.content)
        if response.status_code == 200:
            return 1
        elif response.status_code != 200:
            return 0
    except:
        return 0

def GetRmRainSensorState(url, access_token):
    try:
        response = requests.get(url + 'api/4/restrictions/currently' + access_token, verify=False)
        rm_data = json.loads(response.content)
        if rm_data['rainDelay'] == True:
            rd = 1
        else:
            rd = 0

        if rm_data['rainSensor'] == True:
            rs = 1
        else:
            rs = 0
        if rm_data['freeze'] == True:
            fr = 1
        else:
            fr = 0

        return rd,rs,fr

    except:
        LOGGER.debug('Error getting rain sensor info')

def RmZoneProperties(url, access_token):
    try:
        response = requests.get(url + 'api/4/zone' + access_token, verify=False)
        rm_zone_data = json.loads(response.content)

        return rm_zone_data

    except:
        LOGGER.error('Unable to get zone properties')
        return ""

