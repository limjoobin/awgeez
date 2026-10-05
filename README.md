# AWGEEZ

## What is AWGEEZ?

AWGEEZ (Are We Gonna mEasure Everyone’s disappointment and minimiZe the worst?) is an interactive experiment in stable one-to-one matching. It builds preference rankings from 21 waves of the [Columbia Speed Dating dataset](https://www.kaggle.com/datasets/annavictoria/speed-dating-experiment) and compares Gale–Shapley with an optimizer that minimizes the worst assigned partner rank. A matching can be stable while still giving someone a partner near the bottom of their list; AWGEEZ explores how much that worst outcome can be improved.

The **Stable Matching Explorer** dashboard shows the possible and chosen matches, compares disappointment across the methods, and lets you follow what happens as matched pairs leave the pool over repeated rounds.

## Quick start

Docker Compose handles the dataset, Redis, ingestion, and dashboard. You need Docker with Compose; the first run needs internet access for the images and CSV.

```bash
docker compose up --build -d
```

Open [http://localhost:8000](http://localhost:8000). To stop the app, run `docker compose down`. The dataset and Redis data stay in Docker volumes, so later starts can reuse them. Only the dashboard is exposed on port 8000.

## Methodology

### Preference rankings

We process each wave separately. A date enters someone's preference list when they gave it a `like` rating, even if their historical `dec` response was 0. Missing `like` ratings are left out, and the historical `match` outcome is not used.

We sort each person's dates by `like`, highest first. When two dates tie, we use their ratings for attractiveness, sincerity, intelligence, fun, ambition, and shared interests, weighted by what that person said mattered to them before the event. The weights are normalized to sum to one. If a tied group lacks complete ratings or weights, we order that group by candidate `iid` instead; equal weighted scores use `iid` too. This makes the preference lists deterministic. The [dataset codebook](https://web.mit.edu/17.871/www/2009/speed_dating_codebook.pdf) describes the fields.

### Bipartite matching

For each wave, we put the M participants on one side and the F participants on the other, following the dataset's gender codes 1 and 0. A line joins two people only when **both rated each other**. That line is a possible match, and each person gives it a rank based on their own preferences. The two ranks can be different.

A matching picks some of those lines, at most one per person. The unpicked lines still matter: if two people on one of them would both prefer each other to their assigned partners, the matching is unstable. In the dashboard, faint lines are possible matches and colored lines are the chosen ones.

### Matching methods

We run Gale–Shapley twice, once with M proposing and once with F proposing. The third method uses OR-Tools CP-SAT to find a stable matching with the **lowest possible maximum disappointment**. Once it finds that minimum, it chooses the solution with the lowest total disappointment among those tied on the maximum.

Here, *disappointment* means the rank of a matched person's partner: **1** is their first choice, and larger numbers are less preferred. Unmatched people have no numeric disappointment; they appear in a separate count and are left out of the mean, percentiles, and distribution. All three methods use the same eligible graph, and every result is checked for blocking pairs.

### Repeated rounds

Round 1 includes everyone in the wave. After each round, we draw `ceil(departure rate × matched pairs)` pairs from the minimum-disappointment matching. Both people in each drawn pair leave permanently. A pair's draw weight is `2 / (M rank + F rank)`, so pairs with lower average disappointment are more likely to leave.

A seed keeps the draw reproducible. The three algorithms then run again on the **same remaining pool**. Ranks are recalculated for that pool; moving to a later round changes both the participants and the meaning of a rank. The original preferences in Redis are left untouched.

## Project structure

The path through the app is: **CSV → preference lists → Redis → matching methods → dashboard**. The matching logic is in [src/matching/](src/matching/), data preparation in [src/datasets/](src/datasets/), metrics in [src/evaluation/](src/evaluation/), and the interface in [web/](web/). [tests/](tests/) contains unit tests and small-instance checks of the optimizer.

The scripts are the glue:

- [download_speed_dating.py](scripts/download_speed_dating.py) downloads and checks the CSV, unless a valid copy is already present.
- [ingest_speed_dating.py](scripts/ingest_speed_dating.py) builds preference lists and stores the selected waves in Redis.
- [run_experiment.py](scripts/run_experiment.py) runs and evaluates the three matching methods.
- [visualization_data.py](scripts/visualization_data.py) builds each requested round from the stored graph.
- [serve_ui.py](scripts/serve_ui.py) serves the dashboard and connects it to the Python computation.

## Interpreting results

These ranks come from self-reported ratings, so they describe fairness **under the preferences we constructed**. They are not a measure of real-world compatibility. Compare methods within the same wave and round; later rounds have fewer people and newly calculated ranks.
