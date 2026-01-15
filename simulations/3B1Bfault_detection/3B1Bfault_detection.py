import numpy as np
import matplotlib.pyplot as plt
import random
pow = 4 #needs to be even

def create_message(power): #creates a random message without fault detection bits (works)
    totalPackageLength = 2**power # a power of 2
    dataLength = totalPackageLength - power - 1
    datastring = np.array([random.randint(0,1) for i in range(dataLength)])
    return datastring

def fault_protect(msg): #adds fault detection bits to message
    power = int(np.ceil(np.log2(len(msg))))
    package = np.zeros(2 ** power)
    msg_index = 0

    for i in range(1, len(package)):#makes array long enough for fault detection and sort error detecting bits on powers of 2
        if int(np.log2(i)) != np.log2(i): #error correcting bits are yet not set
            package[i] = msg[msg_index]
            msg_index += 1
    
    to_add = 0 #parameter to figure what fault detection bits to set
    for i in range(len(package)):
        if package[i] == 1:
            to_add = np.bitwise_xor(to_add, i)

    for i in range(power):
        if (to_add >> i & 1 == 1):
            package[2**i] = 1
   
    return package


def format_message(msg): #only makes it in "human readable" format 

    if np.log2(len(msg)) != int(np.log2(len(msg))):
        print("forgot fault protection!!!")
        return 0        

    shape = (int(np.sqrt(len(msg))),int(np.sqrt(len(msg))))
    msg = np.reshape(msg,shape)
    return msg



msg = create_message(pow)
print(msg)

msg = fault_protect(msg)
print(msg)

msg = format_message(msg)
print(msg)


