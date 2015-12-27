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


def get_denoms():
    denom = 0
    for k in CONFIG['bv.denom_inhibit']:
        if CONFIG['bv.denom_inhibit'].getboolean(k):
            denom |= id003.DENOMS[k]
    return [denom, 0]
    
    
def get_security():
    sec = 0
    for k in CONFIG['bv.security']:
        if CONFIG['bv.security'].getboolean(k):
            sec |= id003.DENOMS[k]
    return [sec, 0]
    

def get_directions():
    dir = 0
    for k in CONFIG['bv.direction']:
        if CONFIG['bv.direction'].getboolean(k):
            dir |= id003.DIRECTIONS[k]
    return [dir]
    
    
def get_optional():
    opt = 0
    for k in CONFIG['bv.optional']:
        if CONFIG['bv.optional'].getboolean(k):
            opt |= id003.OPTIONS[k]
    return [opt, 0]


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
            with stdout_lock:
                logging.debug("Entered settings menu from status poll")
                settings()
                logging.debug("Exited settings menu")
                bv.bv_status = None  # print current status after returning
                t.wipe()
        elif opt == b'r':
            with bv_lock:
                logging.debug("Sending reset command")
                status = None
                while status != id003.ACK:
                    bv.send_command(id003.RESET)
                    status, data = bv.read_response()
                    time.sleep(0.2)
                logging.debug("Received ACK")
                
                if bv.req_status()[0] == id003.INITIALIZE:
                    denom = get_denoms()
                    sec = get_security()
                    dir = get_directions()
                    opt = get_optional()
                    logging.info("Initializing bill validator")
                    bv.initialize(denom, sec, dir, opt)
                    
                while bv.req_status()[0] != id003.IDLE:
                    time.sleep(0.2)
                bv.bv_status = None
        elif opt == b'p':
            print("Not implemented yet")


def poll_loop(bv, stdout_lock, bv_lock, interval=0.2):
    denom = get_denoms()
    sec = get_security()
    dir = get_directions()
    opt = get_optional()
    
    print("Please connect bill validator.")
    bv.power_on(denom, sec, dir, opt)
    
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
                if stdout_lock.acquire(timeout=0.5):
                    bv.bv_events[status](data)
                    stdout_lock.release()
        bv.bv_status = (status, data)
        wait = interval - (time.time() - poll_start)
        if wait > 0.0:
            time.sleep(wait)


def display_header(text):
    t.set_pos(0, 0)
    print(text.center(X_SIZE), end='')
    print('=' * X_SIZE, end='')


def display_menu(menu, prompt='>>>', header='', info=''):
    if len(menu) > Y_SIZE - 5:
        raise ValueError("Too many menu options")
    
    # print the header
    t.wipe()
    display_header(header)
    
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
    
    
def settings():
    global CONFIG
    
    t.wipe()
    
    settings_menu = OrderedDict()
    settings_menu['e'] = "Denomination enable/inhibit"
    settings_menu['s'] = "Denomination security"
    settings_menu['d'] = "Direction enable/inhibit"
    settings_menu['o'] = "Optional functions"
    settings_menu['b'] = "Bar code ticket options"
    settings_menu['q'] = "Back"
    
    choice = display_menu(settings_menu, '>>>', "Settings",
                          "Changes will take effect next time bill validator is initialized")
    
    if choice == 'e':
        denom_settings()
    elif choice == 's':
        security_settings()
    elif choice == 'd':
        direction_settings()
    elif choice == 'o':
        opt_settings()
    elif choice == 'b':
        t.wipe()
        print("Barcode settings not available.")
        input("Press enter to go back")
    
    return


