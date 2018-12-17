#!/usr/bin/env bash
mkdir -p SQUAD
cd ./SQUAD
wget https://rajpurkar.github.io/SQuAD-explorer/dataset/train-v1.1.json
wget https://rajpurkar.github.io/SQuAD-explorer/dataset/dev-v1.1.json
wget https://github.com/allenai/bi-att-flow/raw/master/squad/evaluate-v1.1.py
cd ..
