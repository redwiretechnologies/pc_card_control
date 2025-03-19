# SPDX-FileCopyrightText: 2024 Red Wire Technologies <support@redwiretechnologies.us>

# SPDX-License-Identifier: MIT

import iio
from enum import Enum
from .constants import *

"""Registers specific to an AD9361"""
GPIO_CTRL_NUM = 0x26
GPIO_CTRL_BIT = 4
GPIO_REG_NUM = 0x27

class AD9361_GPO(Enum):
    """Bit indices specific to an AD9361"""
    ADGPO_0 = 4
    ADGPO_1 = 5
    ADGPO_2 = 6
    ADGPO_3 = 7

class iio_gpo_control:
    """ A class for controlling the GPOs on an IIO device like gpiod"""

    def __init__(self, dev_device="ad9361-phy"):
        """
        Initialize an iio_gpo_control instance

        Args:
            dev_device (str): Name of IIO dev device to control
                              (Default: "ad9361-phy")
        """
        self.ctx = iio.LocalContext()
        self.ctrl = self.ctx.find_device(dev_device)
        self.write(GPIO_CTRL_NUM, self.read(GPIO_CTRL_NUM) | (1 << GPIO_CTRL_BIT))

    def read(self, reg):
        """
        Read a register from the IIO device

        Args:
            reg (int): Register number to read

        Returns:
            int: Register value read
        """
        return self.ctrl.reg_read(reg)

    def write(self, reg, val):
        """
        Write a register to the IIO device

        Args:
            reg (int): Register number to read

            val (int): Value to write to the register
        """
        self.ctrl.reg_write(reg, val)

    def get_lines(self, line_num):
        """
        Function to match gpiod structure for controlling gpios

        Args:
            line_num (int): Number corresponding to the requested GPO to
                            control

        Returns:
            iio_gpo_line: An instance that can be operated on like a GPIO
                          line
        """
        return iio_gpo_line(self, line_num)

    def set_value(self, pin_num, output_value):
        """
        Either sets or unsets the requested bit in the register

        Args:
            pin_num (int): The desired bit to control in the register

            output_value (int): The desired setting of the bit in the
                                register
        """
        if output_value == 0:
            self.write(GPIO_REG_NUM, self.read(GPIO_REG_NUM) & ~(1 << pin_num))
        else:
            self.write(GPIO_REG_NUM, self.read(GPIO_REG_NUM) | (1 << pin_num))

class iio_gpo_line:
    """
    A class to control a iio_gpo like a normal GPIO line from gpiod
    """
    def __init__(self, iio_gpo, input_nums):
        """
        Create an iio_gpo_line instance

        Args:
            iio_gpo (iio_gpo_control): Parent iio_gpo_control instance to
                                       operate through

            input_nums (list[int]): Desired input indices to control
        """
        self.parent = iio_gpo
        self.input_lines = input_nums

    def set_values(self, output_vals):
        """
        Set the input_lines to the requested output_vals in the same
        structure as gpiod

        Args:
            output_vals (list[int]): Desired values to set the input_lines
                                     to
        """
        for z in zip(self.input_lines, output_vals):
            self.parent.set_value(z[0], z[1])
