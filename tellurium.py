# SPDX-FileCopyrightText: 2024 Red Wire Technologies <support@redwiretechnologies.us>

# SPDX-License-Identifier: MIT

import gpiod
import logging
from .gpio_line_mux import *
from .iio_gpo_control import *
from .constants import *

class tellurium:

    """
    A class for controlling the Tellurium personality card

    **Expected declaration:**

        my_tellurium = pc_card_control.tellurium(0, 2, 0)
    """
    def __init__(self, pc_slot, gpiochip_num, transceiver_num, carp=0, control_rxtx=1, reset=1):
        """
        Initialize a Tellurium board

        Args:
            pc_slot (int): Personality card slot number ([0-4]). If not on
                           CARP, use 0

            gpiochip_num (int): Number of the gpiochip that is created when
                                the Tellurium DTS is loaded (this can be
                                found via gpioinfo in the terminal)

            transceiver_num (int): The number of which transceiver this is
                                   connected to.

            carp (int): Is this on a CARP (Default: 0)

            control_rxtx (int): Should this control the transceiver's RX/TX
                                lines (Default: 1)

            reset (int): Should the reset() function be called at the end
                         of initialization (Default:1)
        """

        #Setup logger
        self.log = logging.getLogger("tellurium_{}".format(pc_slot))

        #Debug log to express initialization parameters
        self.log.debug("Tellurium init")
        self.log.debug("Using base GPIOCHIP{}".format(BASE_GPIO_CHIP))
        self.log.debug("Using secondary GPIOCHIP{}".format(gpiochip_num))
        if carp:
            self.log.debug("Using CARP GPIOCHIP{}".format(CARP_GPIO_CHIP))
        self.log.debug("Using Personality Card slot {}".format(pc_slot))
        self.log.debug("Using Transceiver {}".format(transceiver_num))
        if control_rxtx:
            self.log.debug("Set to control RX/TX")

        self.gpiochip0 = gpiod.Chip('gpiochip{}'.format(BASE_GPIO_CHIP))
        if carp:
            self.gpiochip2 = gpiod.Chip('gpiochip{}'.format(CARP_GPIO_CHIP))
            self.line_mux  = gpio_line_mux()
        else:
            self.gpo_ctrl = iio_gpo_control()
        self.gpiochip  = gpiod.Chip("gpiochip{}".format(gpiochip_num))

        if carp:
            match pc_slot:
                case 0:
                    self.tx_enable = self.line_mux.get_lines([CARP_GPO_IN.RFP_0_ADGPO_2.value])
                case 1:
                    self.tx_enable = self.line_mux.get_lines([CARP_GPO_IN.RFP_1_ADGPO_2.value])
                case 2:
                    self.tx_enable = self.line_mux.get_lines([CARP_GPO_IN.RFP_2_ADGPO_2.value])
                case 3:
                    self.tx_enable = self.line_mux.get_lines([CARP_GPO_IN.RFP_3_ADGPO_2.value])
        else:
            self.tx_enable = self.gpo_ctrl.get_lines([AD9361_GPO.ADGPO_2.value])

        #These lines are for controlling the RX/TX on the transceivers
        if control_rxtx:
            if carp:
                self.rx = self.gpiochip0.get_lines([132+transceiver_num*3])
                self.tx = self.gpiochip0.get_lines([133+transceiver_num*3])
            else:
                self.rx = self.gpiochip0.get_lines([125])
                self.tx = self.gpiochip0.get_lines([126])
        else:
            self.rx = None
            self.tx = None

        self.rx_lpf  = [None]*3
        self.rx_hpf  = [None]*3
        self.pa      = [None]*2
        self.tx_filt = [None]*3

        # The first four of these lines live on an I2C expander on CARP
        # The position of the GPIOs on the expander are relative to the
        # slot number
        if carp:
            self.rx_lpf[0] = self.gpiochip2.get_lines([6*pc_slot+1])
            self.rx_lpf[1] = self.gpiochip2.get_lines([6*pc_slot+2])
            self.rx_lpf[2] = self.gpiochip2.get_lines([6*pc_slot+3])
            self.rx_hpf[0] = self.gpiochip2.get_lines([6*pc_slot+4])
            self.rx_hpf[1] = self.gpiochip2.get_lines([6*pc_slot+5])
        else:
            self.rx_lpf[0] = self.gpiochip0.get_lines([95])
            self.rx_lpf[1] = self.gpiochip0.get_lines([96])
            self.rx_lpf[2] = self.gpiochip0.get_lines([97])
            self.rx_hpf[0] = self.gpiochip0.get_lines([98])
            self.rx_hpf[1] = self.gpiochip0.get_lines([99])

        # The rest of the lines live on an I2C expander on the Tellurium
        self.rx_hpf[2] = self.gpiochip.get_lines([0])
        self.pa[0] = self.gpiochip.get_lines([1])
        self.pa[1] = self.gpiochip.get_lines([2])
        self.tx_filt[0] = self.gpiochip.get_lines([3])
        self.tx_filt[1] = self.gpiochip.get_lines([4])
        self.tx_filt[2] = self.gpiochip.get_lines([5])

        self.pa_enable = self.gpiochip.get_lines([7])

        self.pa_enable.request(consumer='TELLURIUM_PA_ENABLE', type=gpiod.LINE_REQ_DIR_OUT)
        if control_rxtx:
            self.rx.request(consumer='TELLURIUM_RX_CTRL', type=gpiod.LINE_REQ_DIR_OUT)
            self.tx.request(consumer='TELLURIUM_TX_CTRL', type=gpiod.LINE_REQ_DIR_OUT)

        for i in self.rx_lpf:
            i.request(consumer='TELLURIUM_LPF', type=gpiod.LINE_REQ_DIR_OUT)
        for i in self.rx_hpf:
            i.request(consumer='TELLURIUM_HPF', type=gpiod.LINE_REQ_DIR_OUT)
        for i in self.pa:
            i.request(consumer='TELLURIUM_PA', type=gpiod.LINE_REQ_DIR_OUT)
        for i in self.tx_filt:
            i.request(consumer='TELLURIUM_TX_FILT', type=gpiod.LINE_REQ_DIR_OUT)

        if reset:
            self.reset()

    def reset(self):
        """
        Base reset for the board. Disables RX/TX filtering, sets to not use
        PAs, disables PAs/, and configures the board for receive
        """
        self.configure_rx_unfiltered()
        self.configure_tx_unfiltered()
        self.configure_pa(0)
        self.disable_pa()

    def configure_rx_lpf(self, freq):
        """
        Configure the Low-pass Filters (LPF) for the requested frequency

        Args:
            freq (int): Desired frequency to set.
        """
        freqs = {  145000000: [0, 1, 0],
                   440000000: [0, 1, 1],
                  1370000000: [1, 0, 1],
                  3000000000: [1, 1, 0],
                  9999999999: [0, 0, 1]} #UNFILTERED

        for k, v in freqs.items():
            if freq <= k:
                for gpio, val in zip(self.rx_lpf, v):
                    gpio.set_values([val])
                self.log.info("Set RX LPF to {}".format(k))
                return

    def configure_rx_hpf(self, freq):
        """
        Configure the High-pass Filters (HPF) for the requested frequency

        Args:
            freq (int): Desired frequency to set.
        """
        freqs = { 3780000000: [1, 1, 0],
                  1930000000: [1, 0, 1],
                   840000000: [0, 1, 1],
                   135000000: [0, 1, 0],
                           0: [0, 0, 1]} #UNFILTERED

        for k, v in freqs.items():
            if freq >= k:
                for gpio, val in zip(self.rx_hpf, v):
                    gpio.set_values([val])
                self.log.info("Set RX HPF to {}".format(k))
                return

    def configure_rx_filters(self, freq):
        """
        Configure the LPF and HPF for the requested frequency

        Args:
            freq (int): Desired frequency to set.
        """
        self.configure_rx_lpf(freq)
        self.configure_rx_hpf(freq)

    def configure_rx_unfiltered(self):
        """Configure the RX filters to the unfiltered setting"""
        self.configure_rx_lpf(4000000000)
        self.configure_rx_hpf(100000000)

    def configure_pa(self, power_level):
        """
        Configure the PA

        Args:
            power_level (int): Set power level (0-2).
                               No PA    = 0
                               100mw PA = 1
                               1W PA    = 2
        """
        power = [[0, 0],
                 [1, 0],
                 [1, 1]]

        if power_level not in range(0, 3):
            self.log.warning("Power level must be 0-2")
            return

        for gpio, val in zip(self.pa, power[power_level]):
            gpio.set_values([val])
        self.log.info("Power level set to {}".format(power_level))

    def enable_pa(self):
        """
        Enable the PAs. Disable the LNAs
        """
        self.log.info("Enabling PAs")
        self.pa_enable.set_values([1])
        self.tx_enable.set_values([1])

    def disable_pa(self):
        """
        Disable the PAs.
        """
        self.log.info("Disabling PAs")
        self.tx_enable.set_values([0])
        self.pa_enable.set_values([0])

    def configure_receive(self):
        """
        Disable the PAs. If control_rxtx set, turn off TX and enable RX.
        """
        self.log.info("Configure Receive")
        self.disable_pa()
        if self.tx:
            self.tx.set_values([0])
        if self.rx:
            self.rx.set_values([1])

    def configure_transmit(self):
        """
        Disable the LNAs.
        """
        self.log.info("Configure Transmit")
        if self.rx:
            self.rx.set_values([0])
        if self.tx:
            self.tx.set_values([1])

    def configure_tx_filters(self, freq):
        """
        Configure the TX filters for the requested frequency

        Args:
            freq (int): Desired frequency to set.
        """
        freqs = {  230000000: [1, 0, 1],
                   560000000: [0, 1, 1],
                  1300000000: [1, 1, 0],
                  3125000000: [0, 1, 0],
                  9999999999: [0, 0, 1]} #UNFILTERED

        for k, v in freqs.items():
            if freq <= k:
                self.log.info("Configuring TX filters for {}".format(k))
                for gpio, val in zip(self.tx_filt, v):
                    gpio.set_values([val])
                return

    def configure_tx_unfiltered(self):
        """Configure the TX filters to the unfiltered setting"""
        self.configure_tx_filters(4000000000)
