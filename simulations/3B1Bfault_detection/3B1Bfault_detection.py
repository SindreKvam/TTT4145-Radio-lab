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
    flipped_msg = np.copy(msg)
    number_of_bitflips = random.choice([1,2])

    for i in range(number_of_bitflips):
        flip_index = random.randint(0, len(flipped_msg)-1)
        flipped_msg[flip_index] = not flipped_msg[flip_index]

    return flipped_msg #can allso return 0 bitflips as the same can be flipped twise

def fault_correction(msg):
    fault_index = 0

    for i in range(len(msg)):#calculating fault index
        if msg[i] == 1:
            fault_index = np.bitwise_xor(fault_index, i)
    
    message_parity = np.sum(msg) % 2
    if (message_parity == 1):
        msg[fault_index] = not msg[fault_index]#correcting fault
        #print("error fixed one error")
        return msg, 0
    
    elif (message_parity == 0 and fault_index != 0):
        #print("there were two errors")
        return None, 1
    
    else:
        #print("there were no errors")
        return msg, 2



def sick_test_script(power):
    test_result = np.array([0,0,0])

    for i in range(10000):
        msg = create_message(power)
        protected_message = fault_protect(msg)
        bit_flipped_massege = flip_bit(protected_message)
        corrected_msg, index = fault_correction(bit_flipped_massege)
        test_result[index] += 1

        if index != 1:
            if (protected_message.all() != corrected_msg.all()):
                print("ERROR something is really wrong")
                print("protected message is = \n", format_message(protected_message),"\n")
                print("fault corrected message is = \n", format_message(corrected_msg))
                return 0

    
    print(test_result)
    return 1

sick_test_script(pow)



