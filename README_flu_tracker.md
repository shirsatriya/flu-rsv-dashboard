# Flu & RSV Hospital Admissions Tracker

An interactive dashboard that tracks weekly flu and RSV hospital admissions for every US state, using official CDC data that updates automatically each week.

**Live dashboard:** https://flu-rsv-tracker.streamlit.app

## What it shows

- **Headline numbers:** national admissions for the latest week, the change from the week before, how many states are rising, and the current season's peak so far.
- **State map:** admissions by state for any week, as a total or per 100,000 residents, with a slider to move through time.
- **Flu vs RSV:** both diseases on one chart for any selected state.
- **Season comparison:** each respiratory season overlaid on the same timeline, so the current season can be compared with past ones.
- **Fastest-rising states:** the states with the largest week-over-week increases.

## Data sources

- **Hospital admissions:** CDC National Healthcare Safety Network (NHSN) weekly hospital respiratory data, accessed through the [Delphi Epidata API](https://cmu-delphi.github.io/delphi-epidata/) at Carnegie Mellon University.
- **Population:** US Census Bureau 2024 state population estimates, used to calculate rates per 100,000 residents.

The dashboard fetches new data each time it loads (cached for one hour). If the API is unavailable, it falls back to a saved copy in `flu_rsv_backup.csv`.

## Methods

- CDC epidemiological weeks are converted to the Saturday each week ends on.
- Rates are calculated as weekly admissions divided by state population, times 100,000.
- Respiratory seasons are defined as running from August 1 to July 31.
- A state counts as "rising" if admissions grew more than 10% from the previous week and it had at least 5 admissions the week before, which filters out noise from very small numbers.

## Limitations

- **Reporting lag:** each week's data arrives about 6–7 days after the week ends, and the most recent week is often revised upward as late reports come in.
- **Voluntary reporting period:** hospital reporting was voluntary between May and October 2024, so data from that period is less complete. RSV counts from before November 2024 are especially undercounted.
- **Small populations:** in states with small populations, such as Alaska or Wyoming, a few extra admissions can cause large swings in per-100k rates.
- **Confirmed cases only:** the data counts laboratory-confirmed admissions, so it reflects hospital burden rather than total infections in the community.

## Running it locally

```
pip install -r requirements.txt
streamlit run app.py
```

## Files

- `app.py`: the Streamlit dashboard
- `requirements.txt`: Python libraries needed to run it
- `flu_rsv_backup.csv`: saved data used if the live API is unavailable
- `01_explore_data.ipynb`: notebook used to explore the data before building the dashboard
