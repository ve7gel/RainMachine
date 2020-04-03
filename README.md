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
Please raise any issues on the UDI forum at "https://forum.universal-devices.com/forum/170-green-electronics-rainmachine/"
Github is not watched.

## Release Notes
- 0.4.0 04/03/2020
    - move rain sensor, freeze protect, rain delay to new 'Restrictions' node.  Add info for active restrictions for hourly, weekday, monthly
- 0.3.0 02/14/2020
    - add delay between node adds during discovery
    - add some support for Master Zone - still needs some testing
    
- 0.2.6 02/10/2020
    - initiate immediate node updates at start instead of waiting for first shortPoll
    - minor changes in initial loglevel setting code
    - added forecast today in precip node
    
- 0.2.5 02/08/2020
    - update install.sh and add requests to requirements.txt
    
- 0.2.4 02/06/2020
    - display loglevels as text instead of numbers
    - catch the case where the api call to rainsensorstate returns "None" in the
        event of a dropped connection to the Rainmachine
    
- 0.2.3 02/06/2020
    - change json method for compatibility with earlier
        versions of Python requests.
    
- 0.2.2 02/06/2020
    - change default error level to debug
    
- 0.2.1 02/05/2020
    - clean up code a little.
     
- 0.2.0 02/04/2020
    - added support for HW Vers 1. Tested only in simulation. 
    - fixed apiver calls for HD12 & HD16
    - added code to strip some characters not supported by ISY from zone
        and program names. Convert '&' to 'and'.
    - added ability to set logging level from primary node.
    
- 0.1.5 02/03/2020
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