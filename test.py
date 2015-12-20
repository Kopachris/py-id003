#!/usr/bin/env python3

from id003 import BillVal
import id003
import serial.tools.list_ports
import serial
import time


def main():
    
    timeout = 0.05  # 50 ms, per ID-003 specs
    baud = 9600
    port = 'COM11'  # JCM UAC device (USB serial adapter)
    
    bv = BillVal(port, baud, serial.EIGHTBITS, serial.PARITY_EVEN, timeout=timeout)
    print("Please connect bill validator.")
    bv.power_on()
    
    if bv.init_status == id003.POW_UP:
        print("BV powered up normally.")
    elif bv.init_status == id003.POW_UP_BIA:
        print("BV powered up with bill in acceptor.")
    elif bv.init_status == id003.POW_UP_BIS:
        print("BV powered up with bill in stacker.")
        
    bv.poll()


if __name__ == '__main__':
    main()
