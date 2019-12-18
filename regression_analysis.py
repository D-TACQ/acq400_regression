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
            sample_counter.append(extract_sample_counter(data[index], get_agg_chans(uut), uut.nchan()))
            data[index] = data[index].reshape((-1, int(uut.s0.NCHAN)))
            data[index] = data[index][:,np.array(channels[index])-1]

        events.append(get_es_indices(uut, human_readable=1, return_hex_string=1))

    return data, events, sample_counter



def get_ideal_rgm_data(final_len=75000, es_len=1):
    """ 
    Parameter descriptions:
        final_len: Length of the full rtm data.
        es_len:    Number of samples in the ES.
    """

    # create a linear spacing between 0 and 0.5 * pi, where the
    # number of samples is the size of the parameter sin_len.
    x = np.linspace(0, 2 * np.pi, 20000)
    y = np.sin(x)
    
    # Create an array of zeros of size final_len so we can insert
    # the relevant data into it.
    y2 = np.zeros(final_len)

    es = np.array([np.nan]*es_len)

    # Make a list of fractions of a full sine wave.
    pattern = [0.25, 0.75, 0.25, 0.75, 1]
    pos = 0 

    for num, val in enumerate(pattern):

        # Loop over each burst, insert NaN(s) for the event sample
        # and insert a sine wave chunk proportional to the size of the pattern.
        arr_section = np.concatenate((es, y[0:int(val*y.shape[-1])]))

        y2[pos:pos+arr_section.shape[-1]] = arr_section #np.concatenate((es, y))

        pos = pos + arr_section.shape[-1]
    return y2 * 2**15


def get_ideal_rtm_data(final_len=50000, sin_len=5000, es_len=1):
    """
    Parameter descriptions:
        final_len:    Length of the full rtm data.
        sin_len:      Length of each rtm_translen sized block.
        es_len:       Number of samples in the ES.
    """
    # create a linear spacing between 0 and 0.5 * pi, where the
    # number of samples is the size of the parameter sin_len.
    x = np.linspace(0, 0.5 * np.pi, sin_len)
    
    y = np.sin(x)
    
    # Create an array of zeros of size final_len so we can insert
    # the relevant data into it.
    y2 = np.zeros(final_len)

    es = np.array([np.nan]*es_len)
    
    for num, count in enumerate(range(0, int(final_len/sin_len))):
        # Loop over each rtm_translen section and insert NaN(s) for the event sample
        # and insert a sine wave chunk for the samples.
        arr_section = np.concatenate((es, y)) 
        pos = num * arr_section.shape[-1]

        if arr_section.shape[-1] > y2[pos:pos+sin_len].shape[-1] and num == 9:
            arr_section = arr_section[0:y2[pos:].shape[-1]]

        y2[pos:pos+arr_section.shape[-1]] = arr_section #np.concatenate((es, y))

    return y2 * 2**15


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


def get_ideal_data(test, trg, event, data=[], es_len=1):
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
        ideal_data = get_ideal_rtm_data(final_len=data.shape[-1], sin_len=5000, es_len=es_len)
        return ideal_data

    elif test == "rgm":
        ideal_data = get_ideal_rgm_data(final_len=data.shape[-1], es_len=es_len)
        return ideal_data

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
    if test != "rtm" and test != "rgm":
        ideal_data = scale_wave(real_data, ideal_data)
    # size_test_result = size_test(test, trg, event, real_data)
    # if not size_test_result:
    #     print(CRED, "INCORRECT SIZE DETECTED. Test failed.", CEND)
    #     plt.plot(real_data)
    #     plt.plot(ideal_data)
    #     plt.show()
    mask = ~(np.isnan(real_data) | np.isnan(ideal_data))
    data_type = real_data.dtype
    tolerance = np.iinfo(np.int16).max * 0.01 # 1% of max is the tolerance
    
    comparison = np.allclose(real_data[mask], ideal_data[mask], atol=tolerance, rtol=0)
    print("Data comparison result: {}".format(comparison))
    if not comparison:
        print(CRED, "DATA COMPARISON FAILED", CEND)
        plt.plot(real_data)
        plt.plot(ideal_data)
        plt.grid(True)
        plt.show()
        exit(1)
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


