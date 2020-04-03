#!/usr/bin/env python3
"""
This is a NodeServer for Green Electronics Rainmachine for Polyglot v2 written in Python3
by Gordon Larsen
MIT License

"""
try:
    import polyinterface
except ImportError:
    import pgc_interface as polyinterface

    iscloud = True

import math
import sys
import time
from datetime import datetime

import urllib3

from rm_functions import rmfuncs as rm
from rm_functions import utils

urllib3.disable_warnings()
"""
Import the polyglot interface module. This is in pypy so you can just install it
normally. Replace pip with pip3 if you are using python3.

"""

LOGGER = polyinterface.LOGGER
"""
polyinterface has a LOGGER that is created by default and logs to:
logs/debug.log
You can use LOGGER.info, LOGGER.warning, LOGGER.debug, LOGGER.error levels as needed.
"""


class RMController(polyinterface.Controller):

    def __init__(self, polyglot):
        """
        Optional.
        Super runs all the parent class necessities. You do NOT have
        to override the __init__ method, but if you do, you MUST call super.
        """
        super(RMController, self).__init__(polyglot)
        self.name = 'RainMachine Controller'

        self.address = 'rainmachine'
        self.primary = self.address
        self.host = ""
        self.port = 8080
        self.password = ""
        self.units = ""
        self.hwver = ""
        self.apiver = ""
        self.swver = ""
        self.access_token = ""
        self.timeout = 5
        self.rm_heartbeat = 0
        self.discovery_done = False
        self.translation_table = dict.fromkeys(map(ord, '!?+@#$%'),
                                               None)  # dictionary of disallowed characters in zone and program names
        self.top_level_url = ""
        self.currentloglevel = 10
        self.loglevel = {
            0: 'None',
            10: 'Debug',
            20: 'Info',
            30: 'Error',
            40: 'Warning',
            50: 'Critical'
        }

    def start(self):
        """
        Optional.
        Polyglot v2 Interface startup done. Here is where you start your integration.
        This will run, once the NodeServer connects to Polyglot and gets it's config.
        In this example I am calling a discovery method. While this is optional,
        this is where you should start. No need to Super this method, the parent
        version does nothing.
        """
        # This grabs the server.json data and checks profile_version is up to date

        LOGGER.info('Started Rainmachine NodeServer')
        serverdata = utils.get_server_data(LOGGER)
        LOGGER.debug("Server data: {}".format(serverdata))
        utils.update_version(LOGGER)
        utils.profile_zip(LOGGER)
        self.poly.installprofile()
        self.check_params()
        self.removeNoticesAll()
        self.discover()
        self.setDriver('GV0', 0)
        self.getZoneUpdate()
        self.getProgramUpdate()
        self.getPrecipNodeUpdate()

    def shortPoll(self):
        if not self.discovery_done:
            return

        if self.access_token is None:
            return

        LOGGER.debug("Access token: {}".format(self.access_token))
        # Get the latest from the zones
        self.getZoneUpdate()

        # Update program status
        self.getProgramUpdate()

        # Check for precipitation and forecast changes
        self.getPrecipNodeUpdate()

    def longPoll(self):
        if not self.discovery_done:
            return

        if self.access_token is None:
            LOGGER.error('Bad password or hostname')
            return

        # RainMachine Heartbeat
        self.rm_heartbeat = rm.rmHeartBeat(self.host, self.timeout)
        if self.rm_heartbeat == 0:
            self.setDriver('GV0', 1)
            LOGGER.info('RainMachine responding')
        else:
            self.setDriver('GV0', 0)
            LOGGER.info('RainMachine not responding')

        self.getRestrictionsUpdate()

    def query(self, command=None):
        """
        Optional.
        By default a query to the control node reports the FULL driver set for ALL
        nodes back to ISY. If you override this method you will need to Super or
        issue a reportDrivers() to each node manually.
        """
        self.check_params()
        for node in self.nodes:
            self.nodes[node].reportDrivers()

    def discover(self, *args, **kwargs):
        if self.host == "":
            return

        # Get the rainmachine hardware level and apiVersion
        rmdata = rm.getRainMachineVersion("https://" + self.host)
        if rmdata is None:
            self.hwver = 2
        else:
            self.hwver = rmdata['hwVer']
            # self.hwver = 1
            self.apiver = rmdata['apiVer']
            self.swver = rmdata['swVer']

        LOGGER.info(
            "Rainmachine Hardware version: {0}, API Version: {1}, Software level {2}".format(self.hwver, self.apiver,
                                                                                             self.swver))
        if self.hwver == 1:
            self.port = 443

        #if iscloud:
        #    self.top_level_url = 'http://my.rainmachine.com/'
        #else:
        self.top_level_url = "https://" + self.host + ":" + str(self.port) + "/"

        # Get the rainmachine access_token for further API calls
        self.access_token = rm.getRainmachineToken(self.password, self.top_level_url)
        if self.access_token is None:
            return

        self.access_token = '?access_token=' + self.access_token
        LOGGER.debug("Access token: {}".format(self.access_token))

        # Collect the zone information from the Rainmachine
        zone_data = rm.RmApiGet(self.top_level_url, self.access_token, 'api/4/zone')

        if zone_data is None:
            LOGGER.error('Can\'t get Rainmachine zone data (url {0:s}, access_token {1:s}'.format(self.top_level_url,
                                                                                                  self.access_token))
            return

        for z in zone_data['zones']:
            z_name = z['name'].replace('&', 'and')  # substitute 'and' for '&' in zone names
            zone_name = z_name.translate(self.translation_table)  # remove illegal characters from zone name

            LOGGER.debug("Zone name: {0}, Master: {1}".format(zone_name, z['master']))
            if z['master']:
                zone_name = "Master Zone"

            self.addNode(
                # RmZone(self, self.address, 'zone' + str(z['uid']), 'Zone ' + str(z['uid']) + " - " + z['name']))
                RmZone(self, self.address, 'zone' + str(z['uid']), 'Zone ' + str(z['uid']) + " - " + zone_name,
                       self.top_level_url, self.access_token))
            time.sleep(1)

        # Collect the program information from the Rainmachine
        program_data = rm.RmApiGet(self.top_level_url, self.access_token, 'api/4/program')
        LOGGER.debug("Program data: {}".format(program_data))
        if program_data is None:
            LOGGER.error('Can\'t get Rainmachine programs (url {0:s}, access_token {1:s}'.format(self.top_level_url,
                                                                                                 self.access_token))
            return

        for z in program_data['programs']:
            p_name = z['name'].replace('&', 'and')  # replace '& with 'and' in program name
            prog_name = p_name.translate(self.translation_table)  # remove illegal characters from program name
            LOGGER.debug("Program name: {}".format(prog_name))

            self.addNode(RmProgram(self, self.address, 'program' + str(z['uid']), prog_name, self.top_level_url,
                                   self.access_token))
            # self.addNode(RmProgram(self, self.address, 'program' + str(z['uid']), z['name']))
            time.sleep(1)

        # Set up nodes for rain and qpf data for today and the next 2 days
        if self.hwver != 1:
            self.addNode(RmPrecip(self, self.address, 'precip', 'Precipitation'))

        # Add the restrictions information node
        self.addNode(RmRestrictions(self,self.address, 'restrict', 'Restrictions', self.top_level_url, self.access_token))

        self.discovery_done = True

    def getZoneUpdate(self):

        zone_data = rm.RmApiGet(self.top_level_url, self.access_token, 'api/4/zone')

        if zone_data is None:
            LOGGER.error(
                'Can\'t get Rainmachine zone data (url {0:s}, access_token {1:s}'.format(self.top_level_url,
                                                                                         self.access_token))
            return

        LOGGER.debug("Zone data: {}".format(zone_data))
        # LOGGER.debug(zone_data['zones'])
        try:
            for z in zone_data['zones']:
                self.nodes['zone' + str(z['uid'])].setDriver('ST', z['state'])
                self.nodes['zone' + str(z['uid'])].setDriver('GV3', math.trunc(z['remaining'] / 60))
                self.nodes['zone' + str(z['uid'])].setDriver('GV4', z['remaining'] % 60)
                if z['master']:
                    master_zone = 1  # This is a master zone
                else:
                    master_zone = 0
                self.nodes['zone' + str(z['uid'])].setDriver('GV5', master_zone)

        except:
            LOGGER.error('Unable to update nodes')

    def getProgramUpdate(self):
        program_data = rm.RmApiGet(self.top_level_url, self.access_token, 'api/4/program')

        if program_data is None:
            LOGGER.error(
                'Can\'t get Rainmachine zone data (url {0:s}, access_token {1:s}'.format(self.top_level_url,
                                                                                         self.access_token))
            return

        LOGGER.debug("Program data: {}".format(program_data))

        try:
            for z in program_data['programs']:
                self.nodes['program' + str(z['uid'])].setDriver('ST', z['status'])

                if z['nextRun'] is None:
                    rundayiso = '0'  # Not scheduled
                else:
                    nextrunday = z['nextRun']
                    nextrunday = datetime.date(datetime.strptime(nextrunday, '%Y-%m-%d'))
                    now = datetime.date(datetime.now())
                    # LOGGER.debug("Now= {0}, Next run day = {1}".format(now,nextrunday))
                    nextrun = str(nextrunday - now)
                    # LOGGER.debug("Nextrun is {}".format(nextrun))

                    if str(nextrun[0]) == '0':
                        rundayiso = '8'  # Today
                    elif str(nextrun[0]) == '1':
                        rundayiso = '9'  # Tomorrow
                    else:
                        runday = datetime.date(datetime.strptime(z['nextRun'], '%Y-%m-%d'))
                        rundayiso = runday.isoweekday()

                self.nodes['program' + str(z['uid'])].setDriver('GV3', rundayiso)
        except:
            LOGGER.error('Unable to update programs')

    def getPrecipNodeUpdate(self):
        # Now fill in precip forecast and fields
        if self.hwver != 1:
            try:
                precip = ["", "", "", ""]

                # now = datetime.now()
                today = datetime.now().strftime("%Y-%m-%d")

                mixer_data = rm.RmApiGet(self.top_level_url, self.access_token, 'api/4/mixer/' + today + '/3')
                LOGGER.debug("Mixer data: {}".format(mixer_data))

                precip[0] = mixer_data['mixerDataByDate'][0]['rain']
                precip[1] = mixer_data['mixerDataByDate'][0]['qpf']
                precip[2] = mixer_data['mixerDataByDate'][1]['qpf']
                precip[3] = mixer_data['mixerDataByDate'][2]['qpf']
                LOGGER.debug("Precip list1: {}".format(precip))
                for i in range(0, 3):
                    if precip[i] == None:
                        precip[i] = 0
                #LOGGER.debug("Precip list2: {}".format(precip))

                rain = float(precip[0])
                qpf1 = float(precip[1])
                qpf2 = float(precip[2])
                qpf3 = float(precip[3])
                units_uom = '82'

                if self.units != 'metric':
                    rain = round((rain / 25.4), 2)
                    qpf1 = round((qpf1 / 25.4), 2)
                    qpf2 = round((qpf2 / 25.4), 2)
                    qpf3 = round((qpf3 / 25.4), 2)
                    units_uom = '105'
                self.nodes['precip'].setDriver('ST', rain, uom=units_uom)
                self.nodes['precip'].setDriver('GV0', qpf1, uom=units_uom)
                self.nodes['precip'].setDriver('GV1', qpf2, uom=units_uom)
                self.nodes['precip'].setDriver('GV2', qpf3, uom=units_uom)

            except:
                LOGGER.error("Couldn't update precipation data or forecast")

    def getRestrictionsUpdate(self):
        # rain_delay, rain_sensor, freeze = rm.GetRmRainSensorState(self.top_level_url, self.access_token, self.hwver)
        restrictions = rm.GetRmRestrictions( self.top_level_url, self.access_token, self.hwver )
        LOGGER.debug( "Sensor data: {}".format( restrictions ) )
        rain_delay_time = restrictions['rainDelayCounter']
        if rain_delay_time == -1:
            rain_delay_time = 0

        freeze = restrictions['freeze']

        self.nodes['restrict'].setDriver('GV0', math.trunc( rain_delay_time /60))
        self.nodes['restrict'].setDriver('GV2', int(restrictions['hourly'] == True))
        self.nodes['restrict'].setDriver('GV3', int(restrictions['month'] == True))
        self.nodes['restrict'].setDriver('GV4', int(restrictions['weekDay'] == True))

        if self.hwver == 1:
            rain_sensor = restrictions['rainSensor']
            self.nodes['restrict'].setDriver( 'ST', rain_sensor)
            self.nodes['restrict'].setDriver( 'GV1', freeze )
        else:
            self.nodes['restrict'].setDriver( 'ST', 0 )
            self.nodes['restrict'].setDriver( 'GV1', 0 )
            # Set these drivers to N/A for hardware version 1 RMs, not supported
        '''
        drivers = [
            {'driver': 'ST', 'value': 0, 'uom': 25},  # Rain Sensor
            {'driver': 'GV0', 'value': 0, 'uom': 45},  # Rain Delay Remaining
            {'driver': 'GV1', 'value': 0, 'uom': 25},  # Freeze Protect
            {'driver': 'GV2', 'value': 0, 'uom': 2},  # Hourly restrictions?
            {'driver': 'GV3', 'value': 0, 'uom': 2},  # Month restrictions?
            {'driver': 'GV4', 'value': 0, 'uom': 2}  # Weekday restrictions?
        ]
        '''

    def delete(self):
        LOGGER.info('Rainmachine Nodeserver deleted')

    def stop(self):
        LOGGER.info('Rainmachine NodeServer stopped.')

    def check_params(self):
        self.set_configuration(self.polyConfig)

        LOGGER.info("Adding configuration")
        self.addCustomParam({
            'Hostname': self.host,
            'Password': self.password,
            'Units': self.units,
        })

        if 'Loglevel' in self.polyConfig['customData']:
            self.currentloglevel = self.polyConfig['customData']['Loglevel']
            self.setDriver('GV4', self.currentloglevel)
            LOGGER.setLevel(self.currentloglevel)
            LOGGER.info("Loglevel set to: {}".format(self.loglevel[self.currentloglevel]))
        else:
            self.saveCustomData({
                'Loglevel': self.currentloglevel,  # set default loglevel to 'Info'
            })
            LOGGER.setLevel(self.currentloglevel)
            self.setDriver('GV4', self.currentloglevel)
            LOGGER.info("Loglevel set to 10 (Debug)")
        # Remove all existing notices
        LOGGER.info("remove all notices")
        self.removeNoticesAll()

    def set_configuration(self, config):

        LOGGER.info("Checking existing configuration values")

        if 'Hostname' in config['customParams']:
            self.host = config['customParams']['Hostname']
        else:
            self.host = ""

        if 'Password' in config['customParams']:
            self.password = config['customParams']['Password']
        else:
            self.password = ""

        if 'Units' in config['customParams']:
            self.units = config['customParams']['Units'].lower()
        else:
            self.units = "metric"

        # Add a notice?
        if self.host == "":
            self.addNotice("Hostname or IP address of the Rainmachine device is required.")
        if self.password == "":
            self.addNotice("Password for Rainmachine is required.")
        if self.units == "":
            self.addNotice("Units to display rain information for ISY Precipitation Node.")

    def remove_notices_all(self, command):
        LOGGER.info('remove_notices_all: notices={}'.format(self.poly.config['notices']))
        # Remove all existing notices
        self.removeNoticesAll()

    def update_profile(self, command):
        LOGGER.info('update_profile:')
        utils.update_version(LOGGER)
        utils.profile_zip(LOGGER)
        st = self.poly.installprofile()
        return st

    def set_rain_delay(self, command):
        LOGGER.debug("Received command {} in 'set_rain_delay'".format(command))
        st = rm.RmSetRainDelay(self.top_level_url, self.access_token, command)
        return st

    def set_log_level(self, command):
        LOGGER.debug("Received command {} in 'set_log_level'".format(command))
        value = int(command.get('value'))
        LOGGER.setLevel(value)

        self.setDriver('GV4', value)
        LOGGER.info("Set Logging Level to {}".format(self.loglevel[value]))
        self.saveCustomData({
            'Loglevel': value,
        })

    id = 'RainMachine'

    commands = {
        'QUERY': query,
        'DISCOVER': discover,
        'UPDATE_PROFILE': update_profile,
        'REMOVE_NOTICES_ALL': remove_notices_all,
        'LOG_LEVEL': set_log_level
    }

    drivers = [
        {'driver': 'ST', 'value': 1, 'uom': 2},
        {'driver': 'GV0', 'value': 0, 'uom': 2},
        {'driver': 'GV4', 'value': 0, 'uom': 25}
    ]


