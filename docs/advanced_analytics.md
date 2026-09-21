# Advanced Decision-Support Analytics

## Governed outputs

The pipeline loads `data/raw/meter_consumption.csv` at the grain of **one meter, closed billing interval, and source reading**. It persists normalized meter activity in `fact_meter_consumption`; `dim_meter` retains the governed meter, site, utility-account, and energy-type relationship.

| Output | Purpose |
| --- | --- |
| `analytics_meter_anomaly` | Persisted, traceable robust-anomaly calculation at one meter-consumption fact row. |
| `v_meter_anomaly` | Business-facing anomaly output with meter/site/account context and baseline evidence. |
| `v_bill_meter_variance` | Invoice-versus-meter reconciliation at site × utility account × energy type × exact billing interval. |

## Method and thresholds

For each meter interval, the pipeline assesses only earlier intervals for the same meter. It requires at least six prior periods, then calculates:

`robust_z = 0.6745 × (current kWh − trailing median kWh) / trailing MAD kWh`

An absolute robust-z score above **3.5** is an anomaly (`anomaly_high` or `anomaly_low`). This median/MAD approach is deliberately robust to an isolated extreme reading. Records with fewer than six prior periods are labelled `insufficient_history`; a zero-MAD baseline is explicitly labelled rather than silently divided by zero.

Bill-versus-meter variance is `(billed kWh − metered kWh) / metered kWh`. Exact period, site, account, and energy-type matching is required. Values with absolute variance over **5%** are `variance_high`; missing matches are `meter_missing`.

## Assumptions and limitations

- The source supplies interval consumption, not cumulative register reads. Cumulative reads require rollover and read-quality handling before use.
- The single meter/account mapping is stable for the interval. Meter replacement, shared meters, and allocation logic need effective-dated mapping before production rollout.
- Exact billing periods are used; shifted utility cycles can correctly appear as a missing match and need a governed alignment rule.
- A robust score identifies unusual consumption, not its cause. Weather, occupancy, operating hours, planned shutdowns, and estimated reads should be reviewed before operational action.
- The committed synthetic dataset contains a deliberately extreme September meter interval to exercise detection; it is not a business incident.
