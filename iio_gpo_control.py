# SPDX-FileCopyrightText: 2024 Red Wire Technologies <support@redwiretechnologies.us>

# SPDX-License-Identifier: MIT

import iio

GPIO_CTRL_NUM = 0x26
GPIO_CTRL_BIT = 4
GPIO_REG_NUM = 0x27

L = [0]
H = [1]

ADGPO_0 = 4
ADGPO_1 = 5
ADGPO_2 = 6
ADGPO_3 = 7

class iio_gpo_control:

    def __init__(self, dev_device="ad9361-phy"):
        self.ctx = iio.LocalContext()
        self.ctrl = self.ctx.find_device(dev_device)
        self.write(GPIO_CTRL_NUM, self.read(GPIO_CTRL_NUM) | (1 << GPIO_CTRL_BIT))

    def read(self, reg):
        return self.ctrl.reg_read(reg)

    def write(self, reg, val):
        self.ctrl.reg_write(reg, val)

    def get_lines(self, line_num):
        return iio_gpo_line(self, line_num)

    def set_value(self, pin_num, output_value):
        if output_value == 0:
            self.write(GPIO_REG_NUM, self.read(GPIO_REG_NUM) & ~(1 << pin_num))
        else:
            self.write(GPIO_REG_NUM, self.read(GPIO_REG_NUM) | (1 << pin_num))

class iio_gpo_line:

    def __init__(self, gpio_mux, input_nums):
        self.parent = gpio_mux
        self.input_lines = input_nums

    def set_values(self, output_vals):
        for z in zip(self.input_lines, output_vals):
            self.parent.set_value(z[0], z[1])
