#!/usr/bin/env python3
"""
This is a NodeServer for Green Electronics Rainmachine for Polyglot v2 written in Python3
by Gordon Larsen
MIT License

"""
import json
import subprocess as sp

import requests
from polyinterface import LOGGER


def getRainmachineToken(password, top_level_url):
    # request an access token from the RainMachine, to be used in subsequent calls
    access_token = {}
    api_request = "api/4/auth/login"
    data = {
        "pwd": password,
        "remember": 1
    }

    headers = {
        'Content-Type': 'application/json'
    }
    try:
        r = requests.post(top_level_url + api_request, data=json.dumps(data), headers=headers, verify=False)
        rmdata = r.content
        access_token = json.loads(rmdata)['access_token']
    except:
        LOGGER.error("Incorrect hostname or password")
        return None

    return access_token

def RmApiGet(url, access_token,api_call):

    try:
        response = requests.get(url + api_call + access_token, verify=False)
        rm_zone_data = json.loads(response.content)

    except:
        LOGGER.error("RM API get failed")
        return None

    return rm_zone_data

def rmHeartBeat(host, timeout):

    try:
        response, result = sp.getstatusoutput("ping -c1 -w2 " + host)
        LOGGER.debug('Running on RPi')
        # LOGGER.debug(response)
        if response == 0:

            return response

    except:
        return None

    if response == 127:
        try:
            response = sp.call(['/sbin/ping', '-c1', '-W2', host], shell=False)
            LOGGER.debug('Running on Polisy')
            # LOGGER.debug(response)
            if response == 0:
                return response
        except:
            return None
    else:
        LOGGER.error('Ping Error - No Heartbeat')
        return None
        # Capture any exception

def GetRmRainSensorState(url, access_token):
    try:
        response = requests.get(url + 'api/4/restrictions/currently' + access_token, verify=False)
        rm_data = json.loads(response.content)
        #LOGGER.debug(rm_data)

        if rm_data['rainSensor'] == True:
            rs = 1
        else:
            rs = 0
        if rm_data['freeze'] == True:
            fr = 1
        else:
            fr = 0

        return rm_data['rainDelayCounter'],rs,fr

    except:
        LOGGER.error('Error getting rain sensor info')

def RmZoneProperties(url, access_token):
    try:
        response = requests.get(url + 'api/4/zone' + access_token, verify=False)
        rm_zone_data = json.loads(response.content)

        return rm_zone_data
    except:
        LOGGER.error('Unable to get zone properties')
        return ""

def RmZoneCtrl(url, access_token, command):
    #extract the zone number from the command string
    zone = ''.join(filter(lambda i: i.isdigit(), command['address']))
    if command['cmd'] == 'STOP':
        try:
            response = requests.post(url + 'api/4/zone/' + str(zone) + "/stop" + access_token, data=None, json=None, verify=False)
            LOGGER.info(response)
            #WLOGGER.debug('Received Stop Command')
        except:
            LOGGER.error('Unable to stop zone{1:s} watering'.format(zone))

    elif command['cmd'] == 'RUN':
        #extract the run duration from the command string and convert it to minutes
        zone_duration = '{"time":' + str(int(command['value'])*60) +'}'
        LOGGER.debug(zone_duration)
        #'{"time":60}'
        try:
            response = requests.post(url + 'api/4/zone/' + str(zone) + "/start" + access_token, data=zone_duration, json=None,
                                     verify=False)
            LOGGER.debug('Received Run Command')
            LOGGER.info(response.url)
        except:
            LOGGER.error('Unable to start zone watering')
            #LOGGER.error('Unable to stop zone{1:s} watering'.format(str(zone)))

def RmProgramCtrl(url, access_token, command):
    #extract the zone number from the command string
    program = ''.join(filter(lambda i: i.isdigit(), command['address']))
    if command['cmd'] == 'STOP':
        try:
            response = requests.post(url + 'api/4/program/' + str(program) + "/stop" + access_token, data=None, json=None, verify=False)
            LOGGER.info(response)
            #WLOGGER.debug('Received Stop Command')
        except:
            LOGGER.error('Unable to stop program {1} watering'.format(program))

    elif command['cmd'] == 'RUN':
        #extract the run duration from the command string and convert it to minutes
        #zone_duration = '{"time":' + str(int(command['value'])*60) +'}'
        #LOGGER.debug(zone_duration)
        #'{"time":60}'
        try:
            response = requests.post(url + 'api/4/program/' + str(program) + "/start" + access_token, data=None, json=None,
                                     verify=False)
            LOGGER.debug('Received Run Command')
            LOGGER.info(response.url)
        except:
            LOGGER.error('Unable to stop program {0}'.format(str(program)))

