# SPDX-FileCopyrightText: 2024 Red Wire Technologies <support@redwiretechnologies.us>

# SPDX-License-Identifier: MIT

import gpiod
from .gpio_line_mux import *
from .iio_gpo_control import *
from .constants import *

class bismuth:

    # pc_slot is the personality card slot ([0-4] on CARP)
    # gpiochip_num is the number of the gpiochip for the given Bismuth
    # This can be found by running gpioinfo from the terminal
    # transceiver_num specifies which transceiver card you are using ([0-1] on Carbon)
    def __init__(self, pc_slot, gpiochip_num, transceiver_num, carp=1, control_rxtx=1):
        self.gpiochip0 = gpiod.Chip('gpiochip{}'.format(BASE_GPIO_CHIP))
        if carp:
            self.gpiochip2 = gpiod.Chip('gpiochip{}'.format(CARP_GPIO_CHIP))
            self.line_mux  = gpio_line_mux()
        else:
            self.gpo_ctrl = iio_gpo_control()
        self.gpiochip  = gpiod.Chip("gpiochip{}".format(gpiochip_num))

        self.lna_enable = [None]*2
        if carp:
            match pc_slot:
                case 0:
                    print("Bismuth not supported in slot 0")
                    exit(1)
                case 1:
                    self.lna_enable[0] = self.line_mux.get_lines([RFP_1_ADGPO_0])
                    self.lna_enable[1] = self.line_mux.get_lines([RFP_1_ADGPO_1])
                    self.tx_enable = self.line_mux.get_lines([RFP_1_ADGPO_2])
                case 2:
                    self.lna_enable[0] = self.line_mux.get_lines([RFP_2_ADGPO_0])
                    self.lna_enable[1] = self.line_mux.get_lines([RFP_2_ADGPO_1])
                    self.tx_enable = self.line_mux.get_lines([RFP_2_ADGPO_2])
                case 3:
                    print("Bismuth not supported in slot 3")
                    exit(1)
        else:
            self.lna_enable[0] = self.gpo_ctrl.get_lines([ADGPO_0])
            self.lna_enable[1] = self.gpo_ctrl.get_lines([ADGPO_1])
            self.tx_enable = self.gpo_ctrl.get_lines([ADGPO_2])

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

        self.pa      = [None]*2
        self.tx_filt = [None]*3

        # The first four of these lines live on an I2C expander on CARP
        # The position of the GPIOs on the expander are relative to the
        # slot number
        if carp:
            self.pa[0] = self.gpiochip2.get_lines([6*pc_slot+1])
            self.pa[1] = self.gpiochip2.get_lines([6*pc_slot+2])
            self.tx_filt[0] = self.gpiochip2.get_lines([6*pc_slot+3])
            self.tx_filt[1] = self.gpiochip2.get_lines([6*pc_slot+4])
            self.tx_filt[2] = self.gpiochip2.get_lines([6*pc_slot+5])
        else:
            self.pa[0] = self.gpiochip0.get_lines([94])
            self.pa[1] = self.gpiochip0.get_lines([95])
            self.tx_filt[0] = self.gpiochip0.get_lines([96])
            self.tx_filt[1] = self.gpiochip0.get_lines([97])
            self.tx_filt[2] = self.gpiochip0.get_lines([98])

        self.rx_att = [None]*2
        self.rx_att[0] = self.gpiochip.get_lines([5])
        self.rx_att[1] = self.gpiochip.get_lines([6])
        self.pa_enable = self.gpiochip.get_lines([7])

        self.pa_enable.request(consumer='BISMUTH_PA_ENABLE', type=gpiod.LINE_REQ_DIR_OUT)
        if control_rxtx:
            self.rx.request(consumer='BISMUTH_RX_CTRL', type=gpiod.LINE_REQ_DIR_OUT)
            self.tx.request(consumer='BISMUTH_TX_CTRL', type=gpiod.LINE_REQ_DIR_OUT)

        for i in self.pa:
            i.request(consumer='BISMUTH_PA', type=gpiod.LINE_REQ_DIR_OUT)
        for i in self.rx_att:
            i.request(consumer='BISMUTH_RX_ATT', type=gpiod.LINE_REQ_DIR_OUT)
        for i in self.tx_filt:
            i.request(consumer='BISMUTH_TX_FILT', type=gpiod.LINE_REQ_DIR_OUT)

    # Configure PA
    # 0=No PA
    # 1=First Stage PA
    # 2=Full Power PA
    def configure_pa(self, power_level):

        power = [[0, 0],
                 [1, 0],
                 [1, 1]]

        if power_level not in range(0, 3):
            print("Power level must be 0-2")
            return

        for gpio, val in zip(self.pa, power[power_level]):
            gpio.set_values([val])
        print("Power level set to {}".format(power_level))

    def enable_pa(self):
        print("Enabling PAs")
        if self.rx:
            self.rx.set_values([0])
        if self.tx:
            self.tx.set_values([1])
        self.disable_lnas()
        self.pa_enable.set_values([1])
        self.tx_enable.set_values([1])

    def disable_pa(self):
        print("Disabling PAs")
        self.tx_enable.set_values([0])
        self.pa_enable.set_values([0])
        if self.rx:
            self.rx.set_values([1])
        if self.tx:
            self.tx.set_values([0])
        self.enable_lnas()

    #Configure TX LPF
    def configure_tx_filters(self, freq):
        freqs = {  230000000: [1, 0, 1],
                   560000000: [0, 1, 1],
                  1300000000: [1, 1, 0],
                  3125000000: [0, 1, 0],
                  9999999999: [0, 0, 1]} #UNFILTERED

        for k, v in freqs.items():
            if freq <= k:
                print("Configuring TX filters for {}".format(k))
                for gpio, val in zip(self.tx_filt, v):
                    gpio.set_values([val])
                return

    #Make TX unfiltered
    def configure_tx_unfiltered(self):
        self.configure_tx_filters(4000000000)

    def enable_lnas(self):
        print("Enabling LNAs")
        for i in self.lna_enable:
            i.set_values([1])

    def disable_lnas(self):
        print("Disabling LNAs")
        for i in self.lna_enable:
            i.set_values([0])

    # Configure RX Attentuation
    # 0= 0dB
    # 1= 6dB
    # 2= 12dB
    # 3= 18dB
    def configure_rx_att(self, rx_att):

        rx_lev = [[0, 0],
                  [0, 1],
                  [1, 0],
                  [1, 1]]

        rx_map = [0, 6, 12, 18]

        if rx_att not in range(0, 4):
            print("RX Attentuation level must be 0-3")
            return

        for gpio, val in zip(self.rx_att, rx_lev[rx_att]):
            gpio.set_values([val])
        print("RX Attentuation set to {}dB".format(rx_map[rx_att]))
