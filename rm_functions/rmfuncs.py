#!/usr/bin/env python3
"""
This is a NodeServer for Green Electronics Rainmachine for Polyglot v2 written in Python3
by Gordon Larsen
MIT License

"""
import json
import subprocess as sp

import requests
import urllib3
from polyinterface import LOGGER

urllib3.disable_warnings()

def getRainMachineVersion(url):

    try:
        response = requests.get(url + ":8080/api/4/apiVer", verify=False)
        LOGGER.info("Found Rainmachine on port 8080")
        LOGGER.debug("API Response: {0}, content {1}".format(response, response.content))
        #return json.loads(response.content)
        return response.json()

    except OSError:
        response = requests.get(url + ":443/api/4/apiVer", verify=False)
        LOGGER.info("Found Rainmachine on port 443")
        #return json.loads(response.content)
        return response.json()

    except:
        LOGGER.error("Error getting Rainmachine version info")
        LOGGER.debug("Response was {0} from url {1}".format(response, url))
        return None

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
        if r.status_code is 200:
            rmdata = r.json()
            access_token = rmdata['access_token']
            return access_token
        else:
            return r.status_code

    except:
        LOGGER.error("Incorrect hostname or password")
        return None

def RmApiGet(url, access_token,api_call):
    # call to acquire data from Rainmachine
    try:
        response = requests.get(url + api_call + access_token, verify=False)
        if response.status_code is 200:
            rm_data = response.json()
        else:
            return response.status_code

    except OSError as err:
        LOGGER.error("RM call {} failed".format(err))
        return None

    return rm_data

def rmHeartBeat(host, timeout):

    try:
        response, result = sp.getstatusoutput("ping -c1 -w" + str(timeout) + " " + host)
        LOGGER.debug("rmHeartBeat response: {}".format(response))
        if response == 0:
            LOGGER.debug('Running on RPi')
            return response

    except OSError as err:
        LOGGER.error('Ping Error - No Heartbeat')
        LOGGER.debug(err)
        return None

    if response == 127:
        try:
            response = sp.call(['/sbin/ping', '-c1', '-W' + str(timeout), host], shell=False)
            LOGGER.debug("rmHeartBeat response: {}".format(response))
            if response == 0:
                LOGGER.debug('Running on Polisy')
                return response
        except OSError as err:
            LOGGER.error(err)
            return None
    else:
        LOGGER.error('Ping Error - No Heartbeat')
        return None
        # Capture any exception

def GetRmRestrictions(url, access_token):
    try:
        response = requests.get(url + 'api/4/restrictions/currently' + access_token, verify=False)
        rm_data = response.json()
        #LOGGER.debug("GetRmRestrictions data: {}".format(rm_data))
        return rm_data

    except OSError:
        LOGGER.error('Error getting restrictions info')
        return None

def RmZoneProperties(url, access_token):
    try:
        response = requests.get(url + 'api/4/zone' + access_token, verify=False)
        #rm_zone_data = json.loads(response.content)
        rm_zone_data = response.json()
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
            LOGGER.debug(response)
            LOGGER.debug('Received Stop Command')
        except:
            LOGGER.error('Unable to stop zone {} watering'.format(zone))

    elif command['cmd'] == 'RUN':
        #extract the run duration from the command string and convert it to minutes
        zone_duration = '{"time":' + str(int(command['value'])*60) +'}'
        LOGGER.debug("Zone duration: {}".format(zone_duration))
        #'{"time":60}'
        try:
            response = requests.post(url + 'api/4/zone/' + str(zone) + "/start" + access_token, data=zone_duration, json=None,
                                     verify=False)
            LOGGER.debug('Received Run Command')
            LOGGER.debug(response.url)
        except:
            LOGGER.error('Unable to start zone watering')
            #LOGGER.error('Unable to stop zone{1:s} watering'.format(str(zone)))

def RmProgramCtrl(url, access_token, command):
    #extract the zone number from the command string
    program = ''.join(filter(lambda i: i.isdigit(), command['address']))
    if command['cmd'] == 'STOP':
        try:
            response = requests.post(url + 'api/4/program/' + str(program) + "/stop" + access_token, data=None, json=None, verify=False)
            LOGGER.debug(response)
            LOGGER.debug('Received Stop Command')
        except:
            LOGGER.error('Unable to stop program {} watering'.format(program))

    elif command['cmd'] == 'RUN':
        #extract the run duration from the command string and convert it to minutes
        #zone_duration = '{"time":' + str(int(command['value'])*60) +'}'
        #LOGGER.debug(zone_duration)
        #'{"time":60}'
        try:
            response = requests.post(url + 'api/4/program/' + str(program) + "/start" + access_token, data=None, json=None,
                                     verify=False)
            LOGGER.debug('Received Run Command')
            LOGGER.debug(response.url)
        except:
            LOGGER.error('Unable to stop program {0}'.format(str(program)))

def RmSetRainDelay(url, access_token, command):
    LOGGER.debug("RmSetRainDelay received: {}".format(command))
    value = command['value']
    data = {
        "rainDelay": value
    }

    try:
        response = requests.post(url + 'api/4/restrictions/raindelay' + access_token, data=json.dumps(data), json=None,
                             verify=False)
        LOGGER.debug("SetRainDelay response: {}".format(response))
    except:
        LOGGER.error("Rain delay update failed")
        #LOGGER.error(response)
        return -1
