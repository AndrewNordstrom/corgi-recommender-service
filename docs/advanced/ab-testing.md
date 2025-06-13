### Creating an Experiment via the Dashboard

The Research Dashboard provides a user-friendly interface for creating and configuring new A/B testing experiments without writing any code.

**Step-by-Step Guide:**

1. **Open the Creation Form** – Navigate to the **A/B Testing** tab in the dashboard and click the **"Create New Experiment"** button. This opens the experiment-creation modal.
2. **Define the Experiment**
   * **Name** – Give your experiment a clear, descriptive name (e.g., *"Algorithm Weighting vs. Engagement Boost"*).
   * **Description** – Briefly explain the hypothesis you are testing.
3. **Configure Variants**
   * The form starts with two variants by default. Use the **"Add Variant"** button to add more.
   * **Model Variant** – For each row, choose the registered model you want to test from the dropdown (fetched live from the Model Registry).
   * **Traffic Allocation** – Assign the percentage of traffic for that variant. The **Total Allocation** display at the bottom turns green when all variants sum to exactly **100 %**.
   * **Remove Variant** – Use the trash-can icon to delete a row.
4. **Launch the Experiment** – After validation passes, click **"Create Experiment"**. The experiment is saved with status **DRAFT** and will appear in the experiment list for activation.

> ![Experiment Creation Modal](./assets/ab-testing-create-experiment.png)

The screenshot above shows a completed two-variant experiment with a 50 % / 50 % split.

## How User Assignment Works

When a user requests recommendations while an experiment is **RUNNING**, the backend executes the following flow:

1. `assign_user_to_variant(user_id)` checks the `ab_experiments` table for the most-recent experiment in `RUNNING` state.
2. If the user already has a row in `ab_user_assignments` for that experiment, the stored `variant_id` is reused to guarantee consistency.
3. Otherwise, a deterministic hash of the `user_id` is mapped against each variant's `traffic_allocation` until a bucket is selected.
4. A new row is inserted into `ab_user_assignments` and an event with `event_type="user_assignment"` is written to `ab_experiment_results`.
5. The selected `variant_id` (identical to the `model_id` in the Model Registry) is forwarded to `generate_rankings_for_user`, ensuring the correct algorithm configuration is applied.

### Schema Quick-Reference

```
ab_user_assignments
 ├─ id               INTEGER  PK
 ├─ user_id          TEXT     (anonymised)
 ├─ experiment_id    INTEGER  FK → ab_experiments.id
 ├─ variant_id       INTEGER  FK → ab_experiment_variants.id
 └─ assigned_at      TIMESTAMP
```

## Analysing Experiment Results

Because every assignment and interaction is recorded, you can reproduce funnels and quality metrics with simple SQL:

```sql
-- Assignment counts per variant
SELECT v.name, COUNT(*) as participants
FROM ab_user_assignments a
JOIN ab_experiment_variants v ON v.id = a.variant_id
WHERE a.experiment_id = 42
GROUP BY v.name;

-- Ranking response-time comparison
SELECT r.variant_id,
       AVG(perf.response_time_ms) AS avg_resp_ms
FROM ab_experiment_results r
JOIN recommendation_performance perf ON perf.request_id = r.request_id
WHERE r.experiment_id = 42
  AND r.event_type = 'recommendation_request'
GROUP BY r.variant_id;
```

For advanced analysis, export `ab_user_assignments` and `ab_experiment_results` into your BI tool of choice or use the supplied Jupyter notebook under `examples/analysis/ab_testing_analysis.ipynb`.

---

Once you have declared a **winner**, use the *Stop* button in the dashboard. The status will switch to **COMPLETED**, freezing assignments but keeping the historical data intact. 