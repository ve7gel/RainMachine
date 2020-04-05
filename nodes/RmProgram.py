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

    '''
    def shortPoll(self):

        if self.program_data is None:
            LOGGER.error(
                'Can\'t get Rainmachine program data')
            return

        LOGGER.debug("Program data: {}".format(self.program_data))

        try:
            for z in self.program_data['programs']:
                #self.nodes['program' + str(z['uid'])].setDriver('ST', z['status'])
                self.setDriver('ST', z['status'])
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

                #self.nodes['program' + str(z['uid'])].setDriver('GV3', rundayiso)
                self.setDriver("GV3", rundayiso)
        except:
            LOGGER.error('Unable to update programs')
    '''

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
