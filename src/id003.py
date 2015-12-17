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
SET_BAR_FUNC = 0xC6
SET_BAR_INHIBIT = 0xC7

## Setting status requests ##
GET_DENOM = 0x80
GET_SECURITY = 0x81
GET_INHIBIT = 0x83
GET_DIRECTION = 0x84
GET_OPT_FUNC = 0x85
GET_BAR_FUNC = 0x86
GET_BAR_INHIBIT = 0x87

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

NORM_STATUSES = tuple(range(0x11, 0x1C))

## Power up status ##
POW_UP = 0x40
POW_UP_BIA = 0x41  # Power up with bill in acceptor
POW_UP_BIS = 0x42  # Power up with bill in stacker
POW_STATUSES = 0x40, 0x41, 0x42

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

ERROR_STATUSES = tuple(range(0x43, 0x4C))


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
BARCODE_TKT = 0x6F

ESCROW_USA = {  # 2 and 8 are reserved
    DENOM_1: '$1',
    DENOM_3: '$5',
    DENOM_4: '$10',
    DENOM_5: '$20',
    DENOM_6: '$50',
    DENOM_7: '$100',
    BARCODE_TKT: 'TITO',
}

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

REJECT_REASONS = {
    INSERTION_ERR: "Insertion error",
    MAG_ERR: "Magnetic sensor error",
    REMAIN_ACC_ERR: "Remaining bills in head error",
    COMP_ERR: "Compensation error",
    CONVEYING_ERR: "Conveying error",
    DENOM_ERR: "Error assessing denomination",
    PHOTO_PTN1_ERR: "Photo pattern 1 error",
    PHOTO_LVL_ERR: "Photo level error",
    INHIBIT_ERR: "Inhibited",
    OPERATION_ERR: "Operation error",
    REMAIN_STACK_ERR: "Remaining bills in stacker error",
    LENGTH_ERR: "Length error",
    PHOTO_PTN2_ERR: "Photo pattern 2 error",
}

#REJECT_REASONS = tuple(range(0x71, 0x7F))


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


class DenomError(Exception):
    """Unknown denomination reported in escrow"""
    pass


def get_crc(message):
    """Get CRC value for a given bytes object using CRC-CCITT Kermit"""

    TABLE = [
      0x0000, 0x1189, 0x2312, 0x329B, 0x4624, 0x57AD, 0x6536, 0x74BF,
      0x8C48, 0x9DC1, 0xAF5A, 0xBED3, 0xCA6C, 0xDBE5, 0xE97E, 0xF8F7,
      0x1081, 0x0108, 0x3393, 0x221A, 0x56A5, 0x472C, 0x75B7, 0x643E,
      0x9CC9, 0x8D40, 0xBFDB, 0xAE52, 0xDAED, 0xCB64, 0xF9FF, 0xE876,
      0x2102, 0x308B, 0x0210, 0x1399, 0x6726, 0x76AF, 0x4434, 0x55BD,
      0xAD4A, 0xBCC3, 0x8E58, 0x9FD1, 0xEB6E, 0xFAE7, 0xC87C, 0xD9F5,
      0x3183, 0x200A, 0x1291, 0x0318, 0x77A7, 0x662E, 0x54B5, 0x453C,
      0xBDCB, 0xAC42, 0x9ED9, 0x8F50, 0xFBEF, 0xEA66, 0xD8FD, 0xC974,
      0x4204, 0x538D, 0x6116, 0x709F, 0x0420, 0x15A9, 0x2732, 0x36BB,
      0xCE4C, 0xDFC5, 0xED5E, 0xFCD7, 0x8868, 0x99E1, 0xAB7A, 0xBAF3,
      0x5285, 0x430C, 0x7197, 0x601E, 0x14A1, 0x0528, 0x37B3, 0x263A,
      0xDECD, 0xCF44, 0xFDDF, 0xEC56, 0x98E9, 0x8960, 0xBBFB, 0xAA72,
      0x6306, 0x728F, 0x4014, 0x519D, 0x2522, 0x34AB, 0x0630, 0x17B9,
      0xEF4E, 0xFEC7, 0xCC5C, 0xDDD5, 0xA96A, 0xB8E3, 0x8A78, 0x9BF1,
      0x7387, 0x620E, 0x5095, 0x411C, 0x35A3, 0x242A, 0x16B1, 0x0738,
      0xFFCF, 0xEE46, 0xDCDD, 0xCD54, 0xB9EB, 0xA862, 0x9AF9, 0x8B70,
      0x8408, 0x9581, 0xA71A, 0xB693, 0xC22C, 0xD3A5, 0xE13E, 0xF0B7,
      0x0840, 0x19C9, 0x2B52, 0x3ADB, 0x4E64, 0x5FED, 0x6D76, 0x7CFF,
      0x9489, 0x8500, 0xB79B, 0xA612, 0xD2AD, 0xC324, 0xF1BF, 0xE036,
      0x18C1, 0x0948, 0x3BD3, 0x2A5A, 0x5EE5, 0x4F6C, 0x7DF7, 0x6C7E,
      0xA50A, 0xB483, 0x8618, 0x9791, 0xE32E, 0xF2A7, 0xC03C, 0xD1B5,
      0x2942, 0x38CB, 0x0A50, 0x1BD9, 0x6F66, 0x7EEF, 0x4C74, 0x5DFD,
      0xB58B, 0xA402, 0x9699, 0x8710, 0xF3AF, 0xE226, 0xD0BD, 0xC134,
      0x39C3, 0x284A, 0x1AD1, 0x0B58, 0x7FE7, 0x6E6E, 0x5CF5, 0x4D7C,
      0xC60C, 0xD785, 0xE51E, 0xF497, 0x8028, 0x91A1, 0xA33A, 0xB2B3,
      0x4A44, 0x5BCD, 0x6956, 0x78DF, 0x0C60, 0x1DE9, 0x2F72, 0x3EFB,
      0xD68D, 0xC704, 0xF59F, 0xE416, 0x90A9, 0x8120, 0xB3BB, 0xA232,
      0x5AC5, 0x4B4C, 0x79D7, 0x685E, 0x1CE1, 0x0D68, 0x3FF3, 0x2E7A,
      0xE70E, 0xF687, 0xC41C, 0xD595, 0xA12A, 0xB0A3, 0x8238, 0x93B1,
      0x6B46, 0x7ACF, 0x4854, 0x59DD, 0x2D62, 0x3CEB, 0x0E70, 0x1FF9,
      0xF78F, 0xE606, 0xD49D, 0xC514, 0xB1AB, 0xA022, 0x92B9, 0x8330,
      0x7BC7, 0x6A4E, 0x58D5, 0x495C, 0x3DE3, 0x2C6A, 0x1EF1, 0x0F78
]

    crc = 0x0000
    for byte in message:
        crc = (crc >> 8) ^ TABLE[(crc ^ byte) & 0xff]
        
    # convert to bytes, big-endian
    crc = '%04x' % crc
    crc = [int(crc[-2:], 16), int(crc[:-2], 16)]

    return bytes(crc)


