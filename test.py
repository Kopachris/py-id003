#!/usr/bin/env python3

from id003 import BillVal
import id003
import serial.tools.list_ports
import serial
import time


def main():
    
    timeout = 0.2
    baud = 9600
    port = 'COM11'  # JCM UAC device (USB serial adapter)
    
    bv = BillVal(port, baud, serial.EIGHTBITS, serial.PARITY_EVEN, timeout=timeout)
    bv.power_on()
    
    if bv.init_status == id003.POW_UP:
        print("BV powered up normally, version:\n\t" + bv.bv_version)
    elif bv.init_status == id003.POW_UP_BIA:
        print("BV powered up with bill in acceptor.")
    elif bv.init_status == id003.POW_UP_BIS:
        print("BV powered up with bill in stacker.")
        
    while True:
        status, data = bv.req_status()
        
        time.sleep(0.2)


if __name__ == '__main__':
    main()