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
import configparser
import threading

import serial.tools.list_ports
from serial.serialutil import SerialException

from collections import OrderedDict

X_SIZE, Y_SIZE = t.get_size()

CONFIG_FILE = 'bv.ini'
CONFIG = configparser.ConfigParser()
CONFIG.read(CONFIG_FILE)


def kb_loop(bv, stdout_lock, bv_lock):
    global CONFIG

    print("Press Q at any time to quit, or H for help")
    while True:
        with stdout_lock:
            opt = t.get_key(0.1)
        if opt is not None:
            opt = opt.lower()
        if opt == b'q':
            bv.bv_on = False
            with open(CONFIG_FILE, 'w') as f:
                CONFIG.write(f)
            return
        elif opt == b'h':
            print("Q - Quit\n" "H - Help\n" "S - Settings menu\n"
                  "R - Reset and initialize bill validator\n"
                  "P - Pause bill validator\n" "M - Stop polling "
                  "and return to main menu")
        elif opt == b'm':
            return
        elif opt == b's':
            print("Not implemented yet")
        elif opt == b'r':
            print("Not implemented yet")
        elif opt == b'p':
            print("Not implemented yet")


def poll_loop(bv, stdout_lock, bv_lock, interval=0.2):
    print("Please connect bill validator.")
    bv.power_on()
    
    if bv.init_status == id003.POW_UP:
        logging.info("BV powered up normally.")
    elif bv.init_status == id003.POW_UP_BIA:
        logging.info("BV powered up with bill in acceptor.")
    elif bv.init_status == id003.POW_UP_BIS:
        logging.info("BV powered up with bill in stacker.")

    while True:
        poll_start = time.time()
        if not bv.bv_on:
            return
        with bv_lock:
            status, data = bv.req_status()
            if (status, data) != bv.bv_status and status in bv.bv_events:
                with stdout_lock:
                    bv.bv_events[status](data)
        bv.bv_status = (status, data)
        wait = interval - (time.time() - poll_start)
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
    global CONFIG
    
    comport = CONFIG['main']['comport']
    poll_interval = float(CONFIG['main']['poll_interval'])

    main_menu = OrderedDict()
    main_menu['r'] = "Run"
    main_menu['s'] = "Settings"
    main_menu['c'] = "Select COM port"
    main_menu['q'] = "Quit"
    
    choice = display_menu(main_menu, '>>>', "ID-003 protocol analyzer", "Using COM port %s" % comport).lower()
    
    if choice == 'r':
        t.wipe()
        try:
            bv = id003.BillVal(comport, threading=True)
        except SerialException:
            print("Unable to open serial port")
            q = 'x'
            while q not in 'qm':
                q = input("(Q)uit or (M)ain menu? ").lower()
                if q == 'q':
                    return True
                elif q == 'm':
                    return
        
        stdout_lock = threading.Lock()
        bv_lock = threading.Lock()
        
        poll_args = (bv, stdout_lock, bv_lock, poll_interval)
        poll_thread = threading.Thread(target=poll_loop, args=poll_args)
        
        kb_args = (bv, stdout_lock, bv_lock)
        kb_thread = threading.Thread(target=kb_loop, args=kb_args)
        
        poll_thread.start()
        while bv.bv_status != (id003.IDLE, b''):
            # wait for power-up before starting keyboard loop
            continue
        kb_thread.start()
        kb_thread.join()
        
        if not bv.bv_on:
            # kb_thread quit, not main menu
            bv.com.close()
            return True
        else:
            # terminate poll thread
            bv.bv_on = False
            poll_thread.join()
            bv.com.close()
            del poll_thread
            del kb_thread
            del bv
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
            CONFIG['main']['comport'] = ports[port].device
        return
    elif choice == 'q':
        return True
	
	
if __name__ == '__main__':
    while not main():
        continue
    with open(CONFIG_FILE, 'w') as f:
        # save configuration on program exit
        CONFIG.write(f)