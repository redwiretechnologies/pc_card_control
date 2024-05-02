import gpiod

GPIOCHIP = 0
CLOCK = [78]
RESET = [79]

#These are intentionally rearranged to make this less confusing
#INPUT GPIOS will select the signal that I'm wanting to write a value to
#OUTPUT GPIOS selects the value I want to write (whether a signal or high/low)
OUTPUT_GPIOS = [83, 82, 81, 80]
INPUT_GPIOS  = [87, 86, 85, 84]
BIT_LENGTH = 4

L = [0]
H = [1]

#These are input mappings to "GPIO" line numbers
#Format RFP_[socket_num]_ADGPO_[pin_num]
#RFP = RF personality
#socket_num = Personality socket number
#ADGPO = Analog Devices (transceiver) general purpose output
#pin_num = GPO pin number for the Analog Devices chip
#On Oxygen, these would be direct connections to the GPO pins on the transceiver
#On Carbon with CARP, these can be configured to connect any personality card's GPO pin to any of the transceivers GPO pins
RFP_0_ADGPO_1 = 0
RFP_0_ADGPO_2 = 1
RFP_1_ADGPO_0 = 2
RFP_1_ADGPO_1 = 3
RFP_1_ADGPO_2 = 4
RFP_2_ADGPO_0 = 5
RFP_2_ADGPO_1 = 6
RFP_2_ADGPO_2 = 7
RFP_3_ADGPO_0 = 8
RFP_3_ADGPO_1 = 9

#These are output mappings to "values" you can set the "GPIO" lines to
#LOW and HIGH are logic '0' and '1' respectively
#Format of others AD_[transceiver_num]_RFIC_GPO_[pin_num]
LOW             = 0
HIGH            = 1
AD_0_RFIC_GPO_0 = 2
AD_0_RFIC_GPO_1 = 3
AD_0_RFIC_GPO_2 = 4
AD_0_RFIC_GPO_3 = 5
AD_1_RFIC_GPO_0 = 6
AD_1_RFIC_GPO_1 = 7
AD_1_RFIC_GPO_2 = 8
AD_1_RFIC_GPO_3 = 9

def bitfield(n):
    return [1 if digit=='1' else 0 for digit in bin(n)[2:].zfill(BIT_LENGTH)]

class gpio_line_mux:

    def __init__(self):
        self.gpiochip = gpiod.Chip('gpiochip0')

        self.clock = self.gpiochip.get_lines(CLOCK)
        self.clock.request(consumer="GPIO_MUX", type=gpiod.LINE_REQ_DIR_OUT)

        self.reset = self.gpiochip.get_lines(RESET)
        self.reset.request(consumer="GPIO_MUX", type=gpiod.LINE_REQ_DIR_OUT)

        self.input_lines = self.gpiochip.get_lines(INPUT_GPIOS)
        self.input_lines.request(consumer="GPIO_MUX", type=gpiod.LINE_REQ_DIR_OUT)

        self.output_lines = self.gpiochip.get_lines(OUTPUT_GPIOS)
        self.output_lines.request(consumer="GPIO_MUX", type=gpiod.LINE_REQ_DIR_OUT)

        self.reset_chip()

    def reset_chip(self):
        self.reset.set_values(L)
        self.reset.set_values(H)

    def pulse(self):
        self.clock.set_values(H)
        self.clock.set_values(L)

    def get_lines(self, line_num):
        return mux_gpio(self, line_num)

    def set_value(self, input_nums, output_nums):
        self.input_lines.set_values(input_nums)
        self.output_lines.set_values(output_nums)
        self.pulse()

class mux_gpio:

    def __init__(self, gpio_mux, input_nums):
        self.parent = gpio_mux
        self.input_lines = [bitfield(input_num) for input_num in input_nums]

    def set_values(self, output_nums):
        for z in zip(self.input_lines, output_nums):
            self.parent.set_value(z[0], bitfield(z[1]))
