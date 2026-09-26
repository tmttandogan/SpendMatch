# SpendMatch

**A working MVP for reconciling marketing campaigns and purchase orders.** SpendMatch creates a shared campaign ID, guides category and finance-code entry, lets a reviewer approve links for old records, and reports only verified spend. All sample records are fictional.

## Why it exists

A marketing operations interviewee described taking at least three days to answer an agency-spend question. Campaign and PO tools do not share consistent identifiers, and people may enter different names or finance codes for the same work. SpendMatch addresses both the historic cleanup and the point where new data is entered.

## Run locally

Install Python 3.10 or newer. In a terminal inside this folder:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

On Windows, activate with `.venv\Scripts\activate` instead. Open the local URL printed by Streamlit (usually `http://localhost:8501`). No API keys or company data are needed.

## Two-minute demo

1. Open **Spend report**. The sample data starts with $37,000 verified spend; three POs need review.
2. Open **Review old data**. Approve the proposed link from `PO-102` to `CMP-001`.
3. Return to **Spend report**. Verified spend is now $45,500. `PO-105` still has a wrong finance code, and `PO-106` has an unknown category; both remain excluded.
4. Open **New PO**, choose `CMP-003`, and try the wrong GL code. The app blocks it and shows the expected category and code.
5. Open **Campaigns** to create a campaign and obtain its shared ID.

## Input format

Campaign CSV columns: `campaign_id,campaign_name,brand,region,agency,category`.

PO CSV columns: `po_id,campaign_id,campaign_name,agency,region,raw_category,gl_code,amount`.

Sample files live in `sample_data/`. Dollar amounts are fictional. One PO is one row; amounts should be numeric without currency symbols. Campaign and PO IDs must be unique in their respective files.

## Matching and taxonomy rules

- A valid shared campaign ID links automatically.
- Without an ID, campaign name and agency similarities produce **suggestions**, not automatic links. A reviewer must approve them.
- Raw labels such as `consumer insights` map to standard categories such as `Research` using the editable alias table in `core.py`.
- Each category has an example GL code defined in `core.py`; codes are illustrative, not an organization's actual accounting policy.
- A report includes a PO only if it is linked or approved, its category is known, and its finance code matches the selected category. An audit export retains all rows and reasons.

## Limitations and next step

This is a local demo. Session changes disappear on server restart, so it is not a production record system. Similarity matching can propose a wrong campaign; human review protects the report. Real adoption would require an approved company taxonomy, permissions, integration with the actual campaign/PO systems, persistent storage, and accounting review of category-to-code rules.

## Test core logic

```bash
python -m unittest discover -s tests -v
```

## Put this project on GitHub

Create a new empty GitHub repository called `spendmatch` (do not initialize it with another README). From this folder:

```bash
git init
git add .
git commit -m "Build SpendMatch MVP"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/spendmatch.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username. GitHub may ask you to sign in. Your submission link is then `https://github.com/YOUR_USERNAME/spendmatch`.
