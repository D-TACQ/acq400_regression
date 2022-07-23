# acq400_regression

## install

### Prerequisites:

1. python3, numpy, matplotlib
2. HP33210 FG (other FG's may work with the same commands, or, write your own)

```
mkdir PROJECTS
cd PROJECTS
git clone https://github.com/D-TACQ/acq400_hapi.git
pushd acq400_hapi; . ./setpath; popd
git clone https://gitub.com/D-TACQ/acq400_regression.git
cd acq400_regression
```

## example operation: hammer PREPOST

run 1000 shots, pre_post test, default PRE=1M, POST=1M
The FG (sig_gen generates start and event triggers at the appropriate times)
One channel is offloaded each shot and compared with model.
The loop is aborted on first error.
Watch progress concurrently on cs-studio.
Program plots data at end of loop or first fail.

```
./regression_test_suite.py --test='pre_post' --trg='1,0,1' --event='1,0,1' --sig_gen_name='sg0138' --channels=[[1]] --demux=1 --loops=1000 acq1001_084
```

typical output:

```
pre_post
Triggering now.
pre 8192 elapsed 8192
pre 57344 elapsed 57344
pre 98304 elapsed 98304
pre 303104 elapsed 303104
pre 507904 elapsed 507904
pre 712704 elapsed 712704
pre 958464 elapsed 958464
pre 999424 elapsed 999424
pre 1040384 elapsed 1040384
pre 1048576 elapsed 1081344
pre 1048576 elapsed 1286144
./results/ACQ423ELF/ACQ1001_TOP_09_09_32B/acq1001_084_2207231352/pre_post_101_101
Data comparison result: True
 Can't access SPAD when demux = 1. If SPAD analysis is required please set demux = 0. 
Test successful. Test number:  902 
TIMING:func:'run_test_iteration' took: 36.44 sec

```



