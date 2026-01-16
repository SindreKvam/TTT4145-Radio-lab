import numpy as np
import matplotlib.pyplot as plt
import random
pow = 4#needs to be even

def create_message(power): #creates a random message without fault detection bits (works)
    totalPackageLength = 2**power # a power of 2
    dataLength = totalPackageLength - power - 1
    datastring = np.array([random.randint(0,1) for i in range(dataLength)])
    return datastring

def fault_protect(msg): #adds fault detection bits to message(works)
    power = int(np.ceil(np.log2(len(msg))))
    package = np.zeros(2 ** power)
    msg_index = 0

    for i in range(1, len(package)):#makes array long enough for fault detection and sort error detecting bits on powers of 2
        if int(np.log2(i)) != np.log2(i): #error correcting bits are yet not set
            package[i] = msg[msg_index]
            msg_index += 1
    
    to_add = 0 #parameter to figure what fault detection bits to set
    for i in range(len(package)): #xor of all indexes having a 1
        if package[i] == 1:
            to_add = np.bitwise_xor(to_add, i)

    for i in range(power):#adding the right locationall parity bits
        if (to_add >> i & 1 == 1):
            package[2**i] = 1
    
    parity_index0 = np.sum(package) % 2 #adding parity to the whole message
    package[0] = parity_index0
   
    return package


def format_message(msg): #only makes it in "human readable" format(works)

    if np.log2(len(msg)) != int(np.log2(len(msg))):
        print("forgot fault protection!!!")
        return 0        

    shape = (int(np.sqrt(len(msg))),int(np.sqrt(len(msg))))
    msg = np.reshape(msg,shape)
    return msg

def flip_bit(msg): #msg = fault protected message, this function flips 1 or 2 random bits
    number_of_bitflips = random.choice([1,2])
    for i in range(number_of_bitflips):
        flip_index = random.randint(0, len(msg)-1)
        msg[flip_index] = not msg[flip_index]
    return msg #can allso return 0 bitflips as the same can be flipped twise

def fault_correction(msg):
    fault_index = 0

    for i in range(len(msg)):#calculating fault index
        if msg[i] == 1:
            fault_index = np.bitwise_xor(fault_index, i)
    
    msg[fault_index] = not msg[fault_index]#correcting fault
    

    message_parity = np.sum(msg)%2
    print(message_parity)
    if fault_index == 0 and message_parity == 0:
        print("There was no fault")
        return(msg)

    elif fault_index != 0 and message_parity == 0:
        print("fault detected and corrected")
        return(msg)
    
    else:
        print("there were two errors")
        return 0






msg = create_message(pow)
print(msg)

msg = fault_protect(msg)
print(msg)

formatted_msg = format_message(msg)
print(formatted_msg,"\n")


"""msg = flip_bit(msg)#flip a bit
formatted_msg = format_message(msg)
print(formatted_msg, "\n")"""

fault_corrected_msg = fault_correction(msg)
if type(fault_corrected_msg) == np.ndarray:
    print(format_message(fault_corrected_msg))



