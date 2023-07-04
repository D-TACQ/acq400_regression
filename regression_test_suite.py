#!/usr/bin/env python3


"""
This is a regression test suite that uses a function generator and the onboard
GPG to test UUTs. For more information on regression tests please refer to the
D-TACQ wiki page:

http://eigg-fs:8090/mediawiki/index.php/Products:ACQ400:Regression_Testing

Usage:

python3 regression_test_suite.py --test='all' --sig_gen_name='10.12.196.174' \
--channels=[[1,2]] --demux=0 --show_es=1 acq1001_084

python3 regression_test_suite.py --test='pre_post' --trg='1,0,1' --event='all' \
--sig_gen_name='10.12.196.174' --channels=[[1,2]] --demux=0 --show_es=1 acq1001_084

python3 regression_test_suite.py --test='pre_post' --trg='all' --event='1,0,1' \
--sig_gen_name='10.12.196.174' --channels=[[1,2]] --demux=0 --show_es=1 acq1001_084

"""

from __future__ import print_function
import acq400_hapi
import numpy as np
import os
import time
import argparse
import socket
import matplotlib.pyplot as plt
import sys
import regression_analysis
import regression_setup
import regression_visualisation
import re


import logging
mpl_logger = logging.getLogger('matplotlib')
mpl_logger.setLevel(logging.WARNING)

def create_rtm_stl():
    stl =  "0,f\n \
    10000,0\n \
    20000,f\n \
    30000,0\n \
    40000,f\n \
    50000,0\n \
    60000,f\n \
    70000,0\n \
    80000,f\n \
    90000,0\n \
    100000,f\n \
    110000,0\n \
    120000,f\n \
    130000,0\n \
    140000,f\n \
    150000,0\n \
    160000,f\n \
    170000,0\n \
    180000,f\n \
    190000,0\n \
    200000,f\n \
    210000,0\n \
    220000,f\n \
    230000,0\n \
    240000,f\n \
    250000,0\n \
    260000,f\n \
    270000,0\n \
    280000,f\n \
    290000,0"
    return stl


def create_rgm_stl():
    # An example STL file for regression test purposes.
    stl = "0,f\n \
    5005,0\n \
    20005,f\n \
    35005,0\n \
    40005,f\n \
    45005,0\n \
    60005,f\n \
    75005,0\n \
    80005,f\n \
    350005,0"
    return stl


import enum
class AnsiCol(enum.Enum):
    CRED = "\x1b[1;31m"
    CGREEN = "\x1b[1;32m"
    CYELLOW = "\x1b[1;33m"
    CBLUE = "\x1b[1;34m"
    CCYAN = '\033[36m'
    CEND = "\33[0m"
    def __str__(self):
        return str(self.value)
    def __add__(self, other):
        return str(self)+other


def calculate_frequency(args, uut, divisor):
    # calculate a reasonable frequency from the clock speed of the master uut.
    if args.is_43X:
        clk_freq = (int(float(uut.s1.ACQ43X_SAMPLE_RATE.split(" ")[1])))
    else:
        clk_freq = (int(float(uut.s0.SIG_CLK_S1_FREQ.split(" ")[1])))
    print("\n\nSample Rate = ",clk_freq,"\n\n")
    freq = clk_freq / divisor
    if int(freq) == 0 :
        print("\n\nWarning CLK Frequency reading ZERO!!!\n\n")
        exit()
    return freq


def trigger_system(args, sig_gen, uut):
    if "rtm" not in args.test: # We don't need to generate a trigger for the RTM regression modes
        print("...Begin Trigger process...")
        time.sleep(1) # Be careful. We need to check that we are in ARM before we send this trigger... SO WE SHOULD ACTUALLY CHECK THAT

        if args.trg[1] == 0: # If trigger condition is EXT; send initial trigger to move from ARM to PRE
            print("FIRE!\n")
            sig_gen.send("TRIG\n".encode())

        if args.test == "pre_post": # We need to add a fudge factor to delay trigger generation 
                                    # until "fudge_pp_event_time" after PRE samples have been captured
                                    # See commit cbd37f2082244d2cd7afa5883ff960df18adbf2f
            print("PRE = {}    POST = {}".format(args.pre, args.post))
            olds = None
            while True:
                news = (uut.statmon.get_pre(), uut.statmon.get_elapsed())
                if olds and news != olds:
                    print("pre {} elapsed {}".format(news[0], news[1]))
                if news[1] > news[0]: # Elapsed is greater than PRE
                    time.sleep(args.fudge_pp_event_time) # Wait for "fudge_pp_event_time"
                    break
                olds = news
            time.sleep(0.1)
            print("FIRE!\n")
            sig_gen.send("TRIG\n".encode())

    return None


