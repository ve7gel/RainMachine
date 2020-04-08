from math import trunc

import polyinterface

from rm_functions import rmfuncs as rm

LOGGER = polyinterface.LOGGER

class RmZone(polyinterface.Node):
    id = "zone"

    def __init__(self, controller, primary, address, name, url, token):
        self.url = url
        self.token = token

        super(RmZone, self).__init__(controller, primary, address, name)

    def set_Driver(self, driver, value,):
        if driver == 'ST':
            self.setDriver(driver , value)
            #LOGGER.debug( "in zone setDriver: {} {} {}".format(self, driver, value ) )
        elif driver == 'GV3':
            self.setDriver(driver, trunc(value/60))
            #LOGGER.debug( "in zone setDriver: {} {} {}".format(self, driver, trunc(value / 60 ) ))

            self.setDriver('GV4', value % 60)
            #LOGGER.debug( "in zone setDriver: {} {} {}".format(self, 'GV4', value % 60 ) )
        elif driver == 'GV5':
            if value == 'master':
                master_zone = 1
            else:
                master_zone = 0
            self.setDriver(driver, master_zone)
            #LOGGER.debug( "in zone setDriver: {} {} {}".format(self, driver, master_zone ) )

        else:
            LOGGER.error("Invalid driver called in RmProgram")
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
