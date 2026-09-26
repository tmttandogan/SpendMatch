"""SpendMatch: taxonomy-guided marketing spend reconciliation demo."""
from pathlib import Path
import streamlit as st

from core import CATEGORIES, DEFAULT_CODES, category_for, csv_bytes, read_csv, reconcile, summarize

ROOT = Path(__file__).parent
CAMPAIGN_COLUMNS = ["campaign_id", "campaign_name", "brand", "region", "agency", "category"]
PO_COLUMNS = ["po_id", "campaign_id", "campaign_name", "agency", "region", "raw_category", "gl_code", "amount"]

st.set_page_config(page_title="SpendMatch", page_icon="🔗", layout="wide")

if "campaigns" not in st.session_state:
    st.session_state.campaigns = read_csv((ROOT / "sample_data/campaigns.csv").read_bytes(), CAMPAIGN_COLUMNS)
if "pos" not in st.session_state:
    st.session_state.pos = read_csv((ROOT / "sample_data/purchase_orders.csv").read_bytes(), PO_COLUMNS)
if "approvals" not in st.session_state:
    st.session_state.approvals = {}

st.title("SpendMatch")
st.caption("Connect campaigns to purchase orders, fix taxonomy issues, and trust the resulting spend report. Fictional demo data.")
tab1, tab2, tab3, tab4 = st.tabs(["1 · Campaigns", "2 · New PO", "3 · Review old data", "4 · Spend report"])

with tab1:
    st.subheader("Create a campaign with a shared ID")
    st.dataframe(st.session_state.campaigns, use_container_width=True, hide_index=True)
    with st.form("campaign_form", clear_on_submit=True):
        a, b = st.columns(2)
        name = a.text_input("Campaign name")
        brand = b.text_input("Brand")
        region = a.text_input("Region", value="US")
        agency = b.text_input("Agency")
        category = st.selectbox("Standard spend category", CATEGORIES)
        create = st.form_submit_button("Create campaign")
    if create:
        if not all(x.strip() for x in (name, brand, region, agency)):
            st.error("Fill in every campaign field.")
        else:
            ids = [int(c["campaign_id"].split("-")[-1]) for c in st.session_state.campaigns
                   if c["campaign_id"].startswith("CMP-") and c["campaign_id"].split("-")[-1].isdigit()]
            cid = f"CMP-{max(ids, default=0) + 1:03d}"
            st.session_state.campaigns.append(dict(campaign_id=cid, campaign_name=name.strip(),
                brand=brand.strip(), region=region.strip(), agency=agency.strip(), category=category))
            st.success(f"Created {cid}. Use this ID when submitting a purchase order.")

with tab2:
    st.subheader("Create a PO with a taxonomy check")
    campaign_ids = [c["campaign_id"] for c in st.session_state.campaigns]
    selected = st.selectbox("Choose the shared campaign ID", campaign_ids,
                            format_func=lambda cid: next(f"{cid} · {c['campaign_name']}" for c in st.session_state.campaigns if c["campaign_id"] == cid))
    campaign = next(c for c in st.session_state.campaigns if c["campaign_id"] == selected)
    expected_category = category_for(campaign["category"])
    st.info(f"Agency: {campaign['agency']}  ·  Category: {expected_category or 'Unmapped'}  ·  Suggested GL code: {DEFAULT_CODES.get(expected_category, 'unknown')}")
    with st.form("po_form", clear_on_submit=True):
        po_id = st.text_input("PO ID", placeholder="PO-107")
        amount = st.number_input("Amount (USD)", min_value=0.01, value=1000.0, step=100.0)
        entered_category = st.selectbox("Spend category", CATEGORIES,
            index=CATEGORIES.index(expected_category) if expected_category in CATEGORIES else 0)
        entered_code = st.text_input("GL finance code", value=DEFAULT_CODES.get(expected_category, ""))
        submit = st.form_submit_button("Check and create PO")
    if submit:
        if not po_id.strip() or po_id.strip() in {p["po_id"] for p in st.session_state.pos}:
            st.error("Enter a unique PO ID.")
        elif entered_category != expected_category or entered_code.strip() != DEFAULT_CODES[entered_category]:
            st.error(f"Taxonomy conflict: this campaign uses {expected_category} ({DEFAULT_CODES.get(expected_category)}). Review the category and code before submitting.")
        else:
            st.session_state.pos.append(dict(po_id=po_id.strip(), campaign_id=selected,
                campaign_name=campaign["campaign_name"], agency=campaign["agency"],
                region=campaign["region"], raw_category=entered_category,
                gl_code=entered_code.strip(), amount=str(amount)))
            st.success(f"Created {po_id.strip()} with shared campaign ID {selected}.")

