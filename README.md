# Rainmachine Nodeserver
To interface Green Electronics LLC rainmachine irrigation controller to the ISY994

Copyright 2020 Gordon Larsen MIT License

#### Installation

This nodeserver was developed on the rainmachine Mini-8. It should work similarly on other devices, 
    but hasn't been tested.
Software currently fully supports hardware version 2, with API version 4.1 or higher.
On hardware version 1, mixer values(rain today and qpf values), rain sensor and freeze protect states are not available.
 
Tested OK on Polisy and RPi

## Issues
Please raise any issues on the UDI forum at "https://forum.universal-devices.com/forum/170-green-electronics-rainmachine/".  
Github is not watched.

### Node drivers for use in substitution variables
#### Zones:
 * 'ST', Zone state
 * 'GV3', Zone runtime minutes remaining
 * 'GV4', Zone runtime seconds remaining
 * 'GV5', Is this a master zone?
    ]
#### Programs:
 * 'ST', Program status
 * 'GV3', Program nextrun day

#### Precipitation:
 * 'ST',  Rain today
 * 'GV0', Precip forecast for today 
 * 'GV1', Precip forecast for tomorrow
 * 'GV2', Precip forecast for day after tomorrow

#### Restrictions:
 * 'ST', Rain Sensor State
 * 'GV0', Rain Delay Remaining
 * 'GV1', Freeze Protect
 * 'GV2', Hourly restrictions?
 * 'GV3', Month restrictions?
 * 'GV4', Weekday restrictions?

## Release Notes
- 0.5.7 27/01/2022
  - minor profile update
- 0.5.6 14/04/2021
    - update list of disallowed zone name characters.  These are stripped from the name when imported from the RM.
- 0.5.5 18/01/2021
    - correct an entry in the nls that was preventing controller status from showing in ISY program status fields.
- 0.5.4 08/12/2020
    - fix a bug introduced in 0.5.3 where loglevel was not retained across restarts.
- 0.5.3 07/12/2020
    - add "Winter" mode. Clean up some profile entries
- 0.5.2 19/062020
    - update to configuration docs
- 0.5.1 13/06/2020
    - update requirements for polyinterface 2.1.0
- 0.5.0 08/04/2020
    - trap network error in restrictions update.
    - add error trapping to recover more gracefully from loss of contact with the Rainmachine
    - Restructure code to move node functions to separate files. 
- 0.4.0 03/04/2020
    - move rain sensor, freeze protect, rain delay to new 'Restrictions' node.  Add info for active hourly, weekday, monthly restrictions 
- 0.3.0 014/02/2020
    - add delay between node adds during discovery
    - add some support for Master Zone - still needs some testing
- 0.2.6 10/02/2020
    - initiate immediate node updates at start instead of waiting for first shortPoll
    - minor changes in initial loglevel setting code
    - added forecast today in precip node
- 0.2.5 08/02/2020
    - update install.sh and add requests to requirements.txt 
- 0.2.4 06/02/2020
    - display loglevels as text instead of numbers
    - catch the case where the api call to rainsensorstate returns "None" in the
        event of a dropped connection to the Rainmachine
- 0.2.3 06/02/2020
    - change json method for compatibility with earlier
        versions of Python requests.
- 0.2.2 06/02/2020
    - change default error level to debug
- 0.2.1 05/02/2020
    - clean up code a little.
- 0.2.0 04/02/2020
    - added support for HW Vers 1. Tested only in simulation. 
    - fixed apiver calls for HD12 & HD16
    - added code to strip some characters not supported by ISY from zone
        and program names. Convert '&' to 'and'.
    - added ability to set logging level from primary node.
- 0.1.5 03/02/2020
    - added some error trapping to figure out HD12 apiver call
        response.
- 0.1.4 02/02/2020
    - fixed logic error (I think) for next  run day display.
- 0.1.3 02/02/2020
    - added a check for hardware version to change https port
        numbers dependent on version.
    - added us units conversion for precip displays.
- 0.1.2 30/01/2020
    - added rain delay setting in primary node.
- 0.1.1 30/01/2020
    - Fix up some error handling.
- 0.1.0 29/01/2020 
    - Initial beta release.