class BillVal(serial.Serial):
    """Represent an ID-003 bill validator as a subclass of `serial.Serial`"""
    
    def __init__(*args, **kwargs):
        serial.Serial.__init__(*args, **kwargs)
        
        self = args[0]
        
        self.bv_status = None
        self.bv_version = None
        if self.timeout is None:
            self.timeout = 1
            
        self.bv_events = {
            IDLE: self._on_idle,
            ACEPTING: self._on_accepting,
            ESCROW: self._on_escrow,
            STACKING: self._on_stacking,
            VEND_VALID: self._on_vend_valid,
            STACKED: self._on_stacked,
            REJECTING: self._on_rejecting,
            RETURNING: self._on_returning,
            HOLDING: self._on_holding,
            INHIBIT: self._on_inhibit,
            INITIALIZE: self._on_init,
        }
        
        # TODO get this from version during powerup
        self.bv_denoms = ESCROW_USA
    
    def _on_idle(self, data):
        print("BV idle.")
    
    def _on_accepting(self, data):
        print("BV accepting...")
    
    def _on_escrow(self, data):
        escrow = data[0]
        if escrow not in self.bv_denoms:
            raise DenomError("Unknown denom in escrow: %x" % escrow)
        elif escrow == BARCODE_TKT:
            barcode = data[1:]
            print("Barcode: %s" % barcode)
        else:
            print("Denom: %s" % self.bv_denoms[escrow])
            
        s_r = ''
        while s_r not in ('s', 'r'):
            s_r = input("(S)tack or (R)eturn? ").lower()
            if s_r == 's':
                print("Telling BV to stack...")
                self.accepting_denom = escrow
                status = None
                while status != ACK:
                    self.send_command(STACK_1, b'')
                    status, data = self.read_response()
                print("Received ACK")
                self.bv_status = None
                return None
            elif s_r == 'r':
                print("Telling BV to return...")
                status = None
                while status != ACK:
                    self.send_command(RETURN, b'')
                    status, data = self.read_response()
                print("Received ACK")
                self.bv_status = None
                return None
                    
    
    def _on_stacking(self, data):
        print("BV stacking...")
    
    def _on_vend_valid(self, data):
        print("Vend valid for %s." % self.accepting_denom)
        self.send_command(ACK, b'')
        self.accepting_denom = None
    
    def _on_stacked(self, data):
        print("Stacked.")

    def _on_rejecting(self, data):
        reason = ord(data)
        if reason in REJECT_REASONS:
            print("BV rejecting, reason: %s" % REJECT_REASONS[reason])
        else:
            print("BV rejecting, unknown reason: %02x" % reason)
    
    def _on_returning(self, data):
        print("BV Returning...")
    
    def _on_holding(self, data):
        pass
    
    def _on_inhibit(self, data):
        print("BV inhibited.")
        input("Press enter to reset and initialize BV.")
        status = None
        while status != ACK:
            self.send_command(RESET, b'')
            status, data = self.read_response()
        if self.req_status()[0] == INITIALIZE:
            self.initialize()
        self.bv_status = None
    
    def _on_init(self, data):
        pass
    
    def send_command(self, command, data=b''):
        """Send a generic command to the bill validator"""
        
        length = 5 + len(data)  # SYNC, length, command, and 16-bit CRC
        message = bytes([SYNC, length, command]) + data
        message += get_crc(message)
        
        return self.write(message)
        
    def read_response(self):
        """Parse data from the bill validator. Returns a tuple (command, data)"""
        
        start = None
        while start == None:
            start = self.read(1)
            if len(start) == 0:
                return (None, b'')
            elif start == b'\x00':
                return (0x00, b'')
            elif ord(start) != SYNC and start:
                raise SyncError("Wrong start byte, got %s" % start)
            
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
            #if status is not None:
                #print(status)
        
        self.init_status = status
            
        if status not in (POW_UP, POW_UP_BIA, POW_UP_BIS):
            raise PowerUpError("Acceptor already powered up")
        elif status == POW_UP:
            print("Powering up...\nGetting version...")
            self.send_command(GET_VERSION)
            status, self.bv_version = self.read_response()
            print(self.bv_version)
            
            while status != ACK:
                print("Sending reset command")
                self.send_command(RESET)
                status, data = self.read_response()
                
            if self.req_status()[0] == INITIALIZE:
                self.initialize()
        else:
            # Acceptor should either reject or stack bill
            while status != ACK:
                self.send_command(RESET)
                status, data = self.read_response()
                
            if self.req_status()[0] == INITIALIZE:
                self.initialize()
                    
        # typically call BillVal.poll() after this
        
        return self.init_status
            
    def initialize(self, denom=[0x82, 0], security=[0, 0], opt_func=[0, 0], 
                   inhibit=[0], bar_func=[0x01, 0x12], bar_inhibit=[0]):
        """Initialize BV settings"""
        
        denom = bytes(denom)
        self.send_command(SET_DENOM, denom)
        status, data = self.read_response()
        if (status, data) != (SET_DENOM, denom):
            raise AckError("Acceptor did not echo denom settings")
        
        security = bytes(security)
        self.send_command(SET_SECURITY, security)
        status, data = self.read_response()
        if (status, data) != (SET_SECURITY, security):
            raise AckError("Acceptor did not echo security settings")
            
        opt_func = bytes(opt_func)
        self.send_command(SET_OPT_FUNC, opt_func)
        status, data = self.read_response()
        if (status, data) != (SET_OPT_FUNC, opt_func):
            raise AckError("Acceptor did not echo option function settings")
            
        inhibit = bytes(inhibit)
        self.send_command(SET_INHIBIT, inhibit)
        status, data = self.read_response()
        if (status, data) != (SET_INHIBIT, inhibit):
            raise AckError("Acceptor did not echo inhibit settings")
        
        bar_func = bytes(bar_func)
        self.send_command(SET_BAR_FUNC, bar_func)
        status, data = self.read_response()
        if (status, data) != (SET_BAR_FUNC, bar_func):
            raise AckError("Acceptor did not echo barcode settings")

        bar_inhibit = bytes(bar_inhibit)
        self.send_command(SET_BAR_INHIBIT, bar_inhibit)
        status, data = self.read_response()
        if (status, data) != (SET_BAR_INHIBIT, bar_inhibit):
            raise AckError("Acceptor did not echo barcode inhibit settings")
    
    def req_status(self):
        """Send status request to bill validator"""
        
        if self.in_waiting:
            # discard any unused data
            self.reset_input_buffer()
            
        self.send_command(STATUS_REQ)
        
        stat, data = self.read_response()
        #if (stat, data) != self.bv_status and self.bv_status is not None:
            #print((hex(stat), data))

        #self.bv_status = (stat, data)
        return stat, data
        
    def poll(self, interval=0.2):
        """Send a status request to the bill validator every `interval` seconds
        and fire event handlers. `interval` defaults to 200 ms, per ID-003 spec.
        
        Event handlers are only fired upon status changes.
        """
        
        while True:
            poll_start = time.time()
            status, data = self.req_status()
            if (status, data) != self.bv_status:
                #print((hex(status), data))
                if status in self.bv_events:
                    self.bv_events[status](data)
            self.bv_status = (status, data)
            wait = interval - (time.time() - poll_start)
            if wait > 0.0:
                time.sleep(wait)
            
        