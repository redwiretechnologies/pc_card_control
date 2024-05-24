# SPDX-FileCopyrightText: 2024 Red Wire Technologies <support@redwiretechnologies.us>

# SPDX-License-Identifier: MIT

import gpiod
from .gpio_line_mux import *
from .iio_gpo_control import *

class tellurium:

    # pc_slot is the personality card slot ([0-4] on CARP)
    # gpiochip_num is the number of the gpiochip for the given Tellurium
    # This can be found by running gpioinfo from the terminal
    # transceiver_num specifies which transceiver card you are using ([0-1] on Carbon)
    def __init__(self, pc_slot, gpiochip_num, transceiver_num, carp=1):
        self.gpiochip0 = gpiod.Chip('gpiochip0')
        if carp:
            self.gpiochip2 = gpiod.Chip('gpiochip2')
            self.line_mux  = gpio_line_mux()
        else:
            self.gpo_ctrl = iio_gpo_control()
        self.gpiochip  = gpiod.Chip("gpiochip{}".format(gpiochip_num))

        if carp:
            match pc_slot:
                case 0:
                    self.tx_enable = self.line_mux.get_lines([RFP_0_ADGPO_2])
                case 1:
                    self.tx_enable = self.line_mux.get_lines([RFP_1_ADGPO_2])
                case 2:
                    self.tx_enable = self.line_mux.get_lines([RFP_2_ADGPO_2])
                case 3:
                    self.tx_enable = self.line_mux.get_lines([RFP_3_ADGPO_2])
        else:
            self.tx_enable = self.gpo_ctrl.get_lines([ADGPO_2])

        #These lines are for controlling the RX/TX on the transceivers
        if carp:
            self.rx = self.gpiochip0.get_lines([132+transceiver_num*3])
            self.tx = self.gpiochip0.get_lines([133+transceiver_num*3])
        else:
            self.rx = self.gpiochip0.get_lines([125])
            self.tx = self.gpiochip0.get_lines([126])

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
    #Configure the low pass filter
    def configure_rx_lpf(self, freq):
        freqs = {  145000000: [0, 1, 0],
                   440000000: [0, 1, 1],
                  1370000000: [1, 0, 1],
                  3000000000: [1, 1, 0],
                  9999999999: [0, 0, 1]} #UNFILTERED

        for k, v in freqs.items():
            if freq <= k:
                for gpio, val in zip(self.rx_lpf, v):
                    gpio.set_values([val])
                print("Set LPF to {}".format(k))
                return

    # Configure the high pass filter
    def configure_rx_hpf(self, freq):
        freqs = { 3780000000: [1, 1, 0],
                  1930000000: [1, 0, 1],
                   840000000: [0, 1, 1],
                   135000000: [0, 1, 0],
                           0: [0, 0, 1]} #UNFILTERED

        for k, v in freqs.items():
            if freq >= k:
                for gpio, val in zip(self.rx_hpf, v):
                    gpio.set_values([val])
                print("Set HPF to {}".format(k))
                return

    # Configure both sets of filters
    def configure_rx_filters(self, freq):
        self.configure_rx_lpf(freq)
        self.configure_rx_hpf(freq)

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
        self.rx.set_values([0])
        self.tx.set_values([1])
        self.pa_enable.set_values([1])
        self.tx_enable.set_values([1])

    def disable_pa(self):
        print("Disabling PAs")
        self.rx.set_values([1])
        self.tx.set_values([0])
        self.pa_enable.set_values([0])
        self.tx_enable.set_values([0])

    #These are each notch filters
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
