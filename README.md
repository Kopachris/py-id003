Update 16 August 2022: This repository is being archived as I have no plans to ever update it again.

# py-id003
Python module for interacting with bill validators using JCM's ID-003 serial protocol

## Usage
0. This program has only been tested to work with UBA-10 with jumpers in the LEFT position. UBA-10 with jumpers in the RIGHT position did not work in testing. This program hasn't been tested with UBA-14, iVizion, or WBA yet (TODO).
0. Ensure all four of the JCM UAC device's DIP switches are set to ON
1. Power on the JCM UAC device
2. Plug the JCM UAC device into your computer's USB port
3. Verify the device driver has installed correctly
  1. Open the Windows Device Manager
  2. The JCM UAC device should show up under COM and LPT ports as a USB serial adapter
  3. The settings for the serial port should be:
    * 9600 baud
    * 8 data bits
    * 1 stop bit
    * Even parity
    * No flow control
4. Run the protocol analyzer by double-clicking "run.bat"
5. Connect the bill validator to the JCM UAC device
