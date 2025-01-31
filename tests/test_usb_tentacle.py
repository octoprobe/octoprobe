import time

from octoprobe.usb_tentacle.usb_constants import UsbPlug, UsbPlugs
from octoprobe.usb_tentacle.usb_tentacle import UsbTentacles


def test_power_default_infra_on():
    usb_tentacles = UsbTentacles.query(require_serial=False)
    usb_tentacles.set_plugs(plugs=UsbPlugs.default_infra_on())


def test_power_default_off():
    usb_tentacles = UsbTentacles.query(require_serial=False)
    usb_tentacles.set_plugs(plugs=UsbPlugs.default_off())


def test_query_serial():
    usb_tentacles = UsbTentacles.query(require_serial=True)
    for usb_tentacle in usb_tentacles:
        print(repr(usb_tentacle))


def test_blib():
    """
    This test provoked:
      usb 3-1.1.4: reset high-speed USB device number 68 using xhci_hcd
      usb 3-1.1.4-port1: attempt power cycle"

    https://www.aliexpress.com/item/1005006892842715.html

    USB Cable --- USB --- USB --- USB 3-1.1.4-port1 --- USB 3-1.1.3-port1 --- USB

    lsusb -t -v
        /:  Bus 003.Port 001: Dev 001, Class=root_hub, Driver=xhci_hcd/12p, 480M
            ID 1d6b:0002 Linux Foundation 2.0 root hub
            |__ Port 001: Dev 116, If 0, Class=Hub, Driver=hub/4p, 480M
                ID 2148:7022
                |__ Port 001: Dev 117, If 0, Class=Hub, Driver=hub/4p, 480M
                    ID 2148:7022
                    |__ Port 003: Dev 118, If 0, Class=Hub, Driver=hub/4p, 480M
                        ID 0424:2514 Microchip Technology, Inc. (formerly SMSC) USB 2.0 Hub
                        |__ Port 001: Dev 071, If 0, Class=Mass Storage, Driver=usb-storage, 12M
                            ID 2e8a:0003
                        |__ Port 001: Dev 071, If 1, Class=Vendor Specific Class, Driver=[none], 12M
                            ID 2e8a:0003
                    |__ Port 004: Dev 077, If 0, Class=Hub, Driver=hub/4p, 480M
                        ID 0424:2514 Microchip Technology, Inc. (formerly SMSC) USB 2.0 Hub
                        |__ Port 001: Dev 078, If 0, Class=Communications, Driver=cdc_acm, 12M
                            ID 2e8a:0005
                        |__ Port 001: Dev 078, If 1, Class=CDC Data, Driver=cdc_acm, 12M
                            ID 2e8a:0005
    """
    usb_tentacles = UsbTentacles.query(require_serial=False)
    usb_tentacles.set_plugs(plugs=UsbPlugs.default_off())

    usb_tentacles.set_plugs(plugs=UsbPlugs.default_infra_on())


def test_blib2():
    """
    Same error provoked as above
    """
    usb_tentacles = UsbTentacles.query(require_serial=False)
    usb_tentacles.set_plugs(plugs=UsbPlugs.default_off())
    time.sleep(1.0)

    if True:
        # attempt power cycle
        usb_tentacles[0].set_plugs(plugs=UsbPlugs.default_infra_on())
        usb_tentacles[1].set_plugs(plugs=UsbPlugs.default_infra_on())

    if False:
        # attempt power cycle
        usb_tentacles[0].set_plugs(plugs=UsbPlugs({UsbPlug.INFRA: True}))
        usb_tentacles[1].set_plugs(plugs=UsbPlugs({UsbPlug.INFRA: True}))

    if False:
        # NO: attempt power cycle
        usb_tentacles[0].set_plugs(plugs=UsbPlugs({UsbPlug.ERROR: True}))
        usb_tentacles[1].set_plugs(plugs=UsbPlugs({UsbPlug.ERROR: True}))

    if False:
        # attempt power cycle - strange rythm
        usb_tentacles[0].set_plugs(plugs=UsbPlugs({UsbPlug.INFRA: True}))
        usb_tentacles[1].set_plugs(plugs=UsbPlugs({UsbPlug.ERROR: True}))