def opt_settings():
    global CONFIG
    
    t.wipe()
    display_header("Optional function settings")
    
    opts = dict()
    set_opts = OrderedDict()
    opt_txt = {
        'power_recovery': "Power recovery:\t\t\t\t",
        'auto_retry': "Auto-retry operaton:\t\t\t",
        '24_char_barcode': "Accept 24-character barcodes:\t\t",
        'near_full': "Stacker nearly full event:\t\t",
        'entrance_event': "Entrance sensor event:\t\t\t",
        'encryption': "Encryption:\t\t\t\t",
    }
    
    for i, k in enumerate(CONFIG['bv.optional'].keys()):
        opt_enabled = CONFIG['bv.optional'].getboolean(k)
        opts[i] = k
        set_opts[k] = opt_enabled
        
        print(opt_txt[k], end='')
        start_x, start_y = t.get_pos()
        if opt_enabled:
            print('X')
        else:
            print('_')
            
    print("\n\n_ = disabled, X = enabled")
    print("\nPress Enter to save and go back, or Esc to go back without saving")
    t.set_pos(start_x, 3)
    
    max_opt = len(CONFIG['bv.optional']) - 1
    cur_opt = 0
    while True:
        x, y = t.get_pos()
        c = t.getch()
        
        if c == b'\xe0H' and cur_opt > 0:
            # up
            t.set_pos(x, y-1)
            cur_opt -= 1
        elif c == b'\xe0P' and cur_opt < max_opt:
            # down
            t.set_pos(x, y+1)
            cur_opt += 1
        elif c == b'\t' and cur_opt == max_opt:
            # wrap around to first option
            t.set_pos(x, 3)
            cur_opt = 0
        elif c == b'\t':
            # next option, same as down
            t.set_pos(x, y+1)
            cur_opt += 1
        elif c == b'X' or c == b'x':
            set_opts[opts[cur_opt]] = True
            print('X', end='')
            if cur_opt < max_opt:
                t.set_pos(x, y+1)
                cur_opt += 1
            else:
                t.set_pos(x, y)
        elif c == b' ':
            set_opts[opts[cur_opt]] = False
            print('_', end='')
            if cur_opt < max_opt:
                t.set_pos(x, y+1)
                cur_opt += 1
            else:
                t.set_pos(x, y)
        elif c == b'\r':
            # save and go back
            CONFIG['bv.optional'] = set_opts
            return
        elif c == b'\x1b':
            # escape, go back without saving
            return
    
    
def direction_settings():
    global CONFIG
    
    t.wipe()
    display_header("Direction ihibit settings")
    
    opts = dict()
    set_opts = OrderedDict()
    for i, k in enumerate(CONFIG['bv.direction'].keys()):
        dir_enabled = CONFIG['bv.direction'].getboolean(k)
        opts[i] = k
        set_opts[k] = dir_enabled
        
        if k == 'fa':
            print("Front side up, left side in:\t\t", end='')
        elif k == 'fb':
            print("Front side up, right side in:\t\t", end='')
        elif k == 'bb':
            print("Back side up, left side in:\t\t", end='')
        elif k == 'ba':
            print("Back side up, right side in:\t\t", end='')
            
        start_x, start_y = t.get_pos()
        if dir_enabled:
            print('X')
        else:
            print('_')
            
    print("\n\n_ = enabled, X = inhibited")
    print("\nPress Enter to save and go back, or Esc to go back without saving")
    t.set_pos(start_x, 3)
    
    max_opt = len(CONFIG['bv.direction']) - 1
    cur_opt = 0
    while True:
        x, y = t.get_pos()
        c = t.getch()
        
        if c == b'\xe0H' and cur_opt > 0:
            # up
            t.set_pos(x, y-1)
            cur_opt -= 1
        elif c == b'\xe0P' and cur_opt < max_opt:
            # down
            t.set_pos(x, y+1)
            cur_opt += 1
        elif c == b'\t' and cur_opt == max_opt:
            # wrap around to first option
            t.set_pos(x, 3)
            cur_opt = 0
        elif c == b'\t':
            # next option, same as down
            t.set_pos(x, y+1)
            cur_opt += 1
        elif c == b'X' or c == b'x':
            set_opts[opts[cur_opt]] = True
            print('X', end='')
            if cur_opt < max_opt:
                t.set_pos(x, y+1)
                cur_opt += 1
            else:
                t.set_pos(x, y)
        elif c == b' ':
            set_opts[opts[cur_opt]] = False
            print('_', end='')
            if cur_opt < max_opt:
                t.set_pos(x, y+1)
                cur_opt += 1
            else:
                t.set_pos(x, y)
        elif c == b'\r':
            # save and go back
            CONFIG['bv.direction'] = set_opts
            return
        elif c == b'\x1b':
            # escape, go back without saving
            return

    