def get_es_indices(uut, file_path="default", nchan="default", human_readable=0, return_hex_string=0):
    """
    Returns the location of event samples.

    get_es_indices will pull data from a system by default (it will also
    read in a raw datafile) and reads through the data in order to find the
    location of the event samples. The system will also return the raw
    event sample data straight from the system.

    If human_readable is set to 1 then the function will return the hex
    interpretations of the event sample data. The indices will remain
    unchanged.

    If return_hex_string is set to 1 (provided human_readable has ALSO been
    set) then the function will return one single string containing all of
    the event samples.

    Data returned by the function looks like:
    [  [Event sample indices], [Event sample data]  ]
    """
    # a function that return the location of event samples.
    # returns:
    # [ [event sample indices], [ [event sample 1], ...[event sample N] ] ]
    indices = []
    event_samples = []
    nchan = uut.nchan() if nchan == "default" else nchan
    aichan = int(get_ai_channels(uut))

    if file_path == "default":
        data = uut.read_muxed_data()
        data = np.array(data)
        if data.dtype == np.int16:
            # convert shorts back to raw bytes and then to longs.
            data = np.frombuffer(data.tobytes(), dtype=np.uint32)
    else:
        data = np.fromfile(file_path, dtype=np.uint32)

    if int(uut.s0.data32) == 0:
        nchan = nchan / 2 # "effective" nchan has halved if data is shorts.
        aichan = int(aichan / 2)
    nchan = int(nchan)
    for index, sample in enumerate(data[0::nchan]):
        # if sample == np.int32(0xaa55f154): # aa55
        if sample == np.uint32(0xaa55f154): # aa55
            indices.append(index)
            event_samples.append(data[index*nchan:index*nchan + aichan])


    if human_readable == 1:
        # Change decimal to hex.
        ii = 0
        while ii < len(event_samples):
            if type(event_samples[ii]) == np.ndarray:
                event_samples[ii] = event_samples[ii].tolist()
            for indice, channel in enumerate(event_samples[ii]):
                event_samples[ii][indice] = '0x{0:08X}'.format(channel)
            ll = int(int(len(event_samples[ii]))/int(len(uut.get_aggregator_sites())))
            event_samples[ii] = [event_samples[ii][i:i + ll] for i in range(0, len(event_samples[ii]), ll)]
            ii += 1

        if return_hex_string == 1:
            # Make a single string containing the hex values.
            es_string = ""
            for num, sample in enumerate(event_samples):
                for i in range(len(sample[0])):
                    for x in event_samples[num]:
                        es_string = es_string + str(x[i]) + " "
                    es_string = es_string + "\n"
                es_string = es_string + "\n"
            event_samples = es_string

    return [indices, event_samples]


def get_ai_channels(uut):
    """
    Returns all of the AI channels. This is a more robust way to get the
    total number of AI channels, as sometimes nchan can be set to include
    the scratch pad.
    """
    ai_channels = 0
    site_types = get_site_types(uut)
    for ai_site in site_types["AISITES"]:
        ai_site = "s{}".format(ai_site)
        ai_channels += int(getattr(getattr(uut, ai_site), "NCHAN"))

    return ai_channels


def get_site_types(uut):
    """
    Returns a dictionary with keys AISITES, AOSITES, and DIOSITES with the
    corresponding values as lists of the channels which are AI, AO, and DIO.
    """
    AISITES = []
    AOSITES = []
    DIOSITES = []

    for site in [1,2,3,4,5,6]:
        try:
            module_name = eval('uut.s{}.module_name'.format(site))
            if module_name.startswith('acq'):
                AISITES.append(site)
            elif module_name.startswith('ao'):
                AOSITES.append(site)
            elif module_name.startswith('dio'):
                DIOSITES.append(site)
        except Exception:
            continue

    site_types = { "AISITES": AISITES, "AOSITES": AOSITES, "DIOSITES": DIOSITES }
    return site_types