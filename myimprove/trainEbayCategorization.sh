#!/usr/bin/env bash


# Test MRPC classifiler
export DATA_DIR=./ebayCatData/
python run_slClassify.py \
  --task_name eBayCat \
  --do_train \
  --do_eval \
  --do_lower_case \
  --data_dir $DATA_DIR \
  --bert_model bert-base-uncased \
  --max_seq_length 128 \
  --train_batch_size 32 \
  --learning_rate 2e-5 \
  --num_train_epochs 10.0 \
  --output_dir ./ebaycat_output/

