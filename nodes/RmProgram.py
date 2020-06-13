from datetime import datetime

import polyinterface

from rm_functions import rmfuncs as rm

LOGGER = polyinterface.LOGGER

class RmProgram(polyinterface.Node):
    id = "program"

    def __init__(self, controller, primary, address, name, url, token):
        self.url = url
        self.token = token
        #self.program_data = rm.RmApiGet(url, token, 'api/4/program')
        super(RmProgram, self).__init__(controller, primary, address, name)


    def set_Driver(self, driver, value,):
        if driver == 'ST':
            self.setDriver(driver , value)
            #LOGGER.debug( "in setDriver: {} {} {}".format( self, driver, value ) )
        elif driver == 'GV3':

            if value is None:
                rundayiso = '0'  # Not scheduled
            else:
                nextrunday = value
                nextrunday = datetime.date( datetime.strptime( nextrunday, '%Y-%m-%d' ) )
                now = datetime.date( datetime.now() )
                # LOGGER.debug("Now= {0}, Next run day = {1}".format(now,nextrunday))
                nextrun = str( nextrunday - now )
                #LOGGER.debug("Nextrun is {}".format(nextrun))

                if str( nextrun[0] ) == '0':
                    rundayiso = '8'  # Today
                elif str( nextrun[0] ) == '1':
                    rundayiso = '9'  # Tomorrow
                else:
                    nextrun = value
                    runday = datetime.date( datetime.strptime( nextrun, '%Y-%m-%d' ) )
                    rundayiso = runday.isoweekday()

            self.setDriver(driver, rundayiso)
            #LOGGER.debug( "in setDriver: {} {} {}".format( self, driver, rundayiso ) )
        else:
            LOGGER.error("Invalid driver called in RmProgram")

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
