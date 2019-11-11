#!/usr/bin/env python

"""
This file contains the functions used for analysis in the acq400_regression test
suite.
"""

import numpy as np
import matplotlib.pyplot as plt


CRED = "\x1b[1;31m"
CGREEN = "\x1b[1;32m"
CYELLOW = "\x1b[1;33m"
CBLUE = "\x1b[1;34m"
CEND = "\33[0m"


def get_post_ideal_wave(trg):

    if trg == [1,0,0]:
        ideal_wave = 1
    elif trg == [1,1,0]:
        ideal_wave = 2
    elif trg == [1,1,1]:
        ideal_wave = 3

    return None


def get_pre_post_ideal_wave(polarity=0, wave_length=20000, full_length=150000):
    """
    Returns a np array of scale 1, which contains a perfect pre_post array,
    with either a falling edge trigger or rising edge trigger.
    Rising has the sine wave in the 100k post section, falling edge has the
    sine wave in the 50k pre section.

    polarity arg:  Either 1 or 0, corresponding to falling (0) or rising (1).
    length arg:    The length of the sine wave in samples.
    """

    x = np.linspace(0, 2 * np.pi, wave_length)
    y1 = np.sin(x)

    y2 = np.zeros(full_length)
    if polarity == 1:
        y2[50000:70000] = y1
    else:
        y2[30000:50000] = y1

    return y2


def get_ideal_data(test, trg, event):
    """
    Returns the ideal data for the scenario, based on the test, the trigger
    and the event types.
    """
    if test == "post":
        ideal_data = get_post_ideal_wave(trg)
        return None

    elif test == "pre_post":
        ideal_data = get_pre_post_ideal_wave(polarity=event[2])
        return ideal_data

    elif test == "rtm":
        return None

    elif test == "rgm":
        return None

    elif test == "rtm_gpg":
        return None

    return ideal_data


def scale_wave(real_data, ideal_data):
    """
    Returns a wave that is scaled to the max of another. This is useful for
    scaling the array returned by get_pre_post_ideal_wave.
    """
    real_max = np.amax(real_data)

    scaled_data = ideal_data * real_max
    scaled_data = scaled_data.astype(np.int16)

    return scaled_data


def compare(real_data, ideal_data):
    """

    """
    if type(ideal_data) is not np.ndarray:
        print("Data analysis not available for this capture mode yet.")
        return True

    if real_data.shape[-1] != ideal_data.shape[-1]:
        print("Data passed to this function is not the correct shape.")
        print("Shape of real_data should be {} and is actually {}."
        .format(ideal_data.shape[-1], real_data.shape[-1]))


    # print(real_data.shape)
    # fake_data = real_data
    # real_data.setflags(write=1)
    # fake_data = np.zeros(150000, dtype=np.int16)
    # real_data[10000] = 5000

    ideal_data = scale_wave(real_data, ideal_data)
    comparison = np.allclose(real_data, ideal_data, atol=40, rtol=0)
    print("Data comparison result: {}".format(comparison))
    if not comparison:

        plt.plot(ideal_data)
        plt.plot(real_data)
        plt.show()
        # exit(1)
    return comparison


def check_sample_counter(sample_counter, test="pre_post"):
    """
    Checks that the sample counter is equal to a newly constructed array where
    each element is one greater than the last. If yes return True, else find
    the gaps and append to a file.
    """

    # ideal_sample_counter = np.arange(sample_counter.shape[-1])
    # sample_counter = sample_counter - sample_counter[0]
    # print(sample_counter)
    # print(ideal_sample_counter)
    # comparison = np.allclose(sample_counter, ideal_sample_counter)
    #
    # if not comparison:
    #     diffs = sample_counter - ideal_sample_counter
    #     discontinuity_sizes = np.nonzero(diffs)[0]
    #     print("Discontinuity found in the sample counter of size {}".format(discontinuity_sizes))

    diffs = np.diff(sample_counter)
    # if np.count(diffs, 1) == diffs.shape[-1]:
    if np.all(diffs < 2):
        return []
    else:
        # diffs = diffs[diffs != 1]
        big_diffs = []
        for pos, diff in enumerate(diffs):
            if diff == 1:
                continue
            if pos == 49999 and test == "pre_post":
                continue
            else:
                big_diffs.append((pos,diff))
        if len(big_diffs) != 0:
            print(CRED, "Discontinuities in sample counter detected: {}".format(big_diffs), CEND)
        return big_diffs


def extract_sample_counter(data, aichan, nchan):
    """
    Take piece of raw data and get the sample counter from it.
    Note that - aichan is the physical channel count and nchan includes spad.
    """
    data = np.array(data)
    if data.dtype == np.int16:
        data = np.frombuffer(data.tobytes(), dtype=np.uint32)
        print(nchan)
        sample_counter = data[int(aichan/2)::int(nchan/2)]
    else:
        sample_counter = data[nchan::nchan]

    return sample_counter


def pre_post_anomaly_detect():
    from sklearn.ensemble import IsolationForest

    return None

