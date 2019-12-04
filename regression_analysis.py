#!/usr/bin/env python

"""
This file contains the functions used for analysis in the acq400_regression test
suite.
"""

import numpy as np
import matplotlib.pyplot as plt
import time


CRED = "\x1b[1;31m"
CGREEN = "\x1b[1;32m"
CYELLOW = "\x1b[1;33m"
CBLUE = "\x1b[1;34m"
CEND = "\33[0m"


def get_data(uuts, args, channels):
    data = []
    sample_counter = []
    events = []

    for index, uut in enumerate(uuts):
        if args.demux == 1:
            data.append(np.column_stack((uut.read_channels(tuple(channels[index])))))
            # sample_counter.append()
        else:
            data.append(uut.read_channels((0), -1)[0])
            print(data)
            # sample_counter.append(regression_analysis.extract_sample_counter(data[index], regression_analysis.get_agg_chans(uut), uut.nchan()))
            sample_counter.append(extract_sample_counter(data[index], get_agg_chans(uut), uut.nchan()))
            data[index] = data[index].reshape((-1, int(uut.s0.NCHAN)))
            data[index] = data[index][:,channels[index]]

            # print(data[0].shape)
            # sample_counter.append(regression_analysis.extract_sample_counter(data[index], int(uut.get_ai_channels()), uut.nchan()))
        events.append(uut.get_es_indices(human_readable=1, return_hex_string=1))

    return data, events, sample_counter


def get_soft_trg_ideal(data):
    """
    Forms a perfect sine wave for a soft trigger run. Takes the channel data
    as an argument so that the first zero crossing can be found, and the starting
    position in radians can be calculated. With this info the sine wave can be
    generated.
    """
    # wave = np.zeros(len(data))
    data = data - np.mean(data)
    zero_crossings = np.where(np.diff(np.sign(data)))[0]
    first_zc = zero_crossings[0]
    crossing_pos = 0 if (data[first_zc-40] < 0 and data[first_zc+40] > 0) else np.pi

    start_pos = crossing_pos - ((first_zc)/20000) * 2*np.pi
    x = np.linspace(start_pos, start_pos + 10*np.pi, 100000)
    y = np.sin(x)
    return y


def get_post_ideal_wave(trg, wave_length=20000, full_length=100000, data=[]):
    """
    A function that returns the ideal waves for each trigger type in the POST
    config.
    """
    x = np.linspace(0, 2 * np.pi, wave_length)
    y1 = np.sin(x)
    y2 = np.zeros(full_length)

    if trg == [1,0,0]:
        ideal_wave = y2
    elif trg == [1,0,1]:
        y2[0:wave_length] = y1
        ideal_wave = y2
    elif trg == [1,1,1]:
        ideal_wave = get_soft_trg_ideal(data)

    return ideal_wave


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


def get_ideal_data(test, trg, event, data=[]):
    """
    Returns the ideal data for the scenario, based on the test, the trigger
    and the event types.
    """
    if test == "post":
        ideal_data = get_post_ideal_wave(trg, data=data, full_length=data.shape[-1])
        return ideal_data

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
    real_data = real_data - np.mean(real_data)
    real_max = np.amax(real_data)
    real_min = np.amin(real_data)

    scaled_data = ideal_data * ((real_max - real_min) / 2)

    return scaled_data


def compare(real_data, ideal_data, test, trg, event):
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
    # size_test_result = size_test(test, trg, event, real_data)
    # if not size_test_result:
    #     print(CRED, "INCORRECT SIZE DETECTED. Test failed.", CEND)
    #     plt.plot(real_data)
    #     plt.plot(ideal_data)
    #     plt.show()
    comparison = np.allclose(real_data, ideal_data, atol=1000, rtol=0)
    print("Data comparison result: {}".format(comparison))
    if not comparison:

        plt.plot(real_data)
        plt.plot(ideal_data)
        plt.show()
        # exit(1)
    return comparison


