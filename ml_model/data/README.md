# ml_model/data/ — Dataset Directory

Place your downloaded CSV files in this directory before training.

## Required Files

| File | Download Source | Description |
|------|----------------|-------------|
| `spam.csv` | [Kaggle SMS Spam Collection](https://www.kaggle.com/datasets/uciml/sms-spam-collection-dataset) | SMS spam detection (5,574 messages) |
| `phishing_site_urls.csv` | [Kaggle Phishing URLs](https://www.kaggle.com/datasets/taruntiwarihp/phishing-site-urls) | URL phishing dataset |

## Setup Steps

1. Create a free account at https://www.kaggle.com
2. Download both datasets and place the CSV files here
3. Run training: `python ml_model/train.py`

> **Note:** If dataset files are not found, the training script will automatically
> generate a synthetic dataset so you can still run a full training cycle.
