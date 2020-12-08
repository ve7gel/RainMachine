#!/usr/bin/env python3
"""
This is a NodeServer for Green Electronics Rainmachine for Polyglot v2 written in Python3
by Gordon Larsen
MIT License

"""
import sys
import time

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
        self.host = None
        self.port = 8080
        self.password = ""
        self.units = ""
        self.hwver = ""
        self.apiver = ""
        self.swver = ""
        self.access_token = ""
        self.timeout = 2
        self.discovery_done = False
        self.translation_table = dict.fromkeys(map(ord, '!?+@#$%'),
                                               None)  # dictionary of disallowed characters in zone and program names
        self.top_level_url = ""
        self.currentloglevel = 10
        self.rmzonenode = []
        self.rmprognode = []
        self.rmprecipnode = None
        self.rmrestrictnode = None
        self.winter_mode = False

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
        # serverdata = utils.get_server_data(LOGGER)
        # LOGGER.debug("Server data: {}".format(serverdata))
        utils.update_version(LOGGER)
        utils.profile_zip(LOGGER)
        self.poly.installprofile()
        self.check_params()
        self.removeNoticesAll()
        #if not self.winter_mode:
        #    self.discover()
        self.setDriver('GV0', 0)


    def shortPoll(self):
        if self.winter_mode:
            return
        if not self.discovery_done:
            self.discover()

        LOGGER.debug("In shortPoll, access token: {}".format(self.access_token))
        if self.access_token is None:
            return

        # Get the latest from the zones
        self.getZoneUpdate()

        # Update program status
        self.getProgramUpdate()

    def longPoll(self):
        """ We check the heartbeat, get updates for precipitation and restrictions nodes """
        if not self.discovery_done or self.winter_mode:
            return

        self.rm_pulse()  # Is the RM on the network

        if self.access_token is None:
            LOGGER.error('Bad password or hostname')
            return

        LOGGER.debug("In longPoll, access token: {}".format(self.access_token))

        # Check for precipitation and forecast changes
        if self.hwver is not 1:
            self.getPrecipNodeUpdate()

        # Update status of restrictions
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
            LOGGER.error("Hostname or IP missing")
            return
        # if self.winter_mode:
        #    LOGGER.info("Nodeserver is in Winter Mode")
        #    return

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
        if self.hwver == 1:  # RM hardware version 1 uses port 443 for secure connection, others use port 8081
            self.port = 443

        self.top_level_url = "https://" + self.host + ":" + str(self.port) + "/"

        # Get the rainmachine access_token for further API calls
        self.access_token = self.getAccessToken(self.password, self.top_level_url)
        if self.access_token is None:
            return

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

            self.rmzonenode.append(self.addNode(
                # RmZone(self, self.address, 'zone' + str(z['uid']), 'Zone ' + str(z['uid']) + " - " + z['name']))
                RmZone(self, self.address, 'zone' + str(z['uid']), 'Zone ' + str(z['uid']) + " - " + zone_name,
                       self.top_level_url, self.access_token)))
            # time.sleep(1)

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

            self.rmprognode.append(self.addNode(
                RmProgram(self, self.address, 'program' + str(z['uid']), prog_name, self.top_level_url,
                          self.access_token)))
            # time.sleep(1)

        # Set up nodes for rain and qpf data for today and the next 2 days
        if self.hwver != 1:
            # self.rmprecipnode = self.addNode(RmPrecip(self, self.address, 'precip', 'Precipitation', self.top_level_url, self.access_token, self.hwver, self.units))
            self.rmprecipnode = self.addNode(
                RmPrecip(self, self.address, 'precip', 'Precipitation', self.top_level_url, self.access_token,
                         self.hwver, self.units))

        # Add the restrictions information node
        self.rmrestrictnode = self.addNode(
            RmRestrictions(self, self.address, 'restrict', 'Restrictions', self.top_level_url, self.access_token,
                           self.hwver))
        self.discovery_done = True

    def rm_pulse(self):
        # RainMachine Heartbeat
        heartbeat = rm.rmHeartBeat(self.host, self.timeout)

        if heartbeat == 0:
            self.setDriver('GV0', 1)
            LOGGER.info('RainMachine responding')
        else:
            self.setDriver('GV0', 0)
            LOGGER.info('RainMachine not responding')

    def getAccessToken(self, password, url):
        """ Get the rainmachine access_token for further API calls """
        token = rm.getRainmachineToken(password, url)
        LOGGER.debug("In get_token, token is {}".format(token))
        if token == 401:
            LOGGER.error("Rainmachine says 'Not Authorized', invalid or no password entered")
            return None

        token = '?access_token=' + token
        LOGGER.debug("Access token: {}".format(token))
        return token

    def getZoneUpdate(self):
        """ This function retrieves the raw zone info from the Rainmachine """
        zone_data = rm.RmApiGet(self.top_level_url, self.access_token, 'api/4/zone')
        LOGGER.debug("Zone data: {}".format(zone_data))
        if zone_data is None:
            LOGGER.error(
                "Can't get Rainmachine zone data {}".format(zone_data))
            return

        try:
            for z in range(int(len(self.rmzonenode))):
                RmZone.set_Driver(self.rmzonenode[z], 'ST', zone_data['zones'][z]['state'])
                RmZone.set_Driver(self.rmzonenode[z], 'GV3', zone_data['zones'][z]['remaining'])
                #        RmZone.setnodeDriver( self.rmzonenode[z], 'GV4', zone_data['zone'][z]['remaining'] )
                RmZone.set_Driver(self.rmzonenode[z], 'GV5', zone_data['zones'][z]['master'])

        except (RuntimeError, TypeError, NameError, OSError) as err:
            LOGGER.error('Unable to update zone data')
            LOGGER.error(err)

    def getProgramUpdate(self):
        """ Get the latest status info on Rainmachine programs here """
        program_data = rm.RmApiGet(self.top_level_url, self.access_token, 'api/4/program')

        if program_data is None:
            LOGGER.error(
                "Can't get Rainmachine program data (url {}, access_token {})".format(self.top_level_url,
                                                                                      self.access_token))
            return

        LOGGER.debug("Program data: {}".format(program_data))
        try:
            for z in range(int(len(self.rmprognode))):
                status = program_data['programs'][z]['status']
                RmProgram.set_Driver(self.rmprognode[z], 'ST', status)
                nextrun = program_data['programs'][z]['nextRun']
                RmProgram.set_Driver(self.rmprognode[z], 'GV3', nextrun)

        except (RuntimeError, TypeError, NameError, OSError) as err:
            LOGGER.error('Unable to update program data')
            LOGGER.error(err)

    def getPrecipNodeUpdate(self):
        RmPrecip.set_Driver(self.rmprecipnode)

    def getRestrictionsUpdate(self):
        RmRestrictions.set_Driver(self.rmrestrictnode)

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

        if 'winterMode' in self.polyConfig['customData']:
            self.winter_mode = self.polyConfig['customData']['winterMode']
            LOGGER.debug("Winter mode set to {}".format(self.polyConfig['customData']['winterMode']))

        if self.winter_mode:
            LOGGER.info("RainMachine Nodeserver winter mode enabled")
            self.setDriver('GV3', 1)
        else:
            LOGGER.info("RainMachine Nodeserver winter mode disabled")
            self.setDriver('GV3', 0)

        if 'Loglevel' in self.polyConfig['customData']:
            LOGGER.debug("in params, Loglevel {}".format(self.polyConfig['customData']['Loglevel']))
            self.currentloglevel = self.polyConfig['customData']['Loglevel']
            LOGGER.debug("in params, self.currentloglevel = {}".format(self.currentloglevel))
            self.setDriver('GV4', self.currentloglevel)
            LOGGER.setLevel(self.currentloglevel)
            LOGGER.info("Loglevel set to: {}".format(self.loglevel[self.currentloglevel]))
        else:
            LOGGER.setLevel(self.currentloglevel)
            self.setDriver('GV4', self.currentloglevel)
            LOGGER.info("Loglevel set to 10 (Debug)")

        payload_data = {
            'Loglevel': self.currentloglevel,
            'winterMode': self.winter_mode,
        }
        self.poly.saveCustomData(payload_data)
        LOGGER.info("Payload_data = {}".format(payload_data))
        LOGGER.info("customData = {}".format(self.polyConfig['customData']))

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
            self.addNotice("Hostname (FQDN) or IP address of the Rainmachine device is required.")
        if self.password == "":
            self.addNotice("Password for Rainmachine is required.")
        if self.units == "":
            self.addNotice("Units to display rain information for ISY Precipitation Node. 'metric' or 'us'")

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

    def set_log_level(self, command):
        LOGGER.debug("Received command {} in 'set_log_level'".format(command))
        value = int(command.get('value'))
        LOGGER.setLevel(value)

        self.setDriver('GV4', value)
        LOGGER.info("Set Logging Level to {}".format(self.loglevel[value]))
        ll_data = {
            'winterMode': self.winter_mode,
            'Loglevel': self.currentloglevel,
        }
        self.poly.saveCustomData(ll_data)
        LOGGER.debug("CustomData = {}".format(self.polyConfig['customData']))

    def set_winter_mode(self, command):
        LOGGER.debug("Received command {} in 'set_winter_mode'".format(command))
        value = int(command.get('value'))
        if value:
            self.winter_mode = True
            self.setDriver('GV3', 1)
        else:
            self.winter_mode = False
            self.setDriver('GV3', 0)

        LOGGER.info("Set winter mode to {}".format(self.winter_mode))
        wm_data = {
            'winterMode': self.winter_mode,
            'Loglevel': self.currentloglevel,
        }
        # self.saveCustomData(wm_data)
        self.poly.saveCustomData(wm_data)
        time.sleep(2)
        LOGGER.info("CustomData = {}".format(self.polyConfig['customData']))

    id = 'RainMachine'

    commands = {
        'QUERY': query,
        'DISCOVER': discover,
        'UPDATE_PROFILE': update_profile,
        'REMOVE_NOTICES_ALL': remove_notices_all,
        'LOG_LEVEL': set_log_level,
        'WINTER': set_winter_mode,
    }

    drivers = [
        {'driver': 'ST', 'value': 1, 'uom': 2},
        {'driver': 'GV0', 'value': 0, 'uom': 2},
        {'driver': 'GV3', 'value': 0, 'uom': 2},
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