def check_sample_counter(sample_counter, test="pre_post"):
    """
    Checks that the sample counter is equal to a newly constructed array where
    each element is one greater than the last. If yes return True, else find
    the gaps and append to a file.
    """

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
            exit(1)
        return big_diffs


def extract_sample_counter(data, aichan, nchan):
    """
    Take piece of raw data and get the sample counter from it.
    Note that - aichan is the physical channel count and nchan includes spad.
    """
    data = np.array(data)
    if data.dtype == np.int16:
        data = np.frombuffer(data.tobytes(), dtype=np.uint32)
        sample_counter = data[int(aichan/2)::int(nchan/2)]
    else:
        sample_counter = data[nchan::nchan]

    return sample_counter


def pre_post_anomaly_detect():
    from sklearn.ensemble import IsolationForest
    # s =
    return None


def get_agg_chans(uut):
    """
    Returns the number of channels contained in the sites in the aggregator.
    """
    channels = 0
    agg_sites = uut.s0.aggregator.split(" ")[1].split("=")[1].split(",")
    agg_sites = [int(s) for s in agg_sites]
    for site in agg_sites:
        channels = channels + int(getattr(getattr(uut, "s{}".format(site)), "NCHAN"))

    return int(channels)


def size_test(test, trg, event, wave):
    """
    Checks the size of a wave based on the specific test that is being run.
    """
    if test == "post":
        if trg == [1,0,0]:
            size = 0
        else:
            size = 2**15

        if np.amax(wave) < size - 1000 or np.amax(wave) > size:
            return False
        else:
            return True
    else:
        return True


def check_config(args, uut):

    # time.sleep(2)
    trg = uut.s1.trg.split(" ")[0].split("=")[1].split(",")
    trg = [ int(num) for num in trg ]
    if trg != args.trg:
        print(CYELLOW, "Trigger not taken!", CEND)
        print("Trigger is: {}, should be: {}".format(trg, args.trg))
        exit(1)

    if args.test != "post" and args.test != "rgm":
        print(args.test)
        event = uut.s1.event0.split(" ")[0].split("=")[1].split(",")
        event = [ int(num) for num in event ]
        if event != args.event:
            print(CYELLOW, "Event not taken!", CEND)
            print("Event is: {}, should be: {}".format(event, args.event))
            exit(1)
    return None


def test_info(args, uuts):
    """
    A function to store information about the test to a file.
    Information stored:

    - Hostname.
    - Firmware
    - FPGA.
    - list-sites.
    - Tests run.
    - Time.
    """
    for uut in uuts:
        hostname = "Hostname: " + uut.s0.HN
        # firmware = uut.s0.FW
        fpga = "FPGA: " + uut.s0.fpga_version
        software_version = "FW Version: " + uut.s0.software_version
        aggregator = "Aggregator: " + uut.s0.aggregator
        test_time = "Time: " + time.asctime()
        run_count = "Loops of each test run: " + str(args.loops)

        sites = []
        string_to_print = ''

        for num, site in enumerate(uut.s0.sites.split(",")):
            MODEL = getattr(getattr(uut, "s{}".format(site)), "MODEL")
            PART_NUM = getattr(getattr(uut, "s{}".format(site)), "PART_NUM")
            SERIAL = getattr(getattr(uut, "s{}".format(site)), "SERIAL")
            sites.append("Sites: \n{}, {}, {}, {}".format(site, MODEL, PART_NUM, SERIAL))


        string_to_print = string_to_print + "{}\n\n" * (6+len(sites))
        string_to_print = string_to_print.format(test_time, run_count, hostname, fpga, \
            software_version, aggregator, *(site for site in sites))
        string_to_print = string_to_print + "\n----------------------\n"
    print(string_to_print)

    dir = "./results/{}/".format(MODEL)
    import os
    if not os.path.exists(dir):
        os.makedirs(dir)

    import datetime
    file = open(dir + fpga.split(" ")[1] + "_" + datetime.datetime.now().strftime("%y%m%d%H%M"), "a")
    file.write(string_to_print)
    file.close()
    return None

