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

import math
import sys
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
    """
    The Controller Class is the primary node from an ISY perspective. It is a Superclass
    of polyinterface.Node so all methods from polyinterface.Node are available to this
    class as well.

    Class Variables:
    self.nodes: Dictionary of nodes. Includes the Controller node. Keys are the node addresses
    self.name: String name of the node
    self.address: String Address of Node, must be less than 14 characters (ISY limitation)
    self.polyConfig: Full JSON config dictionary received from Polyglot for the controller Node
    self.added: Boolean Confirmed added to ISY as primary node
    self.config: Dictionary, this node's Config

    Class Methods (not including the Node methods):
    start(): Once the NodeServer config is received from Polyglot this method is automatically called.
    addNode(polyinterface.Node, update = False): Adds Node to self.nodes and polyglot/ISY. This is called
        for you on the controller itself. Update = True overwrites the existing Node data.
    updateNode(polyinterface.Node): Overwrites the existing node data here and on Polyglot.
    delNode(address): Deletes a Node from the self.nodes/polyglot and ISY. Address is the Node's Address
    longPoll(): Runs every longPoll seconds (set initially in the server.json or default 10 seconds)
    shortPoll(): Runs every shortPoll seconds (set initially in the server.json or default 30 seconds)
    query(): Queries and reports ALL drivers for ALL nodes to the ISY.
    getDriver('ST'): gets the current value from Polyglot for driver 'ST' returns a STRING, cast as needed
    runForever(): Easy way to run forever without maxing your CPU or doing some silly 'time.sleep' nonsense
                  this joins the underlying queue query thread and just waits for it to terminate
                  which never happens.
    """

    def __init__ (self, polyglot):
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
        self.access_token = ""
        self.timeout = 5
        self.discovery_done = False

    def start (self):
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
        LOGGER.debug(serverdata)
        utils.update_version(LOGGER)
        utils.profile_zip(LOGGER)
        self.poly.installprofile()
        self.check_params()
        self.removeNoticesAll()
        self.discover()
        self.setDriver('GV0', 0)

    def shortPoll (self):
        if self.discovery_done == False:
            return

        if self.access_token == None:
            return

        #LOGGER.debug(access_token)
        #zone_data = rm.getRmZones(top_level_url, access_token)
        zone_data = rm.RmApiGet(top_level_url, access_token, 'api/4/zone')

        if zone_data == None:
            LOGGER.error('Can\'t get Rainmachine zone data (url {0:s}, access_token {1:s}'.format(top_level_url,access_token))
            return

        #LOGGER.debug(zone_data)
        #LOGGER.debug(zone_data['zones'])
        try:
            for z in zone_data['zones']:
                self.nodes['zone' + str(z['uid'])].setDriver('ST', z['state'])
                self.nodes['zone' + str(z['uid'])].setDriver('GV3', math.trunc(z['remaining'] / 60))
                self.nodes['zone' + str(z['uid'])].setDriver('GV4', z['remaining'] % 60)

        except:
            LOGGER.error('Unable to update nodes')

        program_data = rm.RmApiGet(top_level_url, access_token, 'api/4/program')

        if program_data == None:
            LOGGER.error(
                'Can\'t get Rainmachine zone data (url {0:s}, access_token {1:s}'.format(top_level_url, access_token))
            return

        # LOGGER.debug(zone_data)
        # LOGGER.debug(zone_data['zones'])

        try:
            for z in program_data['programs']:
                self.nodes['program' + str(z['uid'])].setDriver('ST', z['status'])

                if z['nextRun'] == None:
                    rundayiso = '0' # Not scheduled
                else:
                    nextrunday = z['nextRun']
                    nextrunday = datetime.date(datetime.strptime(nextrunday, '%Y-%m-%d'))
                    now = datetime.date(datetime.now())
                    #LOGGER.debug("Now= {0}, Next run day = {1}".format(now,nextrunday))
                    nextrun = str(nextrunday - now)
                    #LOGGER.debug("Nextrun is {}".format(nextrun))

                    if str(nextrun[0]) == '0':
                        rundayiso = '8' # Today
                    elif str(nextrun[0]) == '1':
                        rundayiso = '9' # Tomorrow
                    else:
                        runday = datetime.date(datetime.strptime(z['nextRun'], '%Y-%m-%d'))
                        rundayiso = runday.isoweekday()

                #LOGGER.debug("Program {0} Next run day is: {1}, rundayiso is {2}".format(z['uid'],runday,rundayiso))

                self.nodes['program' + str(z['uid'])].setDriver('GV3', rundayiso)
                    #self.nodes['program' + str(z['uid'])].setDriver('GV4', z['remaining'] % 60)

        except:
            LOGGER.error('Unable to update programs')

        # Now fill in precip forecast and fields
        try:
            precip = ["","",""]

            now = datetime.now()
            today = now.strftime("%Y-%m-%d")

            mixer_data = rm.RmApiGet(top_level_url, access_token, 'api/4/mixer/' + today + '/3')
            #LOGGER.debug(mixer_data)

            precip[0] = mixer_data['mixerDataByDate'][0]['rain']
            precip[1] = mixer_data['mixerDataByDate'][1]['qpf']
            precip[2] = mixer_data['mixerDataByDate'][2]['qpf']

            for i in range(0,2):
                if  precip[i] == None:
                    precip[i] = 0

            rain = float(precip[0])
            qpf1 = float(precip[1])
            qpf2 = float(precip[2])
            units_uom = '82'

            if self.units != 'metric':
                rain = round((rain /25.4),2)
                qpf1 = round((qpf1 /25.4),2)
                qpf2 = round((qpf2 /25.4),2)
                units_uom = '105'
            #LOGGER.debug(precip[0])
            self.nodes['precip'].setDriver('ST', rain, uom=units_uom)
            self.nodes['precip'].setDriver('GV0', qpf1, uom=units_uom)
            self.nodes['precip'].setDriver('GV1', qpf2, uom=units_uom)

        except:
            LOGGER.error("Couldn't update precipation data or forecast")

    def longPoll (self):
        if self.discovery_done == False:
            return

        if self.access_token == None:
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

        rain_delay, rain_sensor, freeze = rm.GetRmRainSensorState(top_level_url, access_token, self.hwver)

        self.setDriver('GV2', math.trunc(rain_delay / 60))
        if self.hwver != 1:
            self.setDriver('GV1', rain_sensor)
            self.setDriver('GV3', freeze)
        else:
            self.setDriver('GV1', 2)
            self.setDriver('GV3', 2)
            #Set these drivers to NA for hardware version 1 RMs, not supported

    def query (self, command=None):
        """
        Optional.
        By default a query to the control node reports the FULL driver set for ALL
        nodes back to ISY. If you override this method you will need to Super or
        issue a reportDrivers() to each node manually.
        """
        self.check_params()
        for node in self.nodes:
            self.nodes[node].reportDrivers()

    def discover (self, *args, **kwargs):
        if self.host == "":
            pass

        global top_level_url
        global access_token
        top_level_url = "https://" + self.host + ":" + str(self.port) + "/"

        #Get the rainmachine hardware level and apiVersion
        rmdata=rm.getRainMachineVersion(top_level_url)
        if rmdata == None:
            self.hwver = 2
        else:
            self.hwver = rmdata['hwVer']
            apiver = rmdata['apiVer']

        LOGGER.info("Rainmachine Hardware version: {0}, API Version: {1}".format(self.hwver,apiver))
        if self.hwver == 1:
            self.port = 443

        #Get the rainmachine access_token for further API calls

        access_token = rm.getRainmachineToken(self.password, top_level_url)
        if access_token == None:
            return

        access_token = '?access_token=' + access_token
        # LOGGER.debug(self.access_token)

        # Collect the zone information from the Rainmachine
        zone_data = rm.RmApiGet(top_level_url, access_token, 'api/4/zone')

        if zone_data == None:
            LOGGER.error('Can\'t get Rainmachine zone data (url {0:s}, access_token {1:s}'.format(top_level_url,access_token))
            return

        for z in zone_data['zones']:
            self.addNode(
                RmZone(self, self.address, 'zone' + str(z['uid']), 'Zone ' + str(z['uid']) + " - " + z['name']))

        # Collect the program information from the Rainmachine
        program_data = rm.RmApiGet(top_level_url, access_token, 'api/4/program')
        #LOGGER.debug(program_data)
        if program_data == None:
            LOGGER.error('Can\'t get Rainmachine programs (url {0:s}, access_token {1:s}'.format(top_level_url,access_token))
            return

        for z in program_data['programs']:
            self.addNode(
                RmProgram(self, self.address, 'program' + str(z['uid']), z['name']))

        #set up nodes for rain and qpf data for today and the next 2 days

        self.addNode(RmPrecip(self, self.address, 'precip', 'Precipitation'))

        self.discovery_done = True

    def delete (self):
        LOGGER.info('Rainmachine Nodeserver deleted')

    def stop (self):
        self.setDriver('GV0', 0)
        LOGGER.info('Rainmachine NodeServer stopped.')

    def check_params (self):
        self.set_configuration(self.polyConfig)

        LOGGER.info("Adding configuration")
        self.addCustomParam({
            'Hostname': self.host,
            'Password': self.password,
            'Units': self.units,
        })

        self.myConfig = self.polyConfig['customParams']

        # Remove all existing notices
        LOGGER.info("remove all notices")
        self.removeNoticesAll()

        # Add a notice?
        if self.host == "":
            self.addNotice("Hostname or IP address of the Rainmachine device is required.")
        if self.password == "":
            self.addNotice("Password for Rainmachine is required.")
        if self.units == "":
            self.addNotice("Units to display rain information for ISY Precipitation Node.")

    def set_configuration (self, config):

        LOGGER.info("Check for existing configuration value")

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

    def remove_notices_all (self, command):
        LOGGER.info('remove_notices_all: notices={}'.format(self.poly.config['notices']))
        # Remove all existing notices
        self.removeNoticesAll()

    def update_profile (self, command):
        LOGGER.info('update_profile:')
        st = self.poly.installprofile()
        return st

    def set_rain_delay(self, command):
        st = rm.RmSetRainDelay(top_level_url, access_token, command)
        return st

    id = 'RainMachine'

    commands = {
        'QUERY': query,
        'DISCOVER': discover,
        'UPDATE_PROFILE': update_profile,
        'REMOVE_NOTICES_ALL': remove_notices_all,
        'RAIN_DELAY': set_rain_delay
    }

    drivers = [
        {'driver': 'ST', 'value': 1, 'uom': 2},
        {'driver': 'GV0', 'value': 0, 'uom': 2},
        {'driver': 'GV1', 'value': '0', 'uom': '25'},
        {'driver': 'GV2', 'value': '0', 'uom': '45'},
        {'driver': 'GV3', 'value': '0', 'uom': '25'}
    ]

