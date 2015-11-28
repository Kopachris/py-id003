#!/usr/bin/env python3

import serial
import time


###
### Constants
###


### General ###
ACK = 0x50
SYNC = 0xFC

## Setting commands ##
SET_DENOM = 0xC0
SET_SECURITY = 0xC1
SET_INHIBIT = 0xC3
SET_DIRECTION = 0xC4
SET_OPT_FUNC = 0xC5

## Setting status requests ##
GET_DENOM = 0x80
GET_SECURITY = 0x81
GET_INHIBIT = 0x83
GET_DIRECTION = 0x84
GET_OPT_FUNC = 0x85

GET_VERSION = 0x88
GET_BOOT_VERSION = 0x89


### Controller -> Acceptor ###
STATUS_REQ = 0x11

## Operation commands ##
RESET = 0x40
STACK_1 = 0x41
STACK_2 = 0x42
RETURN = 0x43
HOLD = 0x44
WAIT = 0x45


### Acceptor -> Controller ###

## Status ##
ENABLE = 0x11
IDLE = 0x11  # Alias for ENABLE
ACEPTING = 0x12
ESCROW = 0x13
STACKING = 0x14
VEND_VALID = 0x15
STACKED = 0x16
REJECTING = 0x17
RETURNING = 0x18
HOLDING = 0x19
DISABLE = 0x1A
INHIBIT = 0x1A  # Alias for DISABLE
INITIALIZE = 0x1B

## Power up status ##
POW_UP = 0x40
POW_UP_BIA = 0x41  # Power up with bill in acceptor
POW_UP_BIS = 0x42  # Power up with bill in stacker

## Error status ##
STACKER_FULL = 0x43
STACKER_OPEN = 0x44
ACCEPTOR_JAM = 0x45
STACKER_JAM = 0x46
PAUSE = 0x47
CHEATED = 0x48
FAILURE = 0x49
COMM_ERROR = 0x4A
INVALID_COMMAND = 0x4B


### Data constants ###

## Escrow ##
DENOM_1 = 0x61
DENOM_2 = 0x62
DENOM_3 = 0x63
DENOM_4 = 0x64
DENOM_5 = 0x65
DENOM_6 = 0x66
DENOM_7 = 0x67
DENOM_8 = 0x68

## Reject reasons ##
INSERTION_ERR = 0x71
MAG_ERR = 0x72
REMAIN_ACC_ERR = 0x73
COMP_ERR = 0X74
CONVEYING_ERR = 0x75
DENOM_ERR = 0x76
PHOTO_PTN1_ERR = 0x77
PHOTO_LVL_ERR = 0x78
INHIBIT_ERR = 0x79
OPERATION_ERR = 0x7B
REMAIN_STACK_ERR = 0x7C
LENGTH_ERR = 0x7D
PHOTO_PTN2_ERR = 0x7E


class CRCError(Exception):
    """Computed CRC does not match given CRC"""
    pass


class SyncError(Exception):
    """Tried to read a message, but got wrong start byte"""
    pass


class PowerUpError(Exception):
    """Expected power up, but received wrong status"""
    pass


class AckError(Exception):
    """Acceptor did not acknowledge as expected"""
    pass


def get_crc(message):
    """Get CRC value for a given bytes object"""
    
    poly = 0x1021
    #16bit operation register, initialized to zeros
    reg = 0xFFFF
    #pad the end of the message with the size of the poly
    message += b'\x00\x00' 
    #for each bit in the message
    for byte in message:
        mask = 0x80
        while(mask > 0):
            #left shift by one
            reg<<=1
            #input the next bit from the message into the right hand side of the op reg
            if byte & mask:   
                reg += 1
            mask>>=1
            #if a one popped out the left of the reg, xor reg w/poly
            if reg > 0xffff:            
                #eliminate any one that popped out the left
                reg &= 0xffff           
                #xor with the poly, this is the remainder
                reg ^= poly
    return reg


class BillVal(serial.Serial):
    """Represent an ID-003 bill validator as a subclass of `serial.Serial`"""
    
    def __init__(*args, **kwargs):
        serial.Serial.__init__(*args, **kwargs)
        if args[0].timeout is None:
            args[0].timeout = 1
    
    def send_command(self, command, data=b''):
        """Send a generic command to the bill validator"""
        
        length = 5 + len(data)  # SYNC, length, command, and 16-bit CRC
        message = bytes([SYNC, length, command]) + data
        crc = hex(get_crc(message)).split('x')[1]
        crc = [int(crc[:-2], 16), int(crc[-2:], 16)]
        message += bytes(crc)
        return self.write(message)
        
    def read_response(self):
        """Parse data from the bill validator. Returns a tuple (command, data)"""
        
        start = None
        while start == None:
            start = self.read(1)
            if len(start) == 0:
                return (None, b'')
            elif ord(start) != SYNC:
                return (0x00, b'') 
                #raise SyncError("Wrong start byte, got %s" % start)
            
        total_length = self.read()
        data_length = ord(total_length) - 5
        
        command = self.read()
        
        if data_length:
            data = self.read(data_length)
        else:
            data = b''
            
        crc = self.read(2)
        
        # check all our data...
        full_msg = start + total_length + command + data
        if get_crc(full_msg) != crc:
            raise CRCError("CRC mismatch")
            
        return ord(command), data
        
    def power_on(self):
        """Handle startup routines"""
        
        status = None
        while status is None or status == 0x00:
            status, data = self.req_status()
        
        self.init_status = status
            
        if status not in (POW_UP, POW_UP_BIA, POW_UP_BIS):
            raise PowerUpError("Acceptor already powered up")
        elif status == POW_UP:
            self.send_command(GET_VERSION)
            status, self.bv_version = self.read_response()
            
            while status != ACK:
                self.send_command(RESET)
                status, data = self.read_response()
                
            if self.req_status()[0] == INITIALIZE:
                self.send_command(SET_DENOM, b'\x00')
                if self.read_response() != (SET_DENOM, b'\x00'):
                    raise AckError("Acceptor did not echo denom settings")
                
                self.send_command(SET_SECURITY, b'\x00')
                if self.read_response() != (SET_SECURITY, b'\x00'):
                    raise AckError("Acceptor did not echo security settings")
                    
                self.send_command(SET_OPT_FUNC, b'\x00')
                if self.read_response() != (SET_OPT_FUNC, b'\x00'):
                    raise AckError("Acceptor did not echo option function settings")
                    
                self.send_command(SET_INHIBIT, b'\x00')
                if self.read_response() != (SET_IHIBIT, b'\x00'):
                    raise AckError("Acceptor did not echo inhibit settings")
        else:
            # Acceptor should either reject or stack bill
            while status != ACK:
                self.send_command(RESET)
                status, data = self.read_response()
                    
        while status != ENABLE:
            status, data = self.req_status()
            time.sleep(0.1)
            
    def req_status(self):
        """Send status request to bill validator"""

        print("Requesting status...")
        
        if self.in_waiting:
            # discard any unused data
            self.reset_input_buffer()
            
        self.send_command(STATUS_REQ)
        
        stat, data = self.read_response()
        print((stat, data))
        return stat, data
        