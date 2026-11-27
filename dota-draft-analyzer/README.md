# Dota Match Analyzer

[Русская версия](README.ru.md)

A study ML project that estimates a team's win probability before the match and at minute five. It covers Practical Task 6 and SIS-3: scikit-learn, FastAPI, Uvicorn, Docker, Streamlit, MLflow Tracking and the MLflow Model Registry. The two modes use independent historical datasets and separate models.

The Streamlit interface is in English by default. Use the **Language / Язык** selector at the top right to switch to Russian, or open `http://localhost:8501/?lang=ru`. Values already entered are kept when the language changes. API messages are in English.

## Minute-five mode

On the first tab, pick five Radiant and five Dire heroes and fill in **each team's totals over its five players at 5:00**: gold/net worth, XP, last hits, kills, deaths, levels and number of item purchases. Gold is the value of the heroes with their items, not unspent gold. Items is the number of purchases during the first five minutes, not the number of occupied slots. Missing stats stay empty and block the prediction. The "Load example stats" button fills in a real record from the training split; it is not a quality check.

Source: the YASP/Coursera dataset of 97,230 matches described in the [original assignment](https://github.com/romovpa/kaggle-dota2-contest). The CSV comes from an [open mirror](https://github.com/nikkuper/coursera-dota-2) with a pinned commit and SHA-256 in data/early/SOURCE.json. Attribution and the CC BY-SA 4.0 license are in data/early/ATTRIBUTION.md. The UCI data is not merged with this CSV: the two have no reliable common identifier.

| On the same temporal test set of 14,585 matches | Heroes only | Heroes + first 5 minutes |
|---|---:|---:|
| Accuracy | 58.16% | **68.97%** |
| ROC AUC | 0.6069 | **0.7547** |

That is +10.82 percentage points on the same sample. The earlier 60.37% refers to a different dataset (UCI) and cannot be compared with 68.97% directly. At minute five the model has more information, so the task is different from a pre-match prediction.

Split of the new dataset: the first 70% by start_time is fit, the next 15% is validation, the last 15% is the final Test. Ties are ordered by match_id. IDs are unique, so one match never ends up in two parts. The source dataset slightly shifts timestamps for anonymisation, so this is the order of the published timestamps rather than the exact real chronology. The final model is chosen by validation ROC AUC and then refit on the first 85%. The comparison covers a baseline, two heroes-only models, three Logistic Regressions with stats and two HistGradientBoosting variants. The Test set takes no part in the selection.

Features: 113 signed hero indicators, 14 team totals and 7 differences between the teams; numeric features are standardised on the training part only. An explicit allowlist excludes radiant_win, duration, the final tower_status/barracks_status, match_id and start_time. Other columns in the CSV are not used either. The source dataset only contains matches lasting at least 15 minutes; this is a property of the sample, not a guarantee for an arbitrary modern match.

Training: `python train_early.py`. It saves models/early_model.joblib and models/early_metrics.json, writes a separate experiment **Dota Minute Five**, registers **DotaMinuteFiveClassifier** and sets the alias champion. The existing draft model is kept. Restart the API after training. If the CSV is missing, `python download_early_data.py` downloads the pinned mirror and checks its SHA-256.

API for this mode:

- GET /early/metadata — available heroes, examples without the outcome, comparison results.
- GET /early/health — readiness of the minute-five model.
- POST /predict/early — a snapshot with snapshot_seconds=300 and two objects, radiant and dire. Each contains heroes (5 IDs) and the required non-negative integers gold, xp, lh, kills, deaths, level, items. Unknown heroes, duplicates, missing fields, end-of-match fields and any other time are rejected.

Minimal PowerShell example with a real Train record:

```powershell
$meta = Invoke-RestMethod http://localhost:8000/early/metadata
$body = $meta.examples[0] | ConvertTo-Json -Depth 5
Invoke-RestMethod http://localhost:8000/predict/early -Method Post -ContentType application/json -Body $body
```

## Data and limitations

Source: [Stephen Tridgell, Dota2 Games Results, UCI, 2016](https://archive.ics.uci.edu/dataset/367/dota2+games+results), [DOI](https://doi.org/10.24432/C5W593), CC BY 4.0 license. The CSV files are included in `data/` unchanged. The data was collected on 13 August 2016 over two hours. This is a historical study prototype; the model does not assess the current meta and knows nothing about player skill, items, lanes or match events.

The CSV files **have no header**. Each of the 117 columns is: outcome (+1/-1), cluster ID, game mode code, game type code, then 113 hero indicators. +1 means a hero of team A, -1 a hero of team B, 0 means the hero is absent. Each side has exactly five heroes. The labels A/B are used because the UCI description does not confirm which side is Radiant and which is Dire. Hero names use the familiar English spelling and keep the Valve ID. IDs 24 and 108, which never appear in Train, are hidden from the interface. An ID is not the row number in the list.

92,650 Train matches, 10,294 Test matches. The outcome and cluster ID are excluded from the inputs. Game mode and game type codes are treated as categories, hero indicators are passed as numbers. Modern game mode names are not substituted without confirmation.

## Quick start on Windows

Python 3.12 is required. Open a terminal **in the project folder**. `requirements.txt` automatically applies `constraints-tested.txt` with the versions of every dependency in the tested environment; pywin32 is limited to Windows:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe train.py
.\.venv\Scripts\python.exe train_early.py
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

In another terminal in the same folder:

```powershell
.\.venv\Scripts\python.exe -m streamlit run frontend.py
```

In a third terminal, to browse experiments and the Registry:

```powershell
.\.venv\Scripts\python.exe -m mlflow ui --backend-store-uri sqlite:///tracking/mlflow.db --host 127.0.0.1 --port 5000
```

- Interface: http://localhost:8501
- API and liveness check: http://localhost:8000/
- Swagger: http://localhost:8000/docs
- MLflow: http://localhost:5000

`models/model.joblib` and `models/metrics.json` are created by train.py; `models/early_model.joblib` and `models/early_metrics.json` by train_early.py. Both trained models are included in the repository, so you can skip retraining to run the API. To create an MLflow history on another computer, run training again: local MLflow storage uses paths of the current machine.

## Docker

For an automated check on Windows after installing Docker Desktop, run `./verify-docker.ps1`. It uses separate ports and docker-state/, runs training and tests inside containers and saves the real status to docker-evidence/. After a successful build and training you can repeat only the service checks with `./verify-docker.ps1 -Resume`: it recreates the containers, checks HTTP readiness and that the API version matches the champion in the Registry. First-time Windows setup is described in [DOCKER-SETUP.md](DOCKER-SETUP.md). If Docker or WSL is not installed yet, the script returns BLOCKED instead of pretending the check succeeded.

You need a running Docker Desktop with Linux containers. From the project folder:

```powershell
docker compose build
docker compose run --rm train
docker compose run --rm train-early
docker compose up -d --force-recreate api frontend mlflow
docker compose ps
```

Training runs as a separate service, not on every request and not during the image build. `data`, `models`, `tracking` and `mlruns` are mounted as volumes. Training in Docker creates an MLflow history with container paths. To check both the local Windows version and the container version, use separate copies of the project or separate `tracking`/`mlruns` folders: SQLite with absolute paths does not move between operating systems automatically.

```powershell
docker compose logs api
docker compose down
```

To run only the API from the image after training:

```powershell
docker run --rm -p 127.0.0.1:8000:8000 --mount "type=bind,source=$($PWD.Path)/models,target=/app/models,readonly" dota-draft-analyzer:local
```

## Querying the model

`POST /predict`:

```json
{
  "team_a": [1, 2, 3, 4, 5],
  "team_b": [6, 7, 8, 9, 10],
  "game_mode": 2,
  "game_type": 2
}
```

The response contains `team_a_probability`, `team_b_probability`, `predicted_winner`, the model name and version, and a note about the historical data. The probabilities add up to 1. The model uses a 0.5 threshold. The probabilities are classifier estimates and are not guaranteed to be strictly calibrated.

In PowerShell:

```powershell
$body = @{team_a=@(1,2,3,4,5); team_b=@(6,7,8,9,10); game_mode=2; game_type=2} | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/predict -Method Post -ContentType application/json -Body $body
```

## Pick advisor

The **Pick advisor** section suggests the next hero for a partially finished draft. Enter the heroes picked so far (any number, even none), choose the team that picks next and press **Suggest picks**. The **Pick** button next to a suggestion adds that hero to the team, so a whole draft can be built step by step. Nothing is retrained: the advisor uses the same registered draft model.

How it works (recommend.py):

1. Every free hero is tried as the next pick of the chosen team.
2. The model needs a complete 5v5 draft, so the remaining empty slots are filled with random free heroes 50 times and the probabilities are averaged (Monte Carlo). All candidates share the same random fill-ins, which reduces noise in their differences. If the candidate completes the draft, the estimate is exact.
3. Heroes are ranked by the averaged win probability. "vs random pick" compares it with the average over all candidates, i.e. with a random next pick.
4. Because the model is a logistic regression with pair features, every suggestion is explained by its weights in log-odds: the hero's own strength, synergy with picked allies and match-ups against picked enemies. A test checks that these weights add up exactly to the model's change in log-odds.

`POST /recommend`:

```json
{"team_a": [1, 2, 3], "team_b": [6, 7, 8, 9], "side": "team_a", "game_mode": 2, "game_type": 2, "top": 5}
```

The response contains `recommendations` (hero, `win_probability`, `delta`, `hero_strength`, `reasons`), `random_pick_probability`, `exact` and `samples`. Duplicates, unknown heroes, a full team for `side` and more than five heroes per team are rejected with HTTP 422. A request takes about 0.1 seconds.

Limitations: the model learned from 2016 matches and its ROC AUC is 0.64, so suggestions are dominated by heroes that won often then, and differences of 1–2 points are within noise. This is the model's opinion, not advice for the current meta.

`GET /metadata` returns the available heroes, game modes, quality metrics and version. `GET /health` returns 503 if the model is not loaded. Without a model, `/` and `/docs` stay available. Restart the API after the first training. The ten heroes must be unique; unknown IDs, extra fields and non-integer values are rejected with HTTP 422.

## Training and honest evaluation

1. The CSV format, missing values, value encodings and team sizes are checked.
2. 20% of Train groups are set aside for validation with seed 42. Matches with identical features fall into the same group, so they are not duplicated between fit and validation. Grouping can shift the class proportion slightly.
3. The comparison covers a constant-probability baseline, Logistic Regression with C=0.1 and C=1, Random Forest and four regularised models with pair features. Pair features encode ally pairs (plus for A, minus for B) and hero match-ups (the sign flips when the sides are swapped). No player names or outcomes are used to build them. The main features are scaled 10× relative to the pairs so that rare combinations are regularised more strongly. Selection is by validation ROC AUC. If the complex models do not beat the baseline, the baseline can win.
4. The winner is refit on the full Train set. Only then is the final result computed on the original Test set.
5. The report includes accuracy, precision, recall, F1, ROC AUC, log loss, Brier score, the confusion matrix, a comparison with the baseline and the Train/Test feature overlap. Metrics on Test rows without overlap are reported separately if such rows exist. F1 is computed for a win by A: a baseline that always picks A can have a higher F1 while separating the classes poorly. That is why model selection relies on ROC AUC and the evaluation uses several metrics.
6. The SHA-256 of both source CSV files, the training date and the full input feature order are saved.

Each model creates a separate validation run in MLflow. The final run contains the final parameters, metrics, the model artifact, the JSON report and the plots `plots/roc_curve.png` and `plots/confusion_matrix.png` on Test (for minute five, also `plots/draft_only_*` for the heroes-only model). The model is registered as `DotaDraftClassifier`, gets an automatically increasing version and the alias `champion`.

### Loading the model from the Registry

By default the API loads the exported `models/*.joblib` file once at startup. If you set `MODEL_URI` and/or `EARLY_MODEL_URI`, the API loads the model from the MLflow Model Registry — the version the alias points to — and the metadata from `metrics.json` of the same run:

```powershell
$env:MODEL_URI = "models:/DotaDraftClassifier@champion"
$env:EARLY_MODEL_URI = "models:/DotaMinuteFiveClassifier@champion"
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

You can also pin a specific version: `models:/DotaDraftClassifier/2`. `GET /` shows where the model was loaded from (`model_source`); the version number is in `GET /metadata` and in the `/predict` response. To roll back or roll out another version, move the `champion` alias in the MLflow UI and restart the API. Hot reloading without a restart is not claimed.

Version 2 uses pair features: on the same official Test set, accuracy rose from 59.724% to 60.365% and ROC AUC from 0.63458 to 0.64399. That is 66 more correct predictions out of 10,294 matches. The gain is small: the exact McNemar test gives p≈0.052, so a stable improvement on other matches is not yet proven. The Test set had already been used for the v1 report; for the improvement, parameters were chosen strictly on Train/validation, and then one selected variant was checked on the same fixed Test set.

`python train.py --basic` reproduces the original comparison without pair features. `python tune.py` runs an additional search over boosting, pair features and an MLP on Train only, saves JSON and does not replace the API model. Results of the completed search are saved in `models/improvement_search.json` and `models/improvement_extended.json`.

## Checks

After training:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The tests check that training and API features match on a real match, the HTTP result with the real saved model, `/docs`, input errors, an unavailable model, the hero list, loading the champion version from the Registry, and the pick advisor (exact last pick, mirrored drafts, weight explanations, invalid requests). The checks actually performed and the metrics are in `VALIDATION.md` (in Russian).

## Structure

```text
data/                  source Train and Test
models/                model.joblib and metrics.json
train.py               training, evaluation and MLflow Registry
common.py              shared feature contract
draft_features.py      ally pairs and counterpicks without target data
tune.py                model search on Train only
heroes.py              hero names by ID
main.py                FastAPI
frontend.py            Streamlit client
early_ui.py            minute-five stats form
recommend.py           pick advisor: Monte Carlo scoring and weight explanations
advisor_ui.py          pick advisor section
i18n.py                interface texts in English and Russian
early_features.py      allowlist and transforms for the new dataset
train_early.py         independent training and comparison on one temporal Test
download_early_data.py verified download of the new CSV
tests/                 contract, API and Registry tests
Dockerfile             API image
compose.yaml           training, API, UI and MLflow
requirements.txt       pinned direct dependencies
```

## What to show at the defense

Open the interface, load an example and get a prediction. Change one hero and recompute. Show that picking the same hero twice is rejected. In the pick advisor, load the example draft, get suggestions, explain the weights and press Pick to continue the draft. Switch the language to show both versions of the interface. Open Swagger and send a POST request. On the quality tab, compare the baseline with the trained models. In MLflow, show the validation runs, the final run, its parameters, metrics, plots, the model and its version in the Registry. Explain the limitations of the historical data and the Train/validation/Test split.

Do not add the local `tracking/`, `mlruns/` folders or the virtual environment to Git.
