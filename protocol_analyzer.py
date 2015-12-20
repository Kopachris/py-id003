#!/usr/bin/env python3

import os
import sys
src_dir = os.path.abspath('src/')
sys.path.append(src_dir)
sys.ps1 = ''
sys.ps2 = ''

import id003
import termutils as t

import time
import logging
import msvcrt

import serial.tools.list_ports

from collections import OrderedDict

X_SIZE, Y_SIZE = t.get_size()
COMPORT = 'COM3'


def poll_loop(bv, interval):
    while True:
        poll_start = time.time()
        status, data = bv.req_status()
        if (status, data) != bv.bv_status:
            if status in bv.bv_events:
                bv.bv_events[status](data)
        bv.bv_status = (status, data)
        wait = interval - (time.time() - poll_start)
        if msvcrt.kbhit():
            k = msvcrt.getch()
            if k == 'q':
                sys.exit()
        if wait > 0.0:
            time.sleep(wait)
            
            
def display_menu(menu, prompt='>>>', header='', info=''):
    if len(menu) > Y_SIZE - 5:
        raise ValueError("Too many menu options")
    
    # print the header
    t.wipe()
    t.set_pos(0, 0)
    print(header.center(X_SIZE), end='')
    print('=' * X_SIZE, end='')
    
    # print the menu items
    for k, v in menu.items():
        print("{}) {}".format(k, v))
        
    # print prompt and info
    print(prompt, end=' ')
    x, y = t.get_pos()
    print('\n\n' + info)
    t.set_pos(x, y)
    
    # get user's choice
    k = None
    while k not in menu:
        k = input('')
        t.set_pos(x, y)
        print(' ' * (X_SIZE - x), end='')
        t.set_pos(x, y)
    
    return k


def main():
    global COMPORT

    main_menu = OrderedDict()
    main_menu['r'] = "Run"
    main_menu['s'] = "Settings"
    main_menu['c'] = "Select COM port"
    main_menu['q'] = "Quit"
    
    choice = display_menu(main_menu, '>>>', "ID-003 protocol analyzer", "Using COM port %s" % COMPORT).lower()
    
    if choice == 'r':
        t.wipe()
        bv = id003.BillVal(COMPORT)
        print("Please connect bill validator.")
        bv.power_on()
        
        if bv.init_status == id003.POW_UP:
            logging.info("BV powered up normally.")
        elif bv.init_status == id003.POW_UP_BIA:
            logging.info("BV powered up with bill in acceptor.")
        elif bv.init_status == id003.POW_UP_BIS:
            logging.info("BV powered up with bill in stacker.")
            
        print("Press Q at any time to quit")
        poll_loop(bv, 0.2)
        return
    elif choice == 's':
        t.wipe()
        print("Settings not available yet")
        input("Press enter to continue.")
        return
    elif choice == 'c':
        t.wipe()
        com_menu = OrderedDict()
        ports = list(serial.tools.list_ports.comports())
        for i, p in enumerate(ports):
            com_menu[str(i+1)] = p.description
        com_menu['q'] = "Back to main menu"
        port = display_menu(com_menu, '>>>', "Select COM port")
        if port == 'q':
            return
        else:
            port = int(port) - 1
            COMPORT = ports[port].device
        return
    elif choice == 'q':
        sys.exit()
	
	
if __name__ == '__main__':
    while 1:
        main()