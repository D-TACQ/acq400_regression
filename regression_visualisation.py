#!/usr/bin/env python


import os
import matplotlib.pyplot as plt 
import numpy as np
import regression_setup


def get_data_from_dirs_list(dirs):
    data = []
    all_tests = ["post", "pre_post", "rtm", "rtm_gpg", "rgm"]
    fig = plt.figure()
    plt_count = 1
    for test in all_tests:

        gen = (dir for dir in dirs if dir.split("/")[-2].startswith(test))
        for dir in gen:
            if dir.split("/")[-2].startswith("rtm_gpg") and test == "rtm":
                continue
            files = [dir + "/" + name for name in os.listdir(dir)]
            for file in files:
                
                fig = regression_setup.incr_axes(fig, plt_count)
                axs = fig.add_subplot(plt_count,1,plt_count)
                plt_count += 1
                plt.plot(np.fromfile(file, dtype=np.int16))
                plt.title(file.split("/")[-3])
        
        plt.show()
        fig = plt.figure()
        plt_count = 1
        continue

    return data



def get_file_list(directory):
    file_list = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            filePath = os.path.join(root, file)
            file_list.append(filePath)
    return file_list
    

def view_last_run(args, uut):
    directories = args.directories.copy()
    dirs = [directories[0] + "/" + name + "/" for name in os.listdir(directories[0])]
    data = get_data_from_dirs_list(dirs)
    return None

