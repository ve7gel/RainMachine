class RmProgram(polyinterface.Node):
    id = "program"

    def __init__ (self, controller, primary, address, name):
        #LOGGER.debug('in RmZone class')
        #LOGGER.debug(controller)
        #LOGGER.debug(primary)
        #LOGGER.debug(address)
        #LOGGER.debug(name)
        #LOGGER.debug('end RmZone class')
        super(RmProgram, self).__init__(controller, primary, address, name)

    #def setDriver (driver, value):
    #    super(RmZone).setDriver(driver, value, report=True, force=True)

    def zone_run (self,command):
        rm.RmZoneCtrl(top_level_url, access_token, command)

    def zone_stop (self,command):
        #LOGGER.debug(command)
        rm.RmZoneCtrl(top_level_url, access_token, command)

    def query(self):
        self.reportDrivers()

    drivers = [
        {'driver': 'ST', 'value': '0', 'uom': '25'}, # Program state -
        {'driver': 'GV3', 'value': '0', 'uom': '45'},  # Zone runtime minutes remaining
        {'driver': 'GV4', 'value': '0', 'uom': '58'}, # Zone runtime seconds remaining
    ]

    commands = {
        'RUN': zone_run,
        'STOP': zone_stop,
        'QUERY': query
    }
