# SPDX-FileCopyrightText: 2024 Red Wire Technologies <support@redwiretechnologies.us>

# SPDX-License-Identifier: MIT

import gpiod
import smbus
import time
import copy
import logging
from .gpio_line_mux import *
from .iio_gpo_control import *
from .constants import *

class synth_settings:
    """
    A class for holding the synthesizer settings for Argon
    """
    def __init__(self):
        self.base_map = [[0x4e, 0x00, 0x03], [0x4d, 0x00, 0x00], [0x4c, 0x00, 0x0c],
                         [0x4b, 0x08, 0x00], [0x4a, 0x00, 0x00], [0x49, 0x00, 0x3f],
                         [0x48, 0x00, 0x01], [0x47, 0x00, 0x81], [0x46, 0xc3, 0x50],
                         [0x45, 0x00, 0x00], [0x44, 0x03, 0xe8], [0x43, 0x00, 0x00],
                         [0x42, 0x01, 0xf4], [0x41, 0x00, 0x00], [0x40, 0x13, 0x88],
                         [0x3f, 0x00, 0x00], [0x3e, 0x03, 0x22], [0x3d, 0x00, 0xa8],
                         [0x3c, 0x00, 0x00], [0x3b, 0x00, 0x01], [0x3a, 0x90, 0x01],
                         [0x39, 0x00, 0x20], [0x38, 0x00, 0x00], [0x37, 0x00, 0x00],
                         [0x36, 0x00, 0x00], [0x35, 0x00, 0x00], [0x34, 0x08, 0x20],
                         [0x33, 0x00, 0x80], [0x32, 0x00, 0x00], [0x31, 0x41, 0x80],
                         [0x30, 0x03, 0x00], [0x2f, 0x03, 0x00], [0x2e, 0x07, 0xfc],
                         [0x2d, 0xc0, 0xdf], [0x2c, 0x1f, 0x23], [0x2b, 0x01, 0x2c],
                         [0x2a, 0x00, 0x00], [0x29, 0x00, 0x00], [0x28, 0x00, 0x00],
                         [0x27, 0x03, 0xe8], [0x26, 0x00, 0x00], [0x25, 0x04, 0x04],
                         [0x24, 0x00, 0x3b], [0x23, 0x00, 0x04], [0x22, 0x00, 0x00],
                         [0x21, 0x1e, 0x21], [0x20, 0x03, 0x93], [0x1f, 0x43, 0xec],
                         [0x1e, 0x31, 0x8c], [0x1d, 0x31, 0x8c], [0x1c, 0x04, 0x88],
                         [0x1b, 0x00, 0x02], [0x1a, 0x0d, 0xb0], [0x19, 0x0c, 0x2b],
                         [0x18, 0x07, 0x1a], [0x17, 0x00, 0x7c], [0x16, 0x00, 0x01],
                         [0x15, 0x04, 0x01], [0x14, 0xe0, 0x48], [0x13, 0x27, 0xb7],
                         [0x12, 0x00, 0x64], [0x11, 0x01, 0x2c], [0x10, 0x00, 0x80],
                         [0x0f, 0x06, 0x4f], [0x0e, 0x1e, 0x70], [0x0d, 0x40, 0x00],
                         [0x0c, 0x50, 0x01], [0x0b, 0x00, 0x18], [0x0a, 0x12, 0xd8],
                         [0x09, 0x06, 0x04], [0x08, 0x20, 0x00], [0x07, 0x00, 0xb2],
                         [0x06, 0xc8, 0x02], [0x05, 0x00, 0xc8], [0x04, 0x0a, 0x43],
                         [0x03, 0x06, 0x42], [0x02, 0x05, 0x00], [0x01, 0x08, 0x08],
                         [0x00, 0x27, 0x14],
                        ]
        """
        list[list[int]]: Default register settings for the synthesizer to
                         configure for 5.93GHz
        """

        self.change_map = {0: {},
                           1: { 32: [0x2E, 0x07, 0xFD],
                                33: [0x2D, 0xC8, 0xDF],
                              },
                           2: { 32: [0x2E, 0x07, 0xFD],
                                33: [0x2D, 0xC8, 0xDF],
                                35: [0x2B, 0x00, 0x00],
                                42: [0x24, 0x00, 0x4B],
                              },
                          }
        """
        dict: A list of changes that should be made to the base register
              configuration dependent on frequency.  Top level keys
              correspond to the given index of the frequency in
              SYNTH_FREQ. The second level keys refer to the index in the
              base_map (78-desired_register_number)
        """

        self.SYNTH_BOUNDS = [6e9, 11930e6, 17860e6, 21e9]
        """
        list[int]: List of boundary crossovers to switch to the next set of
                   frequency settings
        """
        self.SYNTH_FREQ   = [5930e6, 11860e6, 15e9]
        """
        list[int]: The actual frequency the synthesizer is configured for
                   if you cross SYNTH_BOUND[i+1]
        """

        self.RESET   = [0x00, 0x24, 0x12, 0x00, 0x24, 0x10]
        """
        list[int]: Commands to be sent to reset the synthesizer
        """
        self.POWER_D = [0x00, 0x24, 0x11]
        """
        list[int]: Commands to be sent to power down the synthesizer
        """
        self.POWER_U = [0x00, 0x24, 0x10]
        """
        list[int]: Commands to be sent to power up the synthesizer
        """
        self.FCAL_EN = [0x00, 0x27, 0x1C]
        """
        list[int]: Commands to be sent to enable calibration on the
                   synthesizer
        """

    def get_settings(self, index):
        """
        Returns a copy of the register settings with the proper
        replacements based on the index

        Args:
            index (int): The index of the desired frequency setting from
                         SYNTH_FREQ

        Returns:
            list[list[int]]: The proper register settings to be applied
        """
        settings = copy.deepcopy(self.base_map)
        for k, v in self.change_map[index].items():
            settings[k] = v
        return settings

