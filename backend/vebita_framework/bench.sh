#!/bin/bash
# Safe benchmark runner — limits BLAS thread nesting to prevent segfaults
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export PYTHONIOENCODING=utf-8
python run_benchmark.py "$@"