class RmZone(polyinterface.Node):
    id = "zone"

    def __init__(self, controller, primary, address, name, url, token):
        self.url = url
        self.token = token

        super(RmZone, self).__init__(controller, primary, address, name)

    def zone_run(self, command):
        LOGGER.debug(command)
        rm.RmZoneCtrl(self.url, self.token, command)

    def zone_stop(self, command):
        LOGGER.debug(command)
        rm.RmZoneCtrl(self.url, self.token, command)

    def query(self):
        self.reportDrivers()

    drivers = [
        {'driver': 'ST', 'value': 0, 'uom': 25},  # Zone state
        {'driver': 'GV3', 'value': 0, 'uom': 45},  # Zone runtime minutes remaining
        {'driver': 'GV4', 'value': 0, 'uom': 58},  # Zone runtime seconds remaining
        {'driver': 'GV5', 'value': 0, 'uom': 2},  # Is this a master zone?
    ]

    commands = {
        'RUN': zone_run,
        'STOP': zone_stop,
        'QUERY': query
    }


class RmProgram(polyinterface.Node):
    id = "program"

    def __init__(self, controller, primary, address, name, url, token):
        self.url = url
        self.token = token

        super(RmProgram, self).__init__(controller, primary, address, name)

    def program_run(self, command):
        LOGGER.debug(command)
        rm.RmProgramCtrl(self.url, self.token, command)

    def program_stop(self, command):
        LOGGER.debug(command)
        rm.RmProgramCtrl(self.url, self.token, command)

    def query(self):
        self.reportDrivers()

    drivers = [
        {'driver': 'ST', 'value': 0, 'uom': 25},  # Program status -
        {'driver': 'GV3', 'value': 0, 'uom': 25}  # Program nextrun
        #    {'driver': 'GV4', 'value': '0', 'uom': '58'}, #
    ]

    commands = {
        'RUN': program_run,
        'STOP': program_stop,
        'QUERY': query
    }


