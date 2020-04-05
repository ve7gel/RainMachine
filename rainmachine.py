#!/usr/bin/env python3
"""
This is a NodeServer for Green Electronics Rainmachine for Polyglot v2 written in Python3
by Gordon Larsen
MIT License

"""
import math
import sys
import time
from datetime import datetime

import polyinterface
import urllib3

# from nodes import RmRestrictions
# from nodes import RmPrecip
# from nodes import RmProgram
from nodes import *
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
        self.rmzonenode = []
        self.rmprognode = []
        self.rmprecipnode = None
        self.rmrestrictnode = None

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
        if self.hwver == 1: # RM hardware version 1 uses port 443 for secure connection, others use port 8081
            self.port = 443

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

            self.rmprognode.append(self.addNode( RmProgram( self, self.address, 'program' + str(z['uid']), prog_name, self.top_level_url,self.access_token ) ))
            time.sleep(1)

        # Set up nodes for rain and qpf data for today and the next 2 days
        if self.hwver != 1:
            #self.rmprecipnode = self.addNode(RmPrecip(self, self.address, 'precip', 'Precipitation', self.top_level_url, self.access_token, self.hwver, self.units))
           self.rmprecipnode = self.addNode(RmPrecip(self, self.address, 'precip', 'Precipitation', self.top_level_url, self.access_token, self.hwver, self.units))

        # Add the restrictions information node
        self.rmrestrictnode = self.addNode(RmRestrictions( self, self.address, 'restrict', 'Restrictions', self.top_level_url, self.access_token,self.hwver ) )
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
            LOGGER.error('Unable to update zone data')
    '''
    def getProgramUpdate(self):
        #for x in range(len(self.rmprognode)):
        RmProgram.shortPoll(self.rmprognode[0])
    '''

    def getProgramUpdate(self):
        program_data = rm.RmApiGet(self.top_level_url, self.access_token, 'api/4/program')

        if program_data is None:
            LOGGER.error(
                'Can\'t get Rainmachine program data (url {0:s}, access_token {1:s}'.format(self.top_level_url,
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
            LOGGER.error('Unable to update program data')

    def getPrecipNodeUpdate(self):
        RmPrecip.shortPoll(self.rmprecipnode)

    def getRestrictionsUpdate(self):
        RmRestrictions.shortPoll(self.rmrestrictnode)

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