def config_gpg(uut, args, trg=1):
    # The following settings are very test specific and so they
    # have not been included in a library function.
    uut.s0.gpg_enable = 0
    uut.s0.gpg_clk = "1,2,1" # GPG clock is the same as the site.
    uut.s0.gpg_trg = "1,{},1".format(trg)

    if args.is_43X:
        # We want to use the falling edge of the index pulse from the master
        # site in order to skew the progression of the GPG and the site sampling.
        uut.s0.gpg_sync = "1,2,0"

    uut.s0.gpg_mode = 3 # LOOPWAIT

    if args.test == "rgm":
        stl = create_rgm_stl()
    else:
        stl = create_rtm_stl()
    try:
        uut.load_gpg(stl)
    except Exception:
        print("Load GPG has failed. If you want to use the GPG please make sure")
        print("that the GPG package has been enabled.")
        return False
    uut.s0.gpg_enable = 1
    return True


def configure_sig_gen(sig_gen, args, freq, scale):
    print("Configuring sig gen.")

    sig_gen.send("VOLT {}\n".format(scale).encode())
    sig_gen.send("OUTP:SYNC ON\n".encode())
    freq_string = "FREQ {}\n".format(freq)
    sig_gen.send(freq_string.encode())
    sig_gen.send("FUNC:SHAP SIN\n".encode())

    if args.test == "post":
        if args.trg[1] == 0:
            sig_gen.send("BURS:STAT ON\n".encode())
            sig_gen.send("BURS:NCYC 1\n".encode())
            sig_gen.send("TRIG:SOUR BUS\n".encode())
        elif args.trg[1] == 1:
            sig_gen.send("BURS:STAT OFF\n".encode())
            sig_gen.send("TRIG:SOUR IMM\n".encode())

        if args.trg[2] == 0:
            # If ext falling then we need two sine waves
            print("TRG FALLING set sg")
            sig_gen.send("BURS:STAT ON\n".encode())
            sig_gen.send("BURS:NCYC 3\n".encode())


    if args.test == "pre_post":
        sig_gen.send("BURS:STAT ON\n".encode())
        sig_gen.send("BURS:NCYC 1\n".encode())
        sig_gen.send("TRIG:SOUR BUS\n".encode())

    elif args.test == "rtm" or args.test == "rgm":
        # sig_gen.send("FREQ 1000\n".encode())
        sig_gen.send("TRIG:SOUR IMM\n".encode())
        sig_gen.send("BURS:STAT OFF\n".encode())
        if args.test == "rgm":
            sig_gen.send("BURS:STAT ON\n".encode())
            sig_gen.send("BURS:NCYC 5\n".encode())
            sig_gen.send("TRIG:SOUR BUS\n".encode())
    elif args.test == "rtm_gpg":
        sig_gen.send("TRIG:SOUR IMM\n".encode())
        sig_gen.send("BURS:STAT OFF\n".encode())
        sig_gen.send("FUNC:SHAP RAMP\n".encode())
        sig_gen.send("FREQ 1\n".encode())
    return None


def check_master_slave(args, uut):
    print(uut.s0.HN, uut.s0.sync_role)
    return None


def check_es(events):
    success_flag = True
    for uut_es in events:
        if uut_es == events[0]:
            continue
        else:
            print("\nES location comparison FAILED!\n")
            success_flag = False
            return False
    if success_flag == True:
        print("\nES location comparison successful!\n")

    # import code
    # code.interact(local=locals())
    for index, item in enumerate(events[0][1].split("\n\n")):
        for num, item2 in enumerate(item.split("\n")):
            if num == 0:
                for item3 in item2[0:-1].split(" ")[0:-1]:
                    if not item3.startswith("0xAA55F15"):
                        print(item3)
                        print("Problem found in ES.")
                        success_flag = False
                        return success_flag

    return success_flag


def show_es(events, uuts):
    uut_list = list(range(0, len(uuts)))
    lines = [events[counter][1].splitlines() for counter in uut_list]
    for l in zip(*lines):
        print(*l, sep='')
    for event in events:
        print("{}\n".format(event[0])) # Print indices too!
    return None


def save_data(uuts, data, channels, args):

    directories = args.directories.copy()
    for index, directory in enumerate(directories):
        sub_dir = "{}/{}".format(directory, args.test + "_" + "".join(str(item) for item in args.trg) + "_" + "".join(str(item) for item in args.event))
        directories[index] = sub_dir
        if not os.path.exists(sub_dir):
            os.makedirs(sub_dir)

    for index, uut in enumerate(uuts):
        for num, channel in enumerate(channels[index]):
            channel_data = data[index][:,num]
            print(directories[index])
            channel_data.tofile("{}/{}_ch_{}_data.dat".format(directories[index], args.test, num+1))

    return None


