# SPDX-FileCopyrightText: 2024 Red Wire Technologies <support@redwiretechnologies.us>

# SPDX-License-Identifier: MIT

import gpiod
import logging
from .gpio_line_mux import *
from .iio_gpo_control import *
from .constants import *

class cardf:
    """
    A class for controlling the CARDF backpack

    **Expected declaration:**

        my_cardf = pc_card_control.cardf(0, 2, reset=0)
    """

    def __init__(self, gpiochip_num, control_rxtx=1, reset=1):
        """
        Initialize a CARDF

        Args:
            gpiochip_num (int): Number of the gpiochip that is created when
                                the CARDF DTS is loaded (this can be found
                                via gpioinfo in the terminal)

            control_rxtx (int): Should this control the transceiver's RX/TX
                                lines (Default: 1)

            reset (int): Should the reset() function be called at the end
                         of initialization (Default:1)
        """

        #Setup logger
        self.log = logging.getLogger("cardf")

        #Debug log to express initialization parameters
        self.log.debug("CARDF init")
        self.log.debug("Using base GPIOCHIP{}".format(BASE_GPIO_CHIP))
        self.log.debug("Using secondary GPIOCHIP{}".format(gpiochip_num))
        if control_rxtx:
            self.log.debug("Set to control RX/TX")

        self.gpiochip0 = gpiod.Chip('gpiochip{}'.format(BASE_GPIO_CHIP))
        self.gpiochip  = gpiod.Chip("gpiochip{}".format(gpiochip_num))

        self.tx_enable = [None] * 2
        self.tx_enable[0] = self.gpiochip0.get_lines([78])
        self.tx_enable[1] = self.gpiochip0.get_lines([79])

        #These lines are for controlling the RX/TX on the transceivers
        self.rx = [None] * 2
        self.tx = [None] * 2
        if control_rxtx:
            self.rx[0] = self.gpiochip0.get_lines([132])
            self.rx[1] = self.gpiochip0.get_lines([135])
            self.tx[0] = self.gpiochip0.get_lines([133])
            self.tx[1] = self.gpiochip0.get_lines([136])
        else:
            self.rx = None
            self.tx = None

        self.rx_bpf  = [None]*2
        self.tx_filt = []
        for i in range(0, 2):
            self.tx_filt.append([None, None, None])

        self.lna_enable = [None]*4

        self.pa_enable = [None]*2

        self.bt_enable = [None]*2
        self.wifi_enable = [None]*2

        self.rx_bpf[0] = self.gpiochip.get_lines([12])
        self.rx_bpf[1] = self.gpiochip.get_lines([10])

        self.tx_filt[0][0] = self.gpiochip0.get_lines([82])
        self.tx_filt[0][1] = self.gpiochip0.get_lines([83])
        self.tx_filt[0][2] = self.gpiochip0.get_lines([84])
        self.tx_filt[1][0] = self.gpiochip0.get_lines([85])
        self.tx_filt[1][1] = self.gpiochip0.get_lines([86])
        self.tx_filt[1][2] = self.gpiochip0.get_lines([44])

        self.lna_enable[0] = self.gpiochip.get_lines([0])
        self.lna_enable[1] = self.gpiochip.get_lines([1])
        self.lna_enable[2] = self.gpiochip.get_lines([2])
        self.lna_enable[3] = self.gpiochip.get_lines([3])

        self.pa_enable[0] = self.gpiochip.get_lines([8])
        self.pa_enable[1] = self.gpiochip.get_lines([9])

        self.bt_enable[0] = self.gpiochip.get_lines([4])
        self.bt_enable[1] = self.gpiochip.get_lines([6])

        self.wifi_enable[0] = self.gpiochip.get_lines([5])
        self.wifi_enable[1] = self.gpiochip.get_lines([7])


        self.tx_inhib = self.gpiochip.get_lines([11])

        self.tx_inhib.request(consumer='CARDF_TX_INHIB', type=gpiod.LINE_REQ_DIR_OUT)

        if control_rxtx:
            for i in self.rx:
                i.request(consumer='CARDF_RX_CTRL', type=gpiod.LINE_REQ_DIR_OUT)
            for i in self.tx:
                i.request(consumer='CARDF_TX_CTRL', type=gpiod.LINE_REQ_DIR_OUT)

        for i in self.rx_bpf:
            i.request(consumer='CARDF_RX_BPF', type=gpiod.LINE_REQ_DIR_OUT)
        for j, i in enumerate(self.tx_filt):
            for k in i:
                k.request(consumer='CARDF_TX_FILT_{}'.format(j), type=gpiod.LINE_REQ_DIR_OUT)
        for i in self.lna_enable:
            i.request(consumer='CARDF_LNA_CTRL', type=gpiod.LINE_REQ_DIR_OUT)
        for i in self.pa_enable:
            i.request(consumer='CARDF_PA_CTRL', type=gpiod.LINE_REQ_DIR_OUT)
        for i in self.bt_enable:
            i.request(consumer='CARDF_BT_CTRL', type=gpiod.LINE_REQ_DIR_OUT)
        for i in self.wifi_enable:
            i.request(consumer='CARDF_WIFI_CTRL', type=gpiod.LINE_REQ_DIR_OUT)
        for i in self.tx_enable:
            i.request(consumer='CARDF_TX_EN', type=gpiod.LINE_REQ_DIR_OUT)

        if reset:
            self.reset()

    def reset(self):
        """
        Base reset for the board. Disables filtering, disables PAs/LNAs
        """
        self.configure_rx_unfiltered()
        self.configure_tx_unfiltered()
        self.disable_pa()
        self.disable_lnas()

    def enable_bt(self):
        """Enable Bluetooth"""
        self.log.info("Enabling Bluetooth")
        for gpio in self.bt_enable:
            gpio.set_values([1])

    def disable_bt(self):
        """Disable Bluetooth"""
        self.log.info("Disabling Bluetooth")
        for gpio in self.bt_enable:
            gpio.set_values([0])

    def enable_wifi(self):
        """Enable WiFi"""
        self.log.info("Enabling WiFi")
        for gpio in self.wifi_enable:
            gpio.set_values([1])

    def disable_wifi(self):
        """Disable WiFi"""
        self.log.info("Disabling WiFi")
        for gpio in self.wifi_enable:
            gpio.set_values([0])

    def enable_lnas(self):
        """Enables the LNAs. Also disables the PAs"""
        self.log.info("Enabling LNAs")
        self.disable_pa()
        for gpio in self.lna_enable:
            gpio.set_values([1])

    def disable_lnas(self):
        """Disables the LNAs"""
        for gpio in self.lna_enable:
            gpio.set_values([0])

    def configure_rx_filters(self, freq):
        """
        Configure the RX filters for the requested frequency

        Args:
            freq (int): Desired frequency to set.
        """

        freqs = [([ 902000000,  928000000], [0, 1]),
                 ([2400000000, 2500000000], [1, 0]),
                 ([5000000000, 6000000000], [1, 1]),
                 ([         0, 9999999999], [0, 0])]

        freq_names = ["900MHz", "2.4GHz", "5GHz", "UNFILTERED"]
        for i, k in enumerate(freqs):
            if freq >= k[0][0] and freq <= k[0][1]:
                for gpio, val in zip(self.rx_bpf, k[1]):
                    gpio.set_values([val])
                self.log.info("Set BPF to {}".format(freq_names[i]))
                return

    def configure_rx_unfiltered(self):
        """Configure the RX filters to the unfiltered setting"""
        self.configure_rx_filters(1)

    def configure_receive(self):
        """
        Disable the PAs. If control_rxtx set, turn off TX and enable RX.
        """
        self.log.info("Configure Receive")
        self.disable_pa()
        if self.tx:
            for gpio in self.tx:
                gpio.set_values([0])
        if self.rx:
            for gpio in self.rx:
                gpio.set_values([1])

    def configure_transmit(self):
        """
        Disable the LNAs. If control_rxtx set, turn off RX and enable TX.
        """
        self.log.info("Configure Transmit")
        self.disable_lnas()
        if self.rx:
            for gpio in self.rx:
                gpio.set_values([0])
        if self.tx:
            for gpio in self.tx:
                gpio.set_values([1])

    def enable_pa(self):
        """
        Enable the PAs. Disable the LNAs
        """
        self.log.info("Enabling PAs")
        self.disable_lnas()
        for gpio in self.pa_enable:
            gpio.set_values([1])
        for gpio in self.tx_enable:
            gpio.set_values([1])
        self.tx_inhib.set_values([0])

    def disable_pa(self):
        """
        Disable the PAs.
        """
        self.log.info("Disabling PAs")
        self.tx_inhib.set_values([1])
        for gpio in self.tx_enable:
            gpio.set_values([0])
        for gpio in self.pa_enable:
            gpio.set_values([0])

    def configure_tx_filters(self, freq, tx_path=-1):
        """
        Configure the TX filters for the requested frequency

        Args:
            freq (int): Desired frequency to set.

            tx_path (int): Desired TX path to set the filters for ([0-1] or
                           -1 for both)
        """
        freqs = {  230000000: [1, 0, 1],
                   560000000: [0, 1, 1],
                  1300000000: [1, 1, 0],
                  3125000000: [0, 1, 0],
                  9999999999: [0, 0, 1]} #UNFILTERED

        for k, v in freqs.items():
            if freq <= k:
                if rx_path == -1 or rx_path == 0:
                    self.log.info("Configuring TX filters for {} on TX 0".format(k))
                    for gpio, val in zip(self.tx_filt[0], v):
                        gpio.set_values([val])
                if rx_path == -1 or rx_path == 1:
                    self.log.info("Configuring TX filters for {} on TX 1".format(k))
                    for gpio, val in zip(self.tx_filt[1], v):
                        gpio.set_values([val])
                return

    def configure_tx_unfiltered(self, tx_path=-1):
        """
        Configure the TX filters to the unfiltered setting

        Args:
            tx_path (int): Desired TX path to set the filters for ([0-1] or
                           -1 for both)
        """
        self.configure_tx_filters(4000000000, tx_path)
