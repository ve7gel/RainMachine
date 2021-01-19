import polyinterface
from datetime import datetime

from rm_functions import rmfuncs as rm

LOGGER = polyinterface.LOGGER


class RmPrecip( polyinterface.Node ):
    id = "precip"

    def __init__ (self, controller, primary, address, name, url, token, hwver, units):
        self.url = url
        self.token = token
        self.hwver = hwver
        self.units = units
        super( RmPrecip, self ).__init__( controller, primary, address, name )

    def set_Driver (self):
        # Now fill in precip forecast and fields

        try:
            precip = ["", "", "", ""]

            # now = datetime.now()
            today = datetime.now().strftime( "%Y-%m-%d" )

            mixer_data = rm.RmApiGet( self.url, self.token, 'api/4/mixer/' + today + '/3' )
            LOGGER.debug( "Mixer data: {}".format( mixer_data ) )

            precip[0] = mixer_data['mixerDataByDate'][0]['rain']
            precip[1] = mixer_data['mixerDataByDate'][0]['qpf']
            precip[2] = mixer_data['mixerDataByDate'][1]['qpf']
            precip[3] = mixer_data['mixerDataByDate'][2]['qpf']
            LOGGER.debug( "Precip list: {}".format( precip ) )
            for i in range( 0, 3 ):
                if precip[i] == None:
                    precip[i] = 0
            # LOGGER.debug("Precip list2: {}".format(precip))

            rain = float( precip[0] )
            qpf1 = float( precip[1] )
            qpf2 = float( precip[2] )
            qpf3 = float( precip[3] )
            units_uom = '82'

            if self.units != 'metric':
                rain = round( (rain / 25.4), 2 )
                qpf1 = round( (qpf1 / 25.4), 2 )
                qpf2 = round( (qpf2 / 25.4), 2 )
                qpf3 = round( (qpf3 / 25.4), 2 )
                units_uom = '105'
            self.setDriver( 'ST', rain, uom=units_uom )
            self.setDriver( 'GV0', qpf1, uom=units_uom )
            self.setDriver( 'GV1', qpf2, uom=units_uom )
            self.setDriver( 'GV2', qpf3, uom=units_uom )

        except:
            LOGGER.error( "Couldn't update precipation data or forecast" )

    def query (self):
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
