#!/usr/bin/env python3

from id003 import BillVal
import id003
import serial.tools.list_ports
import serial
import time
import logging


def main():
    port = 'COM11'  # JCM UAC device (USB serial adapter)
    
    bv = BillVal(port)
    print("Please connect bill validator.")
    bv.power_on()
    
    if bv.init_status == id003.POW_UP:
        logging.info("BV powered up normally.")
    elif bv.init_status == id003.POW_UP_BIA:
        logging.info("BV powered up with bill in acceptor.")
    elif bv.init_status == id003.POW_UP_BIS:
        logging.info("BV powered up with bill in stacker.")
        
    bv.poll()


if __name__ == '__main__':
    main()
