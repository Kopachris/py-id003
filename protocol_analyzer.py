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

from collections import OrderedDict

X_SIZE, Y_SIZE = t.get_size()


def poll_loop(bv, interval):
    while True:
        poll_start = time.time()
        status, data = bv.req_status()
        if (status, data) != bv.bv_status:
            if status in bv.bv_events:
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
    main_menu = OrderedDict()
    main_menu['r'] = "Run"
    main_menu['s'] = "Settings"
    
    choice = display_menu(main_menu, '>>>', "ID-003 protocol analyzer", "Using COM port COM11").lower()
    
    if choice == 'r':
        import test
        test.main()
    elif choice == 's':
        t.wipe()
        print("Settings not available yet")
	
	
if __name__ == '__main__':
    main()