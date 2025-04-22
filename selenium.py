# SPDX-FileCopyrightText: 2024 Red Wire Technologies <support@redwiretechnologies.us>
#
# SPDX-License-Identifier: MIT

import gpiod
import logging
from .constants import *

class selenium:
    """
    A class for controlling the Selenium personality card

    **Expected declaration:**

        my_selenium = pc_card_control.selenium(0, 2)
    """

    def __init__(self, pc_slot, gpiochip_num, carp=0, reset=1):
        """
        Initialize a Selenium board

        Args:
            pc_slot (int): Personality card slot number ([0-4]). If not on
                           CARP, use 0

            gpiochip_num (int): Number of the gpiochip that is created when
                                the Selenium DTS is loaded (this can be
                                found via gpioinfo in the terminal)

            carp (int): Is this on a CARP (Default: 0)

            reset (int): Should the reset() function be called at the end
                         of initialization (Default:1)
        """

        #Setup logger
        self.log = logging.getLogger("selenium_{}".format(pc_slot))

        #Debug log to express initialization parameters
        self.log.debug("Selenium init")
        self.log.debug("Using base GPIOCHIP{}".format(BASE_GPIO_CHIP))
        self.log.debug("Using secondary GPIOCHIP{}".format(gpiochip_num))
        if carp:
            self.log.debug("Using CARP GPIOCHIP{}".format(CARP_GPIO_CHIP))
        self.log.debug("Using Personality Card slot {}".format(pc_slot))

        if carp:
            self.gpiochip2 = gpiod.Chip('gpiochip{}'.format(CARP_GPIO_CHIP))
        else:
            self.gpiochip0 = gpiod.Chip('gpiochip{}'.format(BASE_GPIO_CHIP))
        self.gpiochip  = gpiod.Chip("gpiochip{}".format(gpiochip_num))

        self.lpf = [[None]*3, [None]*3]
        self.hpf = [[None]*3, [None]*3]

        # The first four of these lines live on an I2C expander on CARP
        # The position of the GPIOs on the expander are relative to the
        # slot number
        if carp:
            self.lpf[0][0] = self.gpiochip2.get_lines([6*pc_slot+1])
            self.lpf[0][1] = self.gpiochip2.get_lines([6*pc_slot+2])
            self.lpf[0][2] = self.gpiochip2.get_lines([6*pc_slot+3])
            self.hpf[0][0] = self.gpiochip2.get_lines([6*pc_slot+4])
        else:
            self.lpf[0][0] = self.gpiochip0.get_lines([95])
            self.lpf[0][1] = self.gpiochip0.get_lines([96])
            self.lpf[0][2] = self.gpiochip0.get_lines([97])
            self.hpf[0][0] = self.gpiochip0.get_lines([98])

        # The rest of the lines live on an I2C expander on the Selenium
        self.hpf[0][1] = self.gpiochip.get_lines([0])
        self.hpf[0][2] = self.gpiochip.get_lines([1])
        self.lpf[1][0] = self.gpiochip.get_lines([2])
        self.lpf[1][1] = self.gpiochip.get_lines([3])
        self.lpf[1][2] = self.gpiochip.get_lines([4])
        self.hpf[1][0] = self.gpiochip.get_lines([5])
        self.hpf[1][1] = self.gpiochip.get_lines([6])
        self.hpf[1][2] = self.gpiochip.get_lines([7])

        for i in self.lpf:
            for j in i:
                j.request(consumer='SELENIUM_LPF', type=gpiod.LINE_REQ_DIR_OUT)
        for i in self.hpf:
            for j in i:
                j.request(consumer='SELENIUM_HPF', type=gpiod.LINE_REQ_DIR_OUT)

        if reset:
            self.reset()

    def reset(self):
        """ Base reset for the board. Configure for unfiltered """
        self.configure_unfiltered()

    def configure_lpf(self, freq, rx_path=-1):
        """
        Configure the Low-pass Filter (LPF)

        Args:
            freq (int): Desired frequency

            rx_path (int): Index of RF path to set LPF for ([0-1] or -1 for
                           both). (Default: -1)
        """
        freqs = {  145000000: [0, 1, 0],
                   440000000: [0, 1, 1],
                  1370000000: [1, 0, 1],
                  3000000000: [1, 1, 0],
                  9999999999: [0, 0, 1]} #UNFILTERED

        for k, v in freqs.items():
            if freq <= k:

                if rx_path == -1 or rx_path == 0:
                    self.log.info("Set LPF to {} for rx_path 0".format(k))
                    for gpio, val in zip(self.lpf[0], v):
                        gpio.set_values([val])
                if rx_path == -1 or rx_path == 1:
                    self.log.info("Set LPF to {} for rx_path 1".format(k))
                    for gpio, val in zip(self.lpf[1], v):
                        gpio.set_values([val])
                return

    def configure_hpf(self, freq, rx_path=-1):
        """
        Configure the High-pass Filter (HPF)

        Args:
            freq (int): Desired frequency

            rx_path (int): Index of RF path to set HPF for ([0-1] or -1 for
                           both). (Default: -1)
        """
        freqs = { 3780000000: [1, 1, 0],
                  1930000000: [1, 0, 1],
                   840000000: [0, 1, 1],
                   135000000: [0, 1, 0],
                           0: [0, 0, 1]} #UNFILTERED

        for k, v in freqs.items():
            if freq >= k:
                if rx_path == -1 or rx_path == 0:
                    self.log.info("Set HPF to {} for rx_path 0".format(k))
                    for gpio, val in zip(self.hpf[0], v):
                        gpio.set_values([val])
                if rx_path == -1 or rx_path == 1:
                    self.log.info("Set HPF to {} for rx_path 1".format(k))
                    for gpio, val in zip(self.hpf[1], v):
                        gpio.set_values([val])
                return

    def configure_filters(self, freq, rx_path=-1):
        """
        Configure both HPF and LPF

        Args:
            freq (int): Desired frequency

            rx_path (int): Index of RF path to set filters for
                           ([0-1] or -1 for both). (Default: -1)
        """
        self.configure_lpf(freq, rx_path)
        self.configure_hpf(freq, rx_path)

    def configure_unfiltered(self, rx_path=-1):
        """
        Configure the RX filters to the unfiltered setting

        Args:
            rx_path (int): Index of RF path to set filters for
                           ([0-1] or -1 for both). (Default: -1)
        """
        self.configure_lpf(4000000000, rx_path)
        self.configure_hpf(100000000, rx_path)
