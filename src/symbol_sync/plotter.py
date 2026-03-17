import numpy as np

import matplotlib.pyplot as plt


# Data
data = np.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -0.000398275, 1.1614e-05, 0.00049177, -1.6217e-05, -0.000622524, 2.3613e-05, 0.000813336, -3.62873e-05, -0.00110755, 5.99324e-05, 0.0015961, -0.000109536, -0.00249742, 0.000233275, 0.00445344, -0.000643275, -0.0101086, 0.00303258, 0.0424561, -0.10614, 1.13702, -0.10614, 0.0424561, 0.00303258, -0.0101086, -0.000643275, 0.00445344, 0.000233275, -0.00249742, -0.000109536])

# Create scatter plot
x = np.arange(len(data))
plt.scatter(x, data, alpha=0.6)
plt.xlabel("Index")
plt.ylabel("Value")
plt.title("Scatter Plot")
plt.grid(True, alpha=0.3)
plt.show()