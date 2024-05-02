import gpiod

class selenium:

    # pc_slot is the personality card slot ([0-4] on CARP)
    # gpiochip_num is the number of the gpiochip for the given Selenium
    # This can be found by running gpioinfo from the terminal
    def __init__(self, pc_slot, gpiochip_num):
        self.gpiochip2 = gpiod.Chip('gpiochip2')
        self.gpiochip  = gpiod.Chip("gpiochip{}".format(gpiochip_num))

        self.lpf = [[None]*3, [None]*3]
        self.hpf = [[None]*3, [None]*3]

        # The first four of these lines live on an I2C expander on CARP
        # The position of the GPIOs on the expander are relative to the
        # slot number
        self.lpf[0][0] = self.gpiochip2.get_lines([6*pc_slot+1])
        self.lpf[0][1] = self.gpiochip2.get_lines([6*pc_slot+2])
        self.lpf[0][2] = self.gpiochip2.get_lines([6*pc_slot+3])
        self.hpf[0][0] = self.gpiochip2.get_lines([6*pc_slot+4])

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

    #Configure the low pass filter
    def configure_lpf(self, freq):
        freqs = {  145000000: [0, 1, 0],
                   440000000: [0, 1, 1],
                  1370000000: [1, 0, 1],
                  3000000000: [1, 1, 0],
                  9999999999: [0, 0, 1]} #UNFILTERED

        for k, v in freqs.items():
            if freq <= k:
                for gpio, val in zip(self.lpf[0], v):
                    gpio.set_values([val])
                for gpio, val in zip(self.lpf[1], v):
                    gpio.set_values([val])
                print("Set LPF to {}".format(k))
                return

    # Configure the high pass filter
    def configure_hpf(self, freq):
        freqs = { 3780000000: [1, 1, 0],
                  1930000000: [1, 0, 1],
                   840000000: [0, 1, 1],
                   135000000: [0, 1, 0],
                           0: [0, 0, 1]} #UNFILTERED

        for k, v in freqs.items():
            if freq >= k:
                for gpio, val in zip(self.hpf[0], v):
                    gpio.set_values([val])
                for gpio, val in zip(self.hpf[1], v):
                    gpio.set_values([val])
                print("Set HPF to {}".format(k))
                return

    # Configure both sets of filters
    def configure_filters(self, freq):
        self.configure_lpf(freq)
        self.configure_hpf(freq)