class argon:
    """
    A class for controlling the Argon personality card

    **Expected declaration:**

        my_argon = pc_card_control.argon(0, 2, 0, 1, 0x2B)
    """

    def __init__(self, pc_slot, gpiochip_num, transceiver_num, i2cbus, address, carp=0, control_rxtx=1, reset=1):
        """
        Initialize an Argon board

        Args:
            pc_slot (int): Personality card slot number ([0-4]). If not on
                           CARP, use 0

            gpiochip_num (int): Number of the gpiochip that is created when
                                the Argon DTS is loaded (this can be found
                                via gpioinfo in the terminal)

            transceiver_num (int): The number of which transceiver this is
                                   connected to.

            i2cbus (int): The number of the i2cbus that the Argon's I2C->SPI
                          is connected to.

            address (int): The I2C address of the Argon's I2C->SPI chip

            carp (int): Is this on a CARP (Default: 0)

            control_rxtx (int): Should this control the transceiver's RX/TX
                                lines (Default: 1)

            reset (int): Should the reset() function be called at the end
                         of initialization (Default:1)
        """
        #Setup logger
        self.log = logging.getLogger("argon_{}".format(pc_slot))

        self.synth_settings = synth_settings()

        #This chip select is defined here as it should never change
        self.CS = 0x01

        #Debug log to express initialization parameters
        self.log.debug("Argon init")
        self.log.debug("Using base GPIOCHIP{}".format(BASE_GPIO_CHIP))
        self.log.debug("Using secondary GPIOCHIP{}".format(gpiochip_num))
        if carp:
            self.log.debug("Using CARP GPIOCHIP{}".format(CARP_GPIO_CHIP))
        self.log.debug("Using Personality Card slot {}".format(pc_slot))
        self.log.debug("Using Transceiver {}".format(transceiver_num))
        self.log.debug("Using I2C{} {}".format(i2cbus, hex(address)))
        if control_rxtx:
            self.log.debug("Set to control RX/TX")

        #GPIO setup
        self.gpiochip0 = gpiod.Chip('gpiochip{}'.format(BASE_GPIO_CHIP))
        if carp:
            self.gpiochip2 = gpiod.Chip('gpiochip{}'.format(CARP_GPIO_CHIP))
            self.line_mux  = gpio_line_mux()
        else:
            self.gpo_ctrl = iio_gpo_control()
        self.gpiochip  = gpiod.Chip("gpiochip{}".format(gpiochip_num))

        self.bus = smbus.SMBus(i2cbus)
        self.address = address
        self.bus.write_i2c_block_data(self.address, 0x00, [0x00])

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

        self.tx_filt = [None]*3

        # The first four of these lines live on an I2C expander on CARP
        # The position of the GPIOs on the expander are relative to the
        # slot number
        if carp:
            self.tx_filt[0] = self.gpiochip2.get_lines([6*pc_slot+1])
            self.tx_filt[1] = self.gpiochip2.get_lines([6*pc_slot+2])
            self.tx_filt[2] = self.gpiochip2.get_lines([6*pc_slot+3])
        else:
            self.tx_filt[0] = self.gpiochip0.get_lines([95])
            self.tx_filt[1] = self.gpiochip0.get_lines([96])
            self.tx_filt[2] = self.gpiochip0.get_lines([97])

        # The rest of the lines live on an I2C expander on the Argon
        self.synth_en  = self.gpiochip.get_lines([0])
        self.rx_mix_en = self.gpiochip.get_lines([1])
        self.tx_mix_en = self.gpiochip.get_lines([2])

        self.synth_en.request( consumer='ARGON_SYNTH_EN',  type=gpiod.LINE_REQ_DIR_OUT)
        self.rx_mix_en.request(consumer='ARGON_RX_MIX_EN', type=gpiod.LINE_REQ_DIR_OUT)
        self.tx_mix_en.request(consumer='ARGON_TX_MIX_EN', type=gpiod.LINE_REQ_DIR_OUT)
        if control_rxtx:
            self.rx.request(consumer='ARGON_RX_CTRL', type=gpiod.LINE_REQ_DIR_OUT)
            self.tx.request(consumer='ARGON_TX_CTRL', type=gpiod.LINE_REQ_DIR_OUT)

        for i in self.tx_filt:
            i.request(consumer='ARGON_TX_FILT', type=gpiod.LINE_REQ_DIR_OUT)

        if reset:
            self.reset()

    def reset(self):
        """
        Base reset for the board. Turns off the synthesizer, disables TX
        filtering, and configures the board for receive
        """
        self.reset_synth()
        self.configure_tx_unfiltered()
        self.configure_receive()

    def configure_tx_filters(self, freq):
        """
        Configure the TX filters for the requested frequency

        Args:
            freq (int): Desired frequency to set. This does take the
                        current synthesizer settings into account.
        """
        freqs = {  230000000: [1, 0, 1],
                   560000000: [0, 1, 1],
                  1300000000: [1, 1, 0],
                  3125000000: [0, 1, 0],
                  9999999999: [0, 0, 1]} #UNFILTERED

        if self.current_synth_setting != -1:
            frequency = freq-self.synth_settings.SYNTH_FREQ[self.current_synth_setting]
        else:
            frequency = freq

        for k, v in freqs.items():
            if frequency <= k:
                self.log.info("Configuring TX filters for {}".format(k))
                for gpio, val in zip(self.tx_filt, v):
                    gpio.set_values([val])
                return

    def reset_synth(self):
        """
        Reset the synthesizer. Power it down via registers, disable it, and
        disable the RX/TX mixer paths
        """
        self.log.info("Resetting Synthesizer")
        self.send_spi(self.synth_settings.RESET)
        self.send_spi(self.synth_settings.POWER_D)
        self.current_synth_setting = -1
        self.synth_en.set_values([0])
        self.rx_mix_en.set_values([0])
        self.tx_mix_en.set_values([0])

    def configure_tx_unfiltered(self):
        """Configure the TX filters to the unfiltered setting"""
        self.configure_tx_filters(4000000000)

    def configure_synth(self, frequency, autofilter=False):
        """
        Configure the synthesizer for the given frequency. If autofilter
        is set, also set the proper TX filters. If the synthesizer must
        be used to achieve the desired frequency, we enable the RX/TX
        mixer paths and the synthesizer itself. If it is not required,
        we disable all of these.

        Args:
            frequency (int): The desired frequency for the radio to be
                             configured to.

            autofilter (bool): Change filters to the appropriate setting
                               after configuring the synthesizer. If the
                               desired frequency cannot be tuned to, this
                               will set the TX filters to unfiltered.
                               (Default: False)

        Returns:
            freq (int): Frequency that the radio should be tuned to for
                        the requested frequency (taking into account the
                        synthesizer setting).
        """
        self.reset_synth()
        if frequency >= self.synth_settings.SYNTH_BOUNDS[0]:
            #Power synth back up and enable
            self.synth_en.set_values([1])
            self.send_spi(self.synth_settings.POWER_U)
            self.send_spi(self.synth_settings.RESET)
            for i in range(1, len(self.synth_settings.SYNTH_BOUNDS)):
                if frequency < self.synth_settings.SYNTH_BOUNDS[i]:
                    self.log.info("Configuring synthesizer for frequency {}".format(self.synth_settings.SYNTH_FREQ[i-1]))
                    settings = self.synth_settings.get_settings(i-1)
                    for j in settings:
                        self.send_spi(j)
                    self.current_synth_setting = i-1
                    #According to the datasheet, you should wait 10ms before attempting calibration
                    time.sleep(10/1000)
                    self.send_spi(self.synth_settings.FCAL_EN)
                    break
                else:
                    self.current_synth_setting = i
            if self.current_synth_setting == len(self.synth_settings.SYNTH_BOUNDS)-1:
                self.log.warning("Could not tune to frequency {}. Frequency must be less than {}".format(frequency, self.synth_settings.SYNTH_BOUNDS[-1]))
                self.send_spi(self.synth_settings.POWER_D)
                self.current_synth_setting = -1
                self.synth_en.set_values([0])
                if autofilter:
                    self.configure_tx_unfiltered()
            else:
                if autofilter:
                    self.configure_tx_filters(frequency)
                self.rx_mix_en.set_values([1])
                self.tx_mix_en.set_values([1])
        elif autofilter:
            self.configure_tx_filters(frequency)
        if self.current_synth_setting == -1:
            return frequency
        else:
            return frequency-self.synth_settings.SYNTH_FREQ[self.current_synth_setting]

    def send_spi(self, data):
        """
        Sends a list of commands on the SPI bus.

        Args:
            data (list[int]): a list of single byte integers to send in the
                              form [addr, data_upper, data_lower, ...]
        """
        self.log.debug("Sending {}".format([hex(num) for num in data]))
        self.bus.write_i2c_block_data(self.address, self.CS, data)

    def configure_transmit(self):
        """
        Configures the radio for transmit. Disable RX and enables TX (if
        instance is created with control_rxtx set). Then actually sets
        the TX enable line
        """
        self.log.debug("Configuring radio for transmit")
        if self.rx:
            self.rx.set_values([0])
        if self.tx:
            self.tx.set_values([1])
        self.tx_enable.set_values([1])

    def configure_receive(self):
        """
        Configures the radio for receive. Disables the TX enable line.
        Then disable TX and enables RX (if instance is created with
        control_rxtx set).
        """
        self.log.debug("Configuring radio for receive")
        self.tx_enable.set_values([0])
        if self.tx:
            self.tx.set_values([0])
        if self.rx:
            self.rx.set_values([1])