def verify_inputs(args):
    tests = ["post","pre_post", "rtm", "rtm_gpg", "rgm"]
    if args.test not in tests:
        print("Please choose from one of the following tests:")
        print(tests)
        exit(1)
    return None


def custom_test(args, uuts):
    return None


def get_module_voltage(uut):
    """
    Query the module for part_num and check if there is a voltage specified in
    the part_num. If there is a voltage specified then use that, otherwise,
    if the module is an acq48X then use 2.5V, else use 10V.
    """
    part_num = uut.s1.PART_NUM
    if "V" in part_num:
        for item in part_num.split("-"):
            if "V" in item:
                scale = int(item.split("V")[0])
                break
    else:
        if part_num.startswith("ACQ48"):
            scale = 2.5
        else:
            scale = 10
    return scale


def configure_test_iteration(args, uut, is_master):
    if args.test == "pre_post":
        if is_master:
            # regression_setup.configure_pre_post(uut, "master", trigger=args.trg, event=args.event)
            regression_setup.configure_pre_post(uut, "master", trigger=args.trg, event=args.event, pre=args.pre, post=args.post)
        else:
            # uut.s0.sync_role = "slave"
            regression_setup.configure_pre_post(uut, "slave")

    elif args.test == "post":
        if is_master:
            regression_setup.configure_post(uut, "master", trigger=args.trg)
        else:
            regression_setup.configure_post(uut, "slave", trigger=args.trg)

    elif args.test == "rtm":
        if is_master:
            regression_setup.configure_rtm(uut, "master", trigger=args.trg, event=args.event)
        else:
            regression_setup.configure_rtm(uut, "slave")

    elif args.test == "rtm_gpg":
        if is_master:
            regression_setup.configure_rtm(uut, "master", trigger=args.trg, gpg=1, event=args.event)
            if not config_gpg(uut, args, trg=0):            
                print("Breaking out of test {} now.".format(args.test))
                return False
        else:
            regression_setup.configure_rtm(uut, "slave")

    elif args.test == "rgm":
        if is_master:
            regression_setup.configure_rgm(uut, "master", trigger=args.trg, post=75000, gpg=1)
            gpg_config_success = config_gpg(uut, args, trg=0)
            if gpg_config_success != True:
                print("Breaking out of test {} now.".format(args.test))
                return False
        else:
            uut.s0.sync_role = "slave"
            regression_setup.configure_rgm(uut, "slave", post=75000)
    
    regression_analysis.check_config(args, uut)
    return True

@acq400_hapi.timing            
def run_test_iteration(args, uuts, iteration, sig_gen):
    channels = eval(args.channels[0])
    data = []
    events = []
    sample_counter = []
    success_flag = True

    for index, uut in reversed(list(enumerate(uuts))):
        if not configure_test_iteration(args, uut, index==0):
            break

        uut.s0.set_arm
        uut.statmon.wait_armed()

        trigger_system(args, sig_gen, uuts[0])

        for index, uut in enumerate(uuts):
            uut.statmon.wait_stopped()
        data, events, sample_counter = regression_analysis.get_data(uuts, args, channels)

        if args.demux == 0:
            if args.show_es == 1:
                show_es(events, uuts)        
            success_flag = check_es(events)       

        save_data(uuts, data, channels, args)
        for index, data_set in enumerate(data):
            for num, ch in enumerate(channels[index]):
                channel_data = data[index][:, num]
                if args.test == "pre_post":
                    ideal_data = regression_analysis.get_ideal_data(args.test, args.trg, args.event, data=channel_data, pre=args.pre, post=args.post)
                else:
                    ideal_data = regression_analysis.get_ideal_data(args.test, args.trg, args.event, data=channel_data)
                result = regression_analysis.compare(channel_data, ideal_data, args.test, args.trg, args.event)
                if sample_counter != []:
                    spad_test = regression_analysis.check_sample_counter(sample_counter[index], args.test)
                    print("SPAD TEST FAILED!" if spad_test != [] else "SPAD TEST PASSED!")
                elif args.demux == 1:
                    print(AnsiCol.CYELLOW, "Can't access SPAD when demux = 1. If SPAD analysis is required please set demux = 0.", AnsiCol.CEND)

        if args.custom_test == 1:
            custom_test(args, uuts)

        if success_flag == False:
            print(AnsiCol.CRED , "There is a problem with the event samples. Please check them by hand. Exiting now. " , AnsiCol.CEND)
            print("Tests run: ", iteration)
            exit(1)
        else:
            print(AnsiCol.CGREEN + "Test successful. Test number: ", iteration, AnsiCol.CEND)

 
