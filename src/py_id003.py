#!/usr/bin/env python3

import serial


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
GET_OT_FUNC = 0x85

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


class BillVal(serial.Serial):
    """Represent an ID-003 bill validator as a subclass of `serial.Serial`"""
    pass