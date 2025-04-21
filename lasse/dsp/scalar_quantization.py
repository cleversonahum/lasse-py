import matplotlib.pyplot as plt
import numpy as np
import pylab as pl


def ak_quantizer(input, delta, b):
    """
    Assumes the quantizer allocates 2^(b-1) levels to negative output values,
    one levels to '0' and 2^(b-1) - 1 to positive values.
    """
    x = input.ravel()  # create a one-dimensional view of the input array
    # print(x.shape)
    x_q = np.zeros(x.shape, dtype=float)
    x_i = np.zeros(x.shape, dtype=int)
    for i in range(len(x)):
        auxi = x[i] / delta  # Quantizer levels
        # print(auxi.shape)
        auxi = np.round(auxi)  # get the nearest integer
        if auxi > ((2 ** (b - 1)) - 1):
            auxi = (2 ** (b - 1)) - 1  # force a maximum value
        elif auxi < -(2 ** (b - 1)):
            auxi = -(2 ** (b - 1))  # force a minimum value
        auxq = auxi * delta  # get the decoded output already quantized
        x_q[i] = auxq
        x_i[i] = auxi
    x_q = x_q.reshape(input.shape)  # back to the dimension of input array
    x_i = x_i.reshape(input.shape)
    return x_i, x_q


def int_to_bitarray2_numpy_array(xi, num_of_bits):
    N = len(xi)  # assume it's 1D
    num_levels = 2 ** num_of_bits
    out = np.zeros((N, num_levels), dtype=np.uint8)
    for i in range(N):
        out[i, 0 : xi[i]] = 1
    return out


def int_to_bitarray_numpy_array(xi, num_of_bits):
    N = len(xi)  # assume it's 1D
    out = np.zeros((N, num_of_bits), dtype=np.uint8)
    for i in range(N):
        out[i] = np.asarray(int_to_bitarray(xi[i], num_of_bits))
    return out


def int_to_bitarray(n, num_of_bits):
    """
    Convert integer to numpy array of bits 0 and 1 (not strings)
    """
    out = np.zeros((num_of_bits,), dtype=np.uint8)
    mask = 1
    for i in range(num_of_bits):
        out[num_of_bits - 1 - i] = mask & n
        n = n >> 1
    return out


def bitarray_to_int(bitarray):
    """
    Convert numpy array of bits 0 and 1 (not strings) into integer
    """
    num_of_bits = len(bitarray)
    out = np.uint64(0)
    for i in range(num_of_bits):
        factor = bitarray[num_of_bits - 1 - i] << i
        out += factor
    return out


class UniformQuantizer:
    def __init__(self, num_bits, xmin, xmax, forceZeroLevel=False):
        self.num_bits = num_bits
        M = 2 ** num_bits  # number of quantization levels

        # Choose the min value such that the result coincides with Matlab Lloyd's
        # optimum quantizer when the input is uniformly distributed. Instead of
        # delta=abs((xmax-xmin)/(M-1)) #as quantization step use:
        self.delta = abs((xmax - xmin) / M)  # quantization step
        self.quantizerLevels = (
            xmin + (self.delta / 2.0) + np.arange(M) * self.delta
        )  # output values
        if forceZeroLevel:
            raise Exception("forceZeroLevel == True not correctly implemented yet")
            # np.nonzero plays the role of Matlab's find
            isZeroRepresented = np.nonzero(self.quantizerLevels == 0)  # is 0 there?
            # isZeroRepresented is a tuple, check its first (and only) element
            if isZeroRepresented[0].size == 0:  # zero is not represented yet
                min_abs = np.min(np.abs(self.quantizerLevels))
                # take in account that two levels, say -5 and 5 can be minimum
                minLevelIndices = np.nonzero(np.abs(self.quantizerLevels) == min_abs)[
                    0
                ]  # get first element of tuple
                # make sure it is the largest, such that there are more negative
                # quantizer levels than positive
                closestInd = minLevelIndices[-1]  # end
                closestToZeroValue = self.quantizerLevels[closestInd]
                self.quantizerLevels = self.quantizerLevels - closestToZeroValue
                # xmin = quantizerLevels(1) #update levels
                # xmax = quantizerLevels(end)

        self.xminq = np.min(self.quantizerLevels)  # keep to speed up quantize()
        self.xi_max_index = (2 ** self.num_bits) - 1

    def get_quantizer_levels(self):
        return self.quantizerLevels

    def get_partition_thresholds(self):
        # average consecutive quantizer levels
        partitionThresholds = 0.5 * (
            self.quantizerLevels[0:-2] + self.quantizerLevels[1:-1]
        )
        return partitionThresholds

    def quantize_numpy_array(self, x):
        # Note that x_i has values from 0 to (2^b)-1.
        x_i = np.array((x - self.xminq) / self.delta)  # quantizer levels
        x_i = np.round(x_i)  # nearest integer
        x_i[x_i < 0] = 0  # impose minimum
        x_i[x_i > self.xi_max_index] = self.xi_max_index  # impose maximum
        x_q = x_i * self.delta + self.xminq  # quantized and decoded output
        return x_q, x_i.astype(np.int64)
    
    def dequantize_numpy_array(self, x_i):
        x_q = x_i.astype(np.float32) * self.delta + self.xminq  # decoded output
        return x_q

    # AK-TODO: merge quantize_real_scalar and quantize_numpy_array
    def quantize_real_scalar(self, x):
        # Note that x_i has values from 0 to (2^b)-1.
        x_i = (x - self.xminq) / self.delta  # quantizer levels
        x_i = np.round(x_i)  # nearest integer
        if x_i < 0:
            x_i = 0  # impose minimum
        if x_i > self.xi_max_index:
            x_i = self.xi_max_index  # impose maximum
        x_q = x_i * self.delta + self.xminq  # quantized and decoded output
        return x_q, int(x_i)


class OneBitUniformQuantizer(UniformQuantizer):
    def __init__(self, threshold=0):
        # call superclass constructor
        num_bits = 1
        xmin = np.finfo(np.float64).min
        xmax = np.finfo(np.float64).max
        UniformQuantizer.__init__(self, num_bits, xmin, xmax)
        self.threshold = threshold

    def quantize(self, x):
        return x > self.threshold


if __name__ == "__main__":
    num_bits = 3
    xmin = -4
    xmax = 2
    uniformQuantizer = UniformQuantizer(num_bits, xmin, xmax, forceZeroLevel=True)
    print(uniformQuantizer.quantizerLevels)

    # quantize scalar
    x = -1.4
    xq, xi = uniformQuantizer.quantize_real_scalar(x)
    print(xq, xi)

    # convert to bits
    num_bits = 8
    print(int_to_bitarray(xi, num_bits))

    # quantize array
    x = -1.4 * np.ones((3, 2))
    xq, xi = uniformQuantizer.quantize_numpy_array(x)
    print(xq, xi)
    # prepare to convert to bit
    y = xi.flatten().astype(np.int64)
    z = int_to_bitarray_numpy_array(y, num_bits)
    print(z)
    num_bits = 4
    z2 = int_to_bitarray2_numpy_array(y, num_bits)
    print(z2)
