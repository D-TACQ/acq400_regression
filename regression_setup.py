"""
This file contains the functions used for setup in the acq400_regression test
suite.
"""

import numpy as np
import matplotlib.pyplot as plt
import time


def configure_post(uut, role, trigger=[1,1,1], post=100000):
    """
    Configure UUT for a regular transient capture. Default: internal soft
    trigger starts the capture.

    "Role" is a mandatory argument. For master systems, role should be the
    string "master", if the system is a slave then role should be the string
    "slave"

    Default post samples: 100k.
    """

    uut.s0.transient = "PRE=0 POST={} SOFT_TRIGGER={}".format(post, trigger[1])


    slave_trigger = trigger.copy()
    slave_trigger[1] = 0
    trigger = ' '.join([str(elem) + ',' for elem in trigger])
    slave_trigger = ' '.join([str(elem) + ',' for elem in slave_trigger])

    uut.s1.trg = trigger if role == "master" else slave_trigger
    # trg = uut.s1.trg

    uut.s1.event0 = '0,0,0'
    uut.s1.rgm = '0,0,0'
    uut.s0.SIG_EVENT_SRC_0 = 0

    return None


def configure_pre_post(uut, role, trigger=[1,1,1], event=[1,1,1], pre=50000, post=100000):
    """
    Configure UUT for pre/post mode. Default: soft trigger starts the
    data flow and trigger the event on a hard external trigger.

    "Role" is a mandatory argument. For master systems, role should be the
    string "master", if the system is a slave then role should be the string
    "slave"

    Default pre trigger samples: 50k.
    Default post trigger samples: 100k.
    """
    if pre > post:
        print("PRE samples cannot be greater than POST samples. Config not set.")
        return None
    trg = 1 if trigger[1] == 1 else 0
    uut.s0.transient = "PRE={} POST={} SOFT_TRIGGER={}".format(pre, post, trg)

    slave_trigger = trigger.copy()
    slave_trigger[1] = 0
    trigger = ' '.join([str(elem) + ',' for elem in trigger])
    slave_trigger = ' '.join([str(elem) + ',' for elem in slave_trigger])

    event = ' '.join([str(elem) + ',' for elem in event])

    uut.s1.trg = trigger if role == "master" else slave_trigger
    uut.s1.event0 = event
    uut.s1.rgm = '0,0,0'

    uut.s0.SIG_EVENT_SRC_0 = 0
    return None


def configure_rtm(uut, role, trigger=[1,1,1], event=[1,1,1], post=50000, rtm_translen=5000, gpg=0):
    """
    Configure UUT for rtm mode. Default: external trigger starts the capture
    and takes 5000 samples, each subsequent trigger gives us another 5000
    samples.

    "Role" is a mandatory argument. For master systems, role should be the
    string "master", if the system is a slave then role should be the string
    "slave"

    Default rtm_translen: 5k samples.
    Default post: 50k samples

    GPG can be used in RTM mode as the Event. If you are using the GPG
    then this function can put the GPG output onto the event bus (to use as
    an Event for RTM).
    """
    uut.s0.transient = "PRE=0 POST={}".format(post)
    uut.s1.rtm_translen = rtm_translen

    slave_trigger = trigger.copy()
    slave_trigger[1] = 0
    trigger = ' '.join([str(elem) + ',' for elem in trigger])
    slave_trigger = ' '.join([str(elem) + ',' for elem in slave_trigger])

    event = ' '.join([str(elem) + ',' for elem in event])

    uut.s1.trg = trigger if role == "master" else slave_trigger

    uut.s1.event0 = event

    uut.s1.rgm = '3,0,1'

    uut.s0.SIG_EVENT_SRC_0 = 1 if gpg == 1 else 0

    return None

def configure_rgm(uut, role, trigger=[1,0,1], event=[1,1,1], post="100000", gpg=0):
    """
    Configure UUT for RGM mode. Default: external trigger starts the capture
    and the system takes samples every clock whenever the trigger is high.

    "Role" is a mandatory argument. For master systems, role should be the
    string "master", if the system is a slave then role should be the string
    "slave"

    Default post: 100k samples.

    GPG can be used in RGM mode as the Event. If you are using the GPG then
    this function can put the GPG output onto the event bus (to use as an
    Event for RGM).

    """
    uut.s0.transient = "PRE=0 POST={}".format(post)

    slave_trigger = trigger.copy()
    slave_trigger[1] = 0
    trigger = ' '.join([str(elem) + ',' for elem in trigger])
    slave_trigger = ' '.join([str(elem) + ',' for elem in slave_trigger])

    uut.s1.trg = trigger if role == "master" else slave_trigger

    uut.s1.event0 = '0,0,0'

    uut.s1.rgm = '2,0,1'

    uut.s0.SIG_EVENT_SRC_0 = 1 if gpg == 1 else 0

    return None


def incr_axes(fig, plt_count):
    """
    A function that returns the axes after creating a new plot inside them.
    """

    n = len(fig.axes)
    for ii in range(n):
        fig.axes[ii].change_geometry(plt_count,1,ii+1)
    return fig