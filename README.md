# Legal Monitor

This project provides a small utility that periodically queries public
APIs from [Ekosystém Slovensko.Digital](https://ekosystem.slovensko.digital/)
for new submissions relating to bankruptcies, restructurings and
liquidations.  It filters the results for companies whose names
contain a user-provided search query and sends an email notification
whenever such records appear.

## Data sources

The Slovensko.Digital data hub exposes several endpoints under the
`ov` (Obchodný vestník) namespace.  We use the following endpoints
documented on the *Otvorené API* page:

| Dataset | Purpose | Endpoint | Notes |
|-------|---------|----------|------|
| **konkurz_restrukturalizacia_issues** | Bankruptcy/restructuring proposals | `GET …/ov/konkurz_restrukturalizacia_issues/:id` with a synchronisation variant `…/ov/konkurz_restrukturalizacia_issues/sync` | The API returns details about court proposals for bankruptcy or restructuring, including debtor information, proposers and headings【333368336233229†L687-L768】. |
| **konkurz_vyrovnanie_issues** | Progress in bankruptcy/settlement proceedings | `GET …/ov/konkurz_vyrovnanie_issues/:id` | Records include the corporate body name and a description of the announcement【333368336233229†L770-L799】. |
| **likvidator_issues** | Liquidator submissions | `GET …/ov/likvidator_issues/:id` with a synchronisation variant `…/ov/likvidator_issues/sync` | Returns announcements from liquidators, including the corporate body name and other details such as the court and decision dates【333368336233229†L866-L927】. |

All of these datasets support a synchronisation endpoint (the `/sync`
suffix) that accepts a `since` timestamp and returns only records
created or updated after the given ISO‑8601 time.  When more than one
page of results is available, the response includes a `Link` header
pointing to the next page【333368336233229†L762-L768】.

## Components

### `monitor.py`

This module contains the core logic:

* **`fetch_changes`** — calls the `/sync` endpoint for a dataset,
  follows pagination via the `Link` header and returns a list of
  records.
* **`fetch_items_from_last_n_days`** — helper that fetches all items
  from a given dataset for the last *n* days.
* **`record_contains_novis`** — inspects a record and checks
  whether the debtor’s or corporate body name contains `NOVIS`.
* **`filter_records_for_novis`** — filters a list of records to those
  relevant to the query.
* **`send_email`** — uses the [Resend Python SDK](https://resend.com/docs/send-with-python) to send a formatted HTML email
  summarising the matching records.  API credentials are read from
  environment variables.
* **`perform_update`** — orchestrates the whole update: fetches
  changes since a timestamp, filters them and triggers an email
  notification.

When executed directly (`python monitor.py`), the module reads a
timestamp from `last_run.txt`, defaults to 30 days ago if missing,
runs an update and saves the current timestamp back to the file.

### `streamlit_app.py`

Provides a minimal web interface using [Streamlit](https://streamlit.io/):

* Shows the time of the last update run.
* Offers a **Run update** button to trigger a manual check.
* Displays a JSON summary of the run, including how many records were
  fetched and how many matched.

To launch the app:

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

### `requirements.txt`

Lists the Python dependencies: `requests`, `resend` and `streamlit`.

## Configuration

The monitor uses the Resend email service. Before running it you
must set the following environment variables:

* **`RESEND_API_KEY`** – Your Resend API key.
* **`RESEND_FROM_EMAIL`** – A verified sender email in your Resend account.

Optional monitor-specific variables:

* **`MONITOR_TO_EMAILS`** – Comma-separated recipient list.
  Defaults to `RESEND_TO_EMAIL` (if set) or `kzvolsky@novis.eu`.
* **`MONITOR_KEYWORDS`** – Comma-separated keywords (for example: `NOVIS,Novis`).
  The monitor runs the check for each keyword and deduplicates results.
* **`MONITOR_DAYS_BACK`** – Number of days to look back (default: `5`).
* **`MONITOR_SEARCH_MODE`** – `full_text` (default), `targeted`, or `combined`.

When matches are found, the email includes attachments:

* Word template (`docs/legal_monitor_template.docx`)
* PDF preview (`docs/legal_monitor_template_preview.pdf`)
* Generated XLSX report (`novis_matches.xlsx`) with the matching records


## Scheduling

The project does not include a built‑in scheduler to avoid blocking
the Streamlit interface. Deployments are expected to schedule the
update task using external tools such as `cron`, `systemd` timers or
task queues.

To run every hour and check the last 5 days for `NOVIS`/`Novis`, add:

```cron
0 * * * * cd /path/to/novis_legal_monitor && \
  RESEND_API_KEY=your_key \
  RESEND_FROM_EMAIL=alerts@your-domain.tld \
  MONITOR_TO_EMAILS=kzvolsky@novis.eu \
  MONITOR_KEYWORDS=NOVIS,Novis \
  MONITOR_DAYS_BACK=5 \
  python monitor.py >> monitor.log 2>&1
```

You can edit only the env values (`MONITOR_TO_EMAILS`, `MONITOR_KEYWORDS`,
`MONITOR_DAYS_BACK`) without changing code.


## Railway deployment (UI + hourly monitor)

Yes — the Streamlit UI flow stays unchanged. The UI calls monitor functions
directly (for manual runs, filters, exports), while the cron job runs
`python monitor.py` in a separate service/process.

Recommended Railway setup:

1. **UI service** (existing): runs Streamlit app, e.g.
   `streamlit run streamlit_app.py --server.port $PORT --server.address 0.0.0.0`
2. **Cron service** (new): same repo, same variables, start command can be simple
   (`sleep infinity`) because schedule triggers override command execution.

### Create the cron in Railway

In Railway dashboard:

1. Open your project and click **New Service** → **GitHub Repo**.
2. Select this same repository.
3. Name it e.g. `legal-monitor-cron`.
4. Set environment variables on this cron service:
   - `RESEND_API_KEY`
   - `RESEND_FROM_EMAIL`
   - `MONITOR_TO_EMAILS` (example: `kzvolsky@novis.eu`)
   - `MONITOR_KEYWORDS` (example: `NOVIS,Novis`)
   - `MONITOR_DAYS_BACK` (example: `5`)
   - optional `MONITOR_SEARCH_MODE` (`full_text`, `targeted`, `combined`)
5. Add a schedule/cron trigger with expression: `0 * * * *` (every hour).
6. Set scheduled command to: `python monitor.py`.
7. Save and run once manually to verify logs and email delivery.

This keeps administration via env vars only, while end users continue using the
UI with all existing capabilities.

## Limitations

* The Slovensko.Digital API is rate‑limited and may return multiple
  pages of results.  The monitor follows the `Link` header but stops
  when an error status is encountered.
* Records that contain `NOVIS` in a different field (e.g. nested
  within free‑form text) are not detected.  Only debtor names,
  proposers’ names and top‑level corporate names are checked.
* The application sends plain HTML emails; no attachments or rich
  formatting beyond simple tables are included.  Resend domain
  verification is required before emails can be delivered.

## License

This example is provided for educational purposes and does not
constitute legal advice.  Use at your own risk.