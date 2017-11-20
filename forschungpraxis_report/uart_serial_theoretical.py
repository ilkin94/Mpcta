#!/usr/bin/env python3

import binascii
import pprint
import matplotlib.pyplot as plt
import numpy as np


x_axis = np.arange(1,128)

y_axis = x_axis*86.6

print (y_axis)


plt.plot(x_axis,y_axis)
plt.xticks(np.arange(0, 130, 5))
plt.yticks(np.arange(0, 13000, 500))
plt.title('UART serial transmission delay')
plt.grid(color='gray', linestyle='dotted')
plt.xlabel('UART data size')
plt.ylabel('UART transmission delay in micro seconds')

plt.show()