def security_settings():
    global CONFIG
    
    t.wipe()
    display_header("Denomination security settings")
    
    opts = dict()
    set_opts = OrderedDict()
    for i, k in enumerate(CONFIG['bv.security'].keys()):
        if id003.DENOM_MAP[k] in id003.ESCROW_USA:
            denom = id003.ESCROW_USA[id003.DENOM_MAP[k]]
        else:
            denom = None
            
        denom_enabled = CONFIG['bv.security'].getboolean(k)
        opts[i] = k
        set_opts[k] = denom_enabled
        
        if denom is not None:
            line = k + ' (' + denom + '):\t\t'
        else:
            line = k + ':\t\t\t'
        
        if denom_enabled:
            line += 'X'
        else:
            line += '_'
            
        print(line)
    
    print("\n\nX = high security, _ = low security")
    print("\nPress Enter to save and go back, or Esc to go back without saving")
    t.set_pos(25, 3)
    
    max_opt = len(CONFIG['bv.security']) - 1
    cur_opt = 0
    while True:
        x, y = t.get_pos()
        c = t.getch()
        
        if c == b'\xe0H' and cur_opt > 0:
            # up
            t.set_pos(x, y-1)
            cur_opt -= 1
        elif c == b'\xe0P' and cur_opt < max_opt:
            # down
            t.set_pos(x, y+1)
            cur_opt += 1
        elif c == b'\t' and cur_opt == max_opt:
            # wrap around to first option
            t.set_pos(x, 3)
            cur_opt = 0
        elif c == b'\t':
            # next option, same as down
            t.set_pos(x, y+1)
            cur_opt += 1
        elif c == b'X' or c == b'x':
            set_opts[opts[cur_opt]] = True
            print('X', end='')
            if cur_opt < max_opt:
                t.set_pos(x, y+1)
                cur_opt += 1
            else:
                t.set_pos(x, y)
        elif c == b' ':
            set_opts[opts[cur_opt]] = False
            print('_', end='')
            if cur_opt < max_opt:
                t.set_pos(x, y+1)
                cur_opt += 1
            else:
                t.set_pos(x, y)
        elif c == b'\r':
            # save and go back
            CONFIG['bv.security'] = set_opts
            return
        elif c == b'\x1b':
            # escape, go back without saving
            return
            
    
    
def denom_settings():
    global CONFIG
    
    t.wipe()
    display_header("Denomination enable/inhibit settings")
    
    opts = dict()
    set_opts = OrderedDict()
    for i, k in enumerate(CONFIG['bv.denom_inhibit'].keys()):
        if id003.DENOM_MAP[k] in id003.ESCROW_USA:
            denom = id003.ESCROW_USA[id003.DENOM_MAP[k]]
        else:
            denom = None
            
        denom_enabled = CONFIG['bv.denom_inhibit'].getboolean(k)
        opts[i] = k     # index into this config section
        set_opts[k] = denom_enabled     # cache settings before writing to config
        
        if denom is not None:
            line = k + ' (' + denom + '):\t\t'
        else:
            line = k + ':\t\t\t'
        
        if denom_enabled:
            line += 'X'
        else:
            line += '_'
            
        print(line)
    
    print("\n\nIf a denom is inhibited through these settings that's not inhibited by the\n"
          "appropriate DIP switch on the BV, the BV will go into INHIBIT status.")
    print("\nPress Enter to save and go back, or Esc to go back without saving")
    t.set_pos(25, 3)
    
    max_opt = len(CONFIG['bv.denom_inhibit']) - 1
    cur_opt = 0
    while True:
        x, y = t.get_pos()
        c = t.getch()
        
        if c == b'\xe0H' and cur_opt > 0:
            # up
            t.set_pos(x, y-1)
            cur_opt -= 1
        elif c == b'\xe0P' and cur_opt < max_opt:
            # down
            t.set_pos(x, y+1)
            cur_opt += 1
        elif c == b'\t' and cur_opt == max_opt:
            # wrap around to first option
            t.set_pos(x, 3)
            cur_opt = 0
        elif c == b'\t':
            # next option, same as down
            t.set_pos(x, y+1)
            cur_opt += 1
        elif c == b'X' or c == b'x':
            set_opts[opts[cur_opt]] = True
            print('X', end='')
            if cur_opt < max_opt:
                t.set_pos(x, y+1)
                cur_opt += 1
            else:
                t.set_pos(x, y)
        elif c == b' ':
            set_opts[opts[cur_opt]] = False
            print('_', end='')
            if cur_opt < max_opt:
                t.set_pos(x, y+1)
                cur_opt += 1
            else:
                t.set_pos(x, y)
        elif c == b'\r':
            # save and go back
            CONFIG['bv.denom_inhibit'] = set_opts
            return
        elif c == b'\x1b':
            # escape, go back without saving
            return
    
    
def main():
    global CONFIG
    
    comport = CONFIG['main']['comport']
    poll_interval = float(CONFIG['main']['poll_interval'])

    main_menu = OrderedDict()
    main_menu['r'] = "Run"
    main_menu['s'] = "Settings"
    main_menu['c'] = "Select COM port"
    main_menu['q'] = "Quit"
    
    choice = display_menu(main_menu, '>>>', "ID-003 protocol analyzer", "Using COM port %s" % comport)
    
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
        settings()
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