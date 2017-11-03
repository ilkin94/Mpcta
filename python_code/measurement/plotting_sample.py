#!/usr/bin/python
import numpy as np
import matplotlib.mlab as mlab
import matplotlib.pyplot as plt
import scipy as sp
import scipy.stats
import json
 
file_ref = open("measurement_udp_data.json","r")

data = json.load(file_ref)

file_ref.close()

#sample count is how many samples are taken for any one payload len, any payload length will do.
sample_count = len(data['6'])
sample_means = []

for key in data:
    mean = np.mean(data[key])
    sample_means.append(mean)
    x_axis.append(int(key))

plt.plot(x_axis,sample_means,'g.',label = 'Processing Delay',markersize=5)

plt.show()
