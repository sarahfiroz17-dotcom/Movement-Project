# VEBITA — Shared Benchmark Framework

**VEBITA** (Vectorized Evaluation Benchmark for Integrated Tracking Algorithms) is a collaborative research platform for benchmarking **511 machine learning algorithms** applied to animal movement data (GPS biologging telemetry from [Movebank](https://www.movebank.org)).

It enables fair, reproducible comparison of algorithms across a 6-person team without each member needing to build their own evaluation pipeline.

---

## Project Structure

```
vebita_framework/
├── core/
│   ├── base.py            # BaseAlgorithm abstract class + AlgoResult dataclass
│   ├── registry.py        # Singleton AlgorithmRegistry + @registry.register decorator
│   ├── data_pipeline.py   # GPS data loading, feature extraction, train/test split
│   ├── benchmark.py       # Parallel BenchmarkRunner (joblib)
│   └── evaluator.py       # Service-specific metric computation
├── services/
│   ├── example_algorithms.py   # 15 reference implementations (all 6 services)
│   └── TEMPLATE_algorithm.py   # Copy-paste template for new algorithms
├── results/               # Benchmark output CSVs (git-ignored)
├── run_benchmark.py       # CLI entry point
├── requirements.txt
└── README.md
```

---

## The 6 Services

Each service corresponds to a distinct movement-analysis task. Every team member contributes algorithms to their assigned service.

| # | Service | Task | Metrics | Team Member | Algorithms |
|---|---------|------|---------|-------------|-----------|
| S1 | Time Series | Speed/altitude forecasting, trend analysis | MAE, RMSE, R² | Abdul Rehman | ~85 |
| S2 | Pattern Recognition | Trajectory clustering, motif discovery | ARI, NMI | Ritikha | ~85 |
| S3 | Environmental Factors | Habitat correlation, barrier detection | Pearson r, Spearman r, R² | Sarah | ~85 |
| S4 | Anomaly Detection | Outlier and irregular movement detection | Precision, Recall, F1, AUC-ROC | Arshan | ~85 |
| S5 | Trajectory Segmentation | Behavioral state segmentation | Accuracy, F1-macro, ARI | Dua | ~85 |
| S6 | Behavioral Classification | Supervised behavior labeling | Accuracy, F1-macro, F1-weighted | Syeda Hiba | ~86 |

**Total: 511 algorithms**

---

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd vebita_framework

# Create virtual environment
python -m venv vebita_env
source vebita_env/bin/activate   # Windows: vebita_env\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Running the Benchmark

```bash
# Run all 511 algorithms across all 6 services (synthetic red_kite data)
python run_benchmark.py

# Run only one service
python run_benchmark.py --service 5

# Use a specific animal profile with more GPS points
python run_benchmark.py --animal wolf --points 2000

# Load real Movebank CSV data
python run_benchmark.py --csv /path/to/movebank_data.csv

# Control parallelism
python run_benchmark.py --jobs 4

# Custom output path
python run_benchmark.py --output results/my_run.csv
```

Results are saved to `results/benchmark_results.csv` and a leaderboard is printed to the terminal.

---

## Adding a New Algorithm

1. Copy `services/TEMPLATE_algorithm.py` into your service folder:
   ```
   services/s{X}_{yourname}/{yourname}_algorithms.py
   ```

2. Implement the class:
   ```python
   from core.base import BaseAlgorithm
   from core.registry import registry

   @registry.register
   class MyAlgorithm(BaseAlgorithm):
       name       = "My Algorithm Name"
       service_id = 5          # your service number (1–6)
       category   = "clustering"
       library    = "scikit-learn"
       animals    = ["red_kite", "wolf"]
       description = "Brief description of what this algorithm does."

       def fit(self, X, y=None):
           # train on X (numpy array, shape [n_samples, 8 features])
           return self

       def predict(self, X):
           # return predictions as numpy array
           return predictions
   ```

3. Import your file in `run_benchmark.py`:
   ```python
   import services.s5_yourname.yourname_algorithms
   ```

Your algorithm is now automatically discovered, benchmarked, and added to the leaderboard.

---

## Data & Features

The pipeline generates or loads GPS tracks and computes **8 movement features** per point:

| Feature | Description |
|---------|-------------|
| `speed_ms` | Instantaneous speed (m/s) via Haversine distance |
| `altitude_m` | GPS altitude in metres |
| `turning_angle` | Direction change between consecutive steps (radians) |
| `straightness` | Path straightness index (0 = tortuous, 1 = straight) |
| `speed_roll_mean` | Rolling mean of speed (window = 5) |
| `speed_roll_std` | Rolling std of speed (window = 5) |
| `step_length_m` | Distance between consecutive GPS fixes (metres) |
| `alt_roll_mean` | Rolling mean of altitude (window = 5) |

Supported synthetic animal profiles: `red_kite`, `black_stork`, `mongolian_gazelle`, `elk`, `wolf`, `brown_bear`, `cheetah`, `white_stork`.

---

## Tech Stack

| Component | Library |
|-----------|---------|
| Data manipulation | NumPy, Pandas |
| ML algorithms | scikit-learn, statsmodels, filterpy |
| Statistics | SciPy |
| Parallelization | joblib |
| API (planned) | FastAPI, Uvicorn |
| Visualization | Matplotlib |

---

## License

Research use only. Contact the project team for redistribution rights.
