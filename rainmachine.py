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

import urllib3
import os
import io
import json
import requests
import subprocess as sp
from rm_functions import mk_profile
import ssl

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
        self.poly.onConfig(self.process_config)
        self.address = 'rainmachine'
        self.primary = self.address
        self.host = ""
        self.password = ""
        self.access_token = ""
        self.timeout = 5

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
        serverdata = mk_profile.get_server_data(LOGGER)
        LOGGER.debug(serverdata)
        mk_profile.update_version(LOGGER)
        self.check_params()
        self.discover()
        self.setDriver('ST', 1)

    def shortPoll (self):
        LOGGER.debug("shortPoll")
        pass

    def longPoll (self):
        #RainMachine Heartbeat
        try:
            response, result = sp.getstatusoutput("ping -c1 -W " + str(self.timeout - 1) + " " + self.host)

            if response == 0:
                self.setDriver('GV0',1)
                LOGGER.info('RainMachine Heartbeart heard')
            else:
                self.setDriver('GV0',0)
                LOGGER.info('RainMachine Heartbeat missed')
        except:
            LOGGER.error('Ping Error')
            # Capture any exception

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
        self.top_level_url = "https://" + self.host + ":8080/"

        self.access_token = getRainmachineToken(self.password, self.top_level_url)
        self.access_token = '?access_token='+self.access_token
        LOGGER.debug(self.access_token)

        zone_data = getRmZones(self.top_level_url,self.access_token)
        LOGGER.debug(zone_data)

        for z in zone_data['zones']:
            self.addNode(RmZone(self, self.address, 'zone'+ str(z['uid']), z['name']))


    def delete (self):
        LOGGER.info('Rainmachine Nodeserver deleted')

    def stop (self):
        LOGGER.debug('Rainmachine NodeServer stopped.')

    def process_config (self, config):

        LOGGER.info("process_config: Enter config={}".format(config));
        mk_profile.profile_zip(LOGGER)
        self.poly.installprofile()

        self.removeNoticesAll()

    def check_params (self):
        self.set_configuration(self.polyConfig)
        # self.setup_nodedefs(self.units)

        LOGGER.info("Adding configuration")
        self.addCustomParam({
            'Hostname': self.host,
            'Password': self.password,
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

    def set_configuration (self, config):
        default_ip = ""
        default_elevation = 0

        LOGGER.info("Check for existing configuration value")

        if 'Hostname' in config['customParams']:
            self.host = config['customParams']['Hostname']
        else:
            self.host = ""

        if 'Password' in config['customParams']:
            self.password = config['customParams']['Password']
        else:
            self.password = ""

        return

    def remove_notices_all (self, command):
        LOGGER.info('remove_notices_all: notices={}'.format(self.poly.config['notices']))
        # Remove all existing notices
        self.removeNoticesAll()

    def update_profile (self, command):
        LOGGER.info('update_profile:')
        st = self.poly.installprofile()
        return st

    id = 'RainMachine'
    commands = {
        'QUERY': query,
        'DISCOVER': discover,
        'UPDATE_PROFILE': update_profile,
        'REMOVE_NOTICES_ALL': remove_notices_all,
    }
    drivers = [
        {'driver': 'ST', 'value': 1, 'uom': 2},
        {'driver': 'GV0', 'value': 0, 'uom': 25},
        {'driver': 'GV1', 'value': 0, 'uom': 25},
        {'driver': 'GV2', 'value': 0, 'uom': 25},
        {'driver': 'GV3', 'value': 0, 'uom': 25}
    ]

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
    response = requests.get(url + 'api/4/zone' + access_token, verify=False)
    rm_zone_data = json.loads(response.content)
    return rm_zone_data


class RmZone(polyinterface.Node):

    def __init__ (self, controller, primary, address, name):
        super(RmZone, self).__init__(controller, primary, address, name)

    id = 'zone'
    drivers = [
        {'driver': 'ST', 'value': 0, 'uom': 'I_ZONE_STATUS'},
        {'driver': 'GV0', 'value': 0, 'uom': 0},
        {'driver': 'GV1', 'value': 0, 'uom': 2}
    ]


    def setDriver(self, driver, value):
        LOGGER.debug(driver, str(value))
        super(RmZone, self).setDriver(driver, value, report=True, force=True)



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
