# Forecast results

Walk-forward backtest: train on all years before, test on each year [2019, 2020, 2021, 2022, 2023].

## Next-day PM2.5 (MAE, µg/m³)

| model                          |   MAE |   skill_vs_persistence |   2019 |   2020 |   2021 |   2022 |   2023 |
|:-------------------------------|------:|-----------------------:|-------:|-------:|-------:|-------:|-------:|
| Persistence (today = tomorrow) | 4.171 |                  0     |  4.331 |  4.045 |  4.401 |  4.079 |  3.758 |
| Seasonal climatology           | 5.683 |                 -0.362 |  5.716 |  6.073 |  5.8   |  5.49  |  4.832 |
| Ridge regression               | 3.792 |                  0.091 |  4.45  |  3.679 |  3.721 |  3.553 |  3.219 |
| LightGBM                       | 3.825 |                  0.083 |  4.444 |  3.632 |  3.892 |  3.609 |  3.156 |

## Next-day ozone (MAE, ppb)

| model                          |   MAE |   skill_vs_persistence |   2019 |   2020 |   2021 |   2022 |   2023 |
|:-------------------------------|------:|-----------------------:|-------:|-------:|-------:|-------:|-------:|
| Persistence (today = tomorrow) | 4.726 |                  0     |  4.789 |  4.491 |  4.823 |  4.856 |  4.594 |
| Seasonal climatology           | 5.595 |                 -0.184 |  5.614 |  5.729 |  5.502 |  5.49  |  5.708 |
| Ridge regression               | 4.135 |                  0.125 |  4.115 |  4.025 |  4.281 |  4.266 |  3.781 |
| LightGBM                       | 4.221 |                  0.107 |  4.188 |  4.22  |  4.244 |  4.238 |  4.205 |

## Will tomorrow exceed 25 µg/m³ PM2.5?

| model               |   ROC-AUC |   PR-AUC |   Brier |   recall@0.5 |   precision@0.5 |
|:--------------------|----------:|---------:|--------:|-------------:|----------------:|
| Persistence         |   nan     |  nan     |   0.169 |        0.628 |           0.627 |
| Logistic regression |     0.9   |    0.719 |   0.106 |        0.601 |           0.683 |
| LightGBM            |     0.898 |    0.733 |   0.108 |        0.65  |           0.636 |
