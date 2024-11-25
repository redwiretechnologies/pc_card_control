# SPDX-FileCopyrightText: 2024 Red Wire Technologies <support@redwiretechnologies.us>

# SPDX-License-Identifier: MIT

import gpiod
from .gpio_line_mux import *
from .iio_gpo_control import *
from .constants import *

class cardf:

    # gpiochip_num is the number of the gpiochip for the CARDF
    # This can be found by running gpioinfo from the terminal
    # transceiver_num specifies which transceiver card you are using ([0-1] on Carbon)
    def __init__(self, gpiochip_num, control_rxtx=1):
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

    def enable_bt(self):
        for gpio in self.bt_enable:
            gpio.set_values([1])

    def disable_bt(self):
        for gpio in self.bt_enable:
            gpio.set_values([0])

    def enable_wifi(self):
        for gpio in self.wifi_enable:
            gpio.set_values([1])

    def disable_wifi(self):
        for gpio in self.wifi_enable:
            gpio.set_values([0])

    def enable_lnas(self):
        for gpio in self.lna_enable:
            gpio.set_values([1])

    def disable_lnas(self):
        for gpio in self.lna_enable:
            gpio.set_values([0])

    #Configure the band pass filter
    def configure_rx_filters(self, freq):
        freqs = [([ 902000000,  928000000], [0, 1]),
                 ([2400000000, 2500000000], [1, 0]),
                 ([5000000000, 6000000000], [1, 1]),
                 ([         0, 9999999999], [0, 0])]

        freq_names = ["900MHz", "2.4GHz", "5GHz", "UNFILTERED"]
        for i, k in enumerate(freqs):
            if freq >= k[0][0] and freq <= k[0][1]:
                for gpio, val in zip(self.rx_bpf, k[1]):
                    gpio.set_values([val])
                print("Set BPF to {}".format(freq_names[i]))
                return

    #Make RX Unfiltered
    def configure_rx_unfiltered(self):
        self.configure_rx_filters(1)

    def enable_pa(self):
        print("Enabling PAs")
        if self.rx:
            for gpio in self.rx:
                gpio.set_values([0])
        if self.tx:
            for gpio in self.tx:
                gpio.set_values([1])
        for gpio in self.pa_enable:
            gpio.set_values([1])
        for gpio in self.tx_enable:
            gpio.set_values([1])
        self.tx_inhib.set_values([0])

    def disable_pa(self):
        print("Disabling PAs")
        self.tx_inhib.set_values([1])
        for gpio in self.tx_enable:
            gpio.set_values([0])
        for gpio in self.pa_enable:
            gpio.set_values([0])
        if self.rx:
            for gpio in self.rx:
                gpio.set_values([1])
        if self.tx:
            for gpio in self.tx:
                gpio.set_values([0])

    #Configure TX notch filters
    def configure_tx_filters(self, freq, rx_path=-1):
        freqs = {  230000000: [1, 0, 1],
                   560000000: [0, 1, 1],
                  1300000000: [1, 1, 0],
                  3125000000: [0, 1, 0],
                  9999999999: [0, 0, 1]} #UNFILTERED

        for k, v in freqs.items():
            if freq <= k:
                print("Configuring TX filters for {}".format(k))
                if rx_path == -1:
                    for r in [0, 1]:
                        for gpio, val in zip(self.tx_filt[r], v):
                            gpio.set_values([val])
                else:
                    for gpio, val in zip(self.tx_filt[rx_path], v):
                        gpio.set_values([val])
                return

    #Make TX unfiltered
    def configure_tx_unfiltered(self, rx_path=-1):
        self.configure_tx_filters(4000000000)