@acq400_hapi.timing
def run_test(args, uuts):
    verify_inputs(args)

    if args.wave_scale == 'auto':
        scale = get_module_voltage(uuts[0])
    args.is_43X = uuts[0].s1.MODEL.startswith("ACQ43")

    sig_gen = socket.socket()
    sig_gen.connect((args.sig_gen_name, 5025))

    if args.config_sig_gen == 1:
        freq = calculate_frequency(args, uuts[0], args.clock_divisor)
        configure_sig_gen(sig_gen, args, freq, scale)

    for iteration in list(range(1, args.loops+1)):
        run_test_iteration(args, uuts, iteration, sig_gen)
        # code.interact(local=locals())
    print(AnsiCol.CBLUE);print("Finished '{}' test. Total tests run: {}".format(args.test, args.loops));print(AnsiCol.CEND)

    return None

def reset_uut(args, uut):
    uut.s0.set_abort
    uut.s0.transient = "DEMUX={}".format(args.demux)
    # check_master_slave(args, uut)
    uut.s0.transient # print transient config
    agg_before = uut.s0.aggregator.split(" ")[1].split("=")[1]
    if args.demux == 0 : # No point in carrying SPAD around when we won't use it from 5300X pull
        uut.s0.spad = '1,2,0'
        uut.s0.run0 = agg_before 

def get_parser():
    desc = "\n\nacq400_regression tests. For argument info run: \n\n" \
    "./regression_test_suite.py -h \n\n" \
    "For Usage examples see below:\n\n" \
    "python3 regression_test_suite.py --test='all' --sig_gen_name='10.12.196.174' " \
    "--channels=[[1,2]] --demux=0 --show_es=1 acq1001_084\n" \
    "\n\n" \
    "python3 regression_test_suite.py --test='pre_post' --trg='1,0,1' --event='all' " \
    "--sig_gen_name='10.12.196.174' --channels=[[1,2]] --demux=0 --show_es=1 acq1001_084\n" \
    "\n\n" \
    "python3 regression_test_suite.py --test='pre_post' --trg='all' --event='1,0,1' " \
    "--sig_gen_name='10.12.196.174' --channels=[[1,2]] --demux=0 --show_es=1 acq1001_084 \n\n"

    if len(sys.argv) < 2:
        print(desc)

    parser = argparse.ArgumentParser(description='regression tests', epilog=desc)

    parser.add_argument('--test', default="pre_post", type=str,
    help='Which test to run. Options are: all, post, pre_post, rtm, rtm_gpg, rgm. \
    Default is pre_post. The "all" option can be used to test every test mode \
    with every trigger mode.')

    parser.add_argument('--trg', default="1,0,1", type=str,
    help='Which trigger to use. Default is 1,0,1. User can also specify \
    --trg=all so that the chosen test will be run multiple times with all \
    trigger types.')

    parser.add_argument('--event', default="1,0,1", type=str,
    help='Which event to use. Default is 1,0,1. User can also specify \
    --event=all so that the chosen test will be run multiple times with all \
    event types.')

    parser.add_argument('--config_sig_gen', default=1, type=int,
    help='If True, configure signal generator. Default is 1 (True).')

    parser.add_argument('--sig_gen_name', default="A-33600-00001", type=str,
    help='Name of signal generator. Default is A-33600-00001.')

    parser.add_argument('--channels', default=['[1],[1]'], nargs='+',
    help='One list per UUT: --channels=[[1],[1]] plots channel 1 on UUT1 and 2')

    parser.add_argument('--clock_divisor', default=20000, type=int,
    help="The speed at which to run the sig gen. 20,000 is human readable and \
    is default.")

    parser.add_argument('--demux', default=1, type=int,
    help="Whether or not to have demux configured on the UUT. Default is 1 \
    (True)")

    parser.add_argument('--show_es', default=1, type=int,
    help="Whether or not to show the event samples when demux = 0. Default is 1\
    (True)")

    parser.add_argument('--loops', default=1, type=int,
    help="Number of iterations to run the test for. Default is 1.")

    parser.add_argument('--custom_test', default=0, type=int,
    help="This argument allows the user to write a custom test in the custom \
    test function. Default is disabled (0).")

    parser.add_argument('--wave_scale', default='auto', type=str,
    help="What scale to make the input wave. Auto is default and any other setting \
    should be of the form '5V'")

    parser.add_argument('--pre', default=99999, type=int, # PREMAX set in bos.sh to 99999 for most systems
    help="set pre length for pre/post")
    
    parser.add_argument('--post', default=1048576, type=int, 
    help="set post length for pre/post")
    
    parser.add_argument('--plot_previous', default=None, 
    help="plot a previous result")
    
    parser.add_argument('--fudge_pp_event_time', default=2, type=int, 
    help="wait a few more seconds before pulling event trigger (this should be randomized)")

    parser.add_argument('uuts', nargs='+', help="Names of uuts to test.")
    return parser


