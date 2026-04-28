Linux USB stability issues
===========================

Linux stability issues is a problem from testbed_micropython.

Up to ~6 tentacles work seemless.

The stability isssue have theses root causes

 * Hub

   * Power drops. This is solved in https://www.octoprobe.org/octohub4/big_picture.html.
   * Hubs too deeply cascaded. octohub4 allows to build a very flat structure.

 * USB protocol stack

   * USB CDC-ACM requires polling for a serial usb device every ~100ms.

     * Example: 16 tentacles with ~2 serial lines each: 32 polls every 100ms.

 * PCI USB host
 
   * The are different chipsets. See 30_usb_host.rst

Ubuntu tuning
-------------------

disable autosuspend
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add kernel boot parameter:

`usbcore.autosuspend=-1 pcie_aspm=off`


.. code-block:: bash

    sudoedit /etc/default/grub
    sudo update-grub
    sudo reboot


keep hubs and CP210x forced on with udev
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`/etc/udev/rules.d/82-octoprobe_cp210x.rules`

.. code-block:: text

    ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="0424", ATTR{idProduct}=="2514", TEST=="power/control", ATTR{power/control}="on"
    ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="10c4", ATTR{idProduct}=="ea60", TEST=="power/control", ATTR{power/control}="on"

.. code-block:: bash

    sudo udevadm control --reload
    sudo udevadm trigger
