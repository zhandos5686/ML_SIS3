# Attribution and dataset license

The early-game dataset is derived from the YASP 3.5 Million Data Dump, credited to Albert Cui, Howard Chung and Nicholas Hanson-Holtry (yasp.co, now OpenDota). The original contest description identifies the underlying dump license as **CC BY-SA 4.0**.

- Original task and data description: https://github.com/romovpa/kaggle-dota2-contest/blob/master/ContestDescription.ipynb
- Original feature extraction definition: https://github.com/romovpa/kaggle-dota2-contest/blob/master/extract_features.py
- Public CSV mirror: https://github.com/nikkuper/coursera-dota-2
- Pinned commit and checksum: SOURCE.json
- License text: https://creativecommons.org/licenses/by-sa/4.0/

The CSV is supplied unchanged from that pinned mirror. Derived example snapshots and aggregate data in this project retain attribution and CC BY-SA 4.0. This notice concerns the dataset and derivatives; it does not assign a license to unrelated project source code.

The source covers matches described as May–December 2015, at least 15 minutes long. Start timestamps were deliberately perturbed in the original task, so the split follows the provided timestamp order rather than an exact real-world chronology. Feature values are cut off at 300 seconds. Final-match duration, outcome and building status columns remain in the source CSV but are excluded by an explicit feature allowlist. Label radiant_win is used only as the target.
