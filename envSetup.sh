#!/usr/bin/env bash

#install conda
# wget https://repo.anaconda.com/archive/Anaconda2-5.3.1-Linux-x86_64.sh

# install py3.5 environment
conda create -n py3.5 python=3.5
source activate py3.5
pip install -r requirements.txt