def run_main(args):
    start = time.time()

    all_tests =  ["post", "pre_post", "rtm", "rtm_gpg", "rgm"]
    all_trgs =   [[1,0,0], [1,0,1], [1,1,1]]
    all_events = [[1,0,0], [1,0,1]] # Not interested in any soft events.

    uuts = [acq400_hapi.factory(u) for u in args.uuts]

    for uut in uuts:
        reset_uut(args, uut)
        
    if args.plot_previous:
        args.directories = [ args.plot_previous ]
        regression_visualisation.view_last_run(args, uuts)
        return        

    args.directories = regression_setup.create_results_dir(uuts)

    if args.test.lower() == "all":
        print("You have selected to run all tests.")
        print("Now running each test {} times with ALL triggers " \
                                "and ALL events.".format(args.loops))

        for test in all_tests:
            args.test = test

            for trg in all_trgs:
                args.trg = trg
                if test == 'rgm' and trg != [1,1,1]:
                    continue

                if test == "post": # Don't need any events for post mode.
                    args.event = "NA"
                    # fig = regression_setup.incr_axes(fig, plt_count)
                    print("\nNow running: {} test with" \
                                        " trigger: {}\n".format(test, args.trg))
                    run_test(args, uuts)

                else:

                    for event in all_events:
                        if test == 'rgm':
                            # Only run RGM mode once as trigger and RGM are now
                            # hard coded to 1,1,1 and 2,0,1 respectively
                            # in the setup file. Event is actually redundant in
                            # RGM mode.
                            if event != [1,0,0]:
                                # Skip all but one as explained above.
                                continue
                            else:
                                # This has no effect other than for the graph label
                                # as the event and RGM are hardcoded for RGM mode.
                                event = [2,0,1]

                        args.event = event
                        print("\nNow running: {} test with trigger: {} and" \
                        " event: {}\n".format(test, args.trg, args.event))
                        run_test(args, uuts)

        regression_analysis.test_info(args, uuts)

    elif args.trg == "all" and args.event == "all":

        for trg in all_trgs:
            if args.test == 'rgm' and trg != [1,1,1]:
                continue
            args.trg = trg
            if args.test == "post": # Don't need any events for post mode.
                args.event = "NA"
                print("\nNow running: {} test with" \
                                    " trigger: {}\n".format(args.test, args.trg))
                run_test(args, uuts)
            else:
                for event in all_events:
                    if args.test == 'rgm':
                        # Only run RGM mode once as trigger and RGM are now
                        # hard coded to 1,1,1 and 2,0,1 respectively
                        # in the setup file. Event is actually redundant in
                        # RGM mode.
                        if event != [1,0,0]:
                            # Skip all but one as explained above.
                            continue
                        else:
                            # This has no effect other than for the graph label
                            # as the event and RGM are hardcoded for RGM mode.
                            event = [2,0,1]
                    args.event = event
                    print("\nNow running: {} test with trigger: {} and" \
                    " event: {}\n".format(args.test, args.trg, args.event))
                    run_test(args, uuts)

    elif args.trg == "all":
        args.event = args.event.split(",")
        args.event = [int(i) for i in args.event]
        for trg in all_trgs:
            args.trg = trg
            run_test(args, uuts)

    elif args.event == "all":
        args.trg = args.trg.split(",")
        args.trg = [int(i) for i in args.trg]
        for event in all_events:
            args.event = event
            run_test(args, uuts)

    else:
        test = args.test
        args.trg = args.trg.split(",")
        args.trg = [int(i) for i in args.trg]
        args.event = args.event.split(",")
        args.event = [int(i) for i in args.event]
        run_test(args, uuts)

    print(AnsiCol.CCYAN+"Elapsed time = ",time.strftime('%H:%M:%S', time.gmtime(time.time()-start)),AnsiCol.CEND)

    # regression_analysis.test_info(args, uut)
    regression_visualisation.view_last_run(args, uuts)


if __name__ == '__main__':
    run_main(get_parser().parse_args())