class RmZone(polyinterface.Node):
    id = "zone"

    def __init__ (self, controller, primary, address, name):
        #LOGGER.debug('in RmZone class')
        #LOGGER.debug(controller)
        #LOGGER.debug(primary)
        #LOGGER.debug(address)
        #LOGGER.debug(name)
        #LOGGER.debug('end RmZone class')
        super(RmZone, self).__init__(controller, primary, address, name)

    #def setDriver (driver, value):
    #    super(RmZone).setDriver(driver, value, report=True, force=True)

    def zone_run (self,command):
        val = int(command.get('value'))
        LOGGER.debug(command)
        rm.RmZoneCtrl(top_level_url, access_token, command)

    def zone_stop (self,command):
        #LOGGER.debug(command)
        rm.RmZoneCtrl(top_level_url, access_token, command)

    def query(self):
        self.reportDrivers()

    drivers = [
        {'driver': 'ST', 'value': '0', 'uom': '25'}, # Zone state
        {'driver': 'GV3', 'value': '0', 'uom': '45'},  # Zone runtime minutes remaining
        {'driver': 'GV4', 'value': '0', 'uom': '58'}, # Zone runtime seconds remaining
    ]

    commands = {
        'RUN': zone_run,
        'STOP': zone_stop,
        'QUERY': query
    }

