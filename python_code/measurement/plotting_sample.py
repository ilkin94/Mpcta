#!/usr/bin/python
import numpy as np
import matplotlib.mlab as mlab
import matplotlib.pyplot as plt
import scipy as sp
import scipy.stats
import json
 
file_ref = open("measurement_data.json","r")

data = json.load(file_ref)

file_ref.close()

samples = data['6']

num_bins = len(samples)

print np.mean(samples)

n, bins, patches = plt.hist(samples, num_bins, facecolor='blue')

print np.std(samples)

print n
print bins

plt.show()