class RmPrecip(polyinterface.Node):
    id = "precip"

    def __init__(self, controller, primary, address, name):
        super(RmPrecip, self).__init__(controller, primary, address, name)

    def query(self):
        self.reportDrivers()

    drivers = [
        {'driver': 'ST', 'value': 0, 'uom': 82},  # Rain today
        {'driver': 'GV0', 'value': 0, 'uom': 82},  # Precip forecast for today added in V 0.2.6
        {'driver': 'GV1', 'value': 0, 'uom': 82},  # Precip forecast for tomorrow
        {'driver': 'GV2', 'value': 0, 'uom': 82}  # Precip forecast for day after tomorrow
    ]

    commands = {
        'QUERY': query
    }

class RmRestrictions(polyinterface.Node):
    id = "restrict"

    def __init__(self, controller, primary, address, name, url, token):
        self.url = url
        self.token = token
        super(RmRestrictions, self).__init__(controller, primary, address, name)

    def query(self):
        self.reportDrivers()

    def set_rain_delay(self, command):
        LOGGER.debug("Received command {} in 'set_rain_delay'".format(command))
        st = rm.RmSetRainDelay(self.url, self.token, command)
        return st

    drivers = [
        {'driver': 'ST', 'value': 0, 'uom': 25},  # Rain Sensor
        {'driver': 'GV0', 'value': 0, 'uom': 45},  # Rain Delay Remaining
        {'driver': 'GV1', 'value': 0, 'uom': 25},  # Freeze Protect
        {'driver': 'GV2', 'value': 0, 'uom': 2},  # Hourly restrictions?
        {'driver': 'GV3', 'value': 0, 'uom': 2},  # Month restrictions?
        {'driver': 'GV4', 'value': 0, 'uom': 2}  # Weekday restrictions?
    ]

    commands = {
        'QUERY': query,
        'RAIN_DELAY': set_rain_delay,
    }

if __name__ == "__main__":
    try:
        polyglot = polyinterface.Interface('RainMachine')
        """
        Instantiates the Interface to Polyglot.
        The name doesn't really matter unless you are starting it from the
        command line then you need a line Template=N
        where N is the slot number.
        """
        polyglot.start()
        """
        Starts MQTT and connects to Polyglot.
        """
        control = RMController(polyglot)
        """
        Creates the Controller Node and passes in the Interface
        """
        control.runForever()
        """
        Sits around and does nothing forever, keeping your program running.
        """
    except (KeyboardInterrupt, SystemExit):
        LOGGER.warning("Received interrupt or exit...")
        """
        Catch SIGTERM or Control-C and exit cleanly.
        """
        polyglot.stop()
    except Exception as err:
        LOGGER.error('Excption: {0}'.format(err), exc_info=True)
    sys.exit(0)