with tab3:
    st.subheader("Reconcile older records")
    st.write("Upload CSV exports or use the fictional sample records. Suggested matches require your approval before appearing in the report.")
    left, right = st.columns(2)
    campaign_file = left.file_uploader("Campaign CSV", type="csv")
    po_file = right.file_uploader("Purchase order CSV", type="csv")
    if st.button("Load uploaded files"):
        if not campaign_file or not po_file:
            st.error("Upload both CSV files.")
        else:
            try:
                new_campaigns = read_csv(campaign_file.getvalue(), CAMPAIGN_COLUMNS)
                new_pos = read_csv(po_file.getvalue(), PO_COLUMNS)
                if len({c["campaign_id"] for c in new_campaigns}) != len(new_campaigns):
                    raise ValueError("Campaign IDs must be unique.")
                if len({p["po_id"] for p in new_pos}) != len(new_pos):
                    raise ValueError("PO IDs must be unique.")
                st.session_state.campaigns = new_campaigns
                st.session_state.pos = new_pos
                st.session_state.approvals = {}
                st.success("Files loaded. Review the suggested matches below.")
            except (ValueError, UnicodeDecodeError) as exc:
                st.error(str(exc))
    rows = reconcile(st.session_state.campaigns, st.session_state.pos, st.session_state.approvals)
    st.dataframe([{key: r.get(key) for key in ("po_id", "campaign_name", "agency", "match_id", "status", "match_reason", "category", "gl_code", "code_warning")}
                  for r in rows], use_container_width=True, hide_index=True)
    review = [r for r in rows if r["status"] in ("review", "unmatched")]
    for r in review:
        with st.expander(f"{r['po_id']} · {r['campaign_name']} · {r['status']}"):
            st.write(f"Proposed link: **{r['match_id'] or 'None'}**. {r['match_reason']}")
            choices = ["Keep unresolved"] + [c["campaign_id"] for c in st.session_state.campaigns]
            default = choices.index(r["match_id"]) if r["match_id"] in choices else 0
            chosen = st.selectbox("Correct campaign", choices, index=default, key=f"pick_{r['po_id']}")
            if st.button("Approve link", key=f"approve_{r['po_id']}"):
                if chosen == "Keep unresolved":
                    st.warning("Choose a campaign ID before approving.")
                else:
                    st.session_state.approvals[r["po_id"]] = chosen
                    st.rerun()
    st.caption("Rows with unknown categories or conflicting GL codes stay out of verified totals. Fix the source CSV and reload it to resolve them.")

with tab4:
    st.subheader("Verified agency spend")
    rows = reconcile(st.session_state.campaigns, st.session_state.pos, st.session_state.approvals)
    report = summarize(rows)
    verified_total = sum(r["Spend"] for r in report)
    unresolved = [r for r in rows if r["status"] not in ("linked", "approved") or r["code_warning"]]
    a, b, c = st.columns(3)
    a.metric("Verified spend", f"${verified_total:,.2f}")
    b.metric("Included POs", len(rows) - len(unresolved))
    c.metric("Needs review", len(unresolved))
    st.dataframe(report, use_container_width=True, hide_index=True)
    if report:
        st.bar_chart({f"{r['Agency']} · {r['Category']}": r["Spend"] for r in report})
    st.subheader("Needs review")
    st.dataframe([{key: r.get(key) for key in ("po_id", "amount", "status", "match_id", "raw_category", "gl_code", "expected_code", "code_warning")}
                  for r in unresolved], use_container_width=True, hide_index=True)
    st.download_button("Download audit trail CSV", csv_bytes(rows), "spendmatch_audit.csv", "text/csv")