class RmProgram(polyinterface.Node):
    id = "program"

    def __init__ (self, controller, primary, address, name):

        super(RmProgram, self).__init__(controller, primary, address, name)

    def program_run (self,command):
        #LOGGER.debug(command)
        rm.RmProgramCtrl(top_level_url, access_token, command)

    def program_stop (self,command):
        #LOGGER.debug(command)
        rm.RmProgramCtrl(top_level_url, access_token, command)

    def query(self):
        self.reportDrivers()

    drivers = [
        {'driver': 'ST', 'value': '0', 'uom': '25'}, # Program status -
        {'driver': 'GV3', 'value': '0', 'uom': '25'}  # Program nextrun
    #    {'driver': 'GV4', 'value': '0', 'uom': '58'}, #
    ]

    commands = {
        'RUN': program_run,
        'STOP': program_stop,
        'QUERY': query
    }

class RmPrecip(polyinterface.Node):
    id = "precip"

    def __init__ (self, controller, primary, address, name):
        super(RmPrecip, self).__init__(controller, primary, address, name)

    def query (self):
        self.reportDrivers()

    drivers = [
        {'driver': 'ST', 'value': '0', 'uom': '82'},  # Rain today
        {'driver': 'GV0', 'value': '0', 'uom': '82'},  # Precip forecast for tomorrow
        {'driver': 'GV1', 'value': '0', 'uom': '82'}  # Precip forecast for tomorrow
    ]

    commands = {
        'QUERY': query
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
