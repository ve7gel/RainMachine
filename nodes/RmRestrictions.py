import polyinterface
LOGGER = polyinterface.LOGGER
from rm_functions import rmfuncs as rm
from math import trunc

class RmRestrictions(polyinterface.Node):
    id = "restrict"

    def __init__(self, controller, primary, address, name, url, token, hwver):
        self.url = url
        self.token = token
        self.hwver = hwver
        super(RmRestrictions, self).__init__(controller, primary, address, name)

    def set_Driver(self):

        # rain_delay, rain_sensor, freeze = rm.GetRmRainSensorState(self.top_level_url, self.access_token)
        try:
            restrictions = rm.GetRmRestrictions( self.url, self.token )
            LOGGER.debug( "Sensor/restrictions data: {}".format( restrictions ) )

            rain_delay_time = restrictions['rainDelayCounter']
            if rain_delay_time == -1:
                rain_delay_time = 0

            freeze = restrictions['freeze']

            self.setDriver('GV0', trunc( rain_delay_time /60))
            self.setDriver('GV2', int(restrictions['hourly'] is True))
            self.setDriver('GV3', int(restrictions['month'] is True))
            self.setDriver('GV4', int(restrictions['weekDay'] is True))

            if self.hwver == 1:
                rain_sensor = restrictions['rainSensor']
                self.setDriver( 'ST', rain_sensor)
                self.setDriver( 'GV1', freeze )
            else:
                self.setDriver( 'ST', 0 )
                self.setDriver( 'GV1', 0 )
                # Set these drivers to N/A for hardware version 1 RMs, not supported
        except:
            LOGGER.error("Unable to update Restrictions data")

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
