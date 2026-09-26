"""Dependency-free matching and reporting logic for SpendMatch."""
import csv
import io
import re
from collections import defaultdict
from difflib import SequenceMatcher

CATEGORIES = ("Creative Production", "Media", "Research", "Strategy")
ALIASES = {
    "creative": "Creative Production", "production": "Creative Production",
    "content production": "Creative Production", "media buying": "Media",
    "paid media": "Media", "advertising": "Media",
    "consumer insights": "Research", "market research": "Research",
    "insights": "Research", "planning": "Strategy",
    "brand strategy": "Strategy", "consulting": "Strategy",
}
DEFAULT_CODES = {
    "Creative Production": "6100", "Media": "6200",
    "Research": "6300", "Strategy": "6400",
}


def norm(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def category_for(raw):
    value = norm(raw)
    for category in CATEGORIES:
        if norm(category) == value:
            return category
    return ALIASES.get(value)


def read_csv(source, required):
    """Read UTF-8 CSV from uploaded bytes or a file-like object."""
    if isinstance(source, bytes):
        source = io.StringIO(source.decode("utf-8-sig"))
    elif isinstance(source, str):
        source = io.StringIO(source)
    reader = csv.DictReader(source)
    columns = set(reader.fieldnames or [])
    missing = set(required) - columns
    if missing:
        raise ValueError("Missing CSV columns: " + ", ".join(sorted(missing)))
    return [{key: (value or "").strip() for key, value in row.items()}
            for row in reader if any((value or "").strip() for value in row.values())]


def suggest(po, campaigns):
    """Return (campaign_id, status, reason); suggestions never count as approved."""
    by_id = {c["campaign_id"]: c for c in campaigns}
    cid = po.get("campaign_id", "").strip()
    if cid and cid in by_id:
        return cid, "linked", "Shared campaign ID"
    if not campaigns:
        return "", "unmatched", "No campaigns available"
    candidates = []
    for c in campaigns:
        name_score = SequenceMatcher(None, norm(po.get("campaign_name")), norm(c["campaign_name"])).ratio()
        agency_score = SequenceMatcher(None, norm(po.get("agency")), norm(c["agency"])).ratio()
        score = 0.7 * name_score + 0.3 * agency_score
        if norm(po.get("region")) and norm(po["region"]) != norm(c.get("region")):
            score -= 0.2
        candidates.append((score, c["campaign_id"]))
    score, candidate = max(candidates)
    if score >= 0.65:
        return candidate, "review", f"Suggested name/agency match ({score:.0%})"
    return "", "unmatched", "No strong match"


def reconcile(campaigns, purchase_orders, approvals=None):
    approvals = approvals or {}
    by_id = {c["campaign_id"]: c for c in campaigns}
    result = []
    for po in purchase_orders:
        record = dict(po)
        cid, status, reason = suggest(po, campaigns)
        if po["po_id"] in approvals and approvals[po["po_id"]] in by_id:
            cid, status, reason = approvals[po["po_id"]], "approved", "Approved by reviewer"
        campaign = by_id.get(cid)
        raw_category = category_for(po.get("raw_category"))
        record.update(match_id=cid, status=status, match_reason=reason,
                      category=raw_category or "Unmapped",
                      expected_code=DEFAULT_CODES.get(raw_category, ""),
                      code_warning=("Category/code mismatch" if raw_category and
                                    po.get("gl_code") != DEFAULT_CODES[raw_category] else
                                    "Unknown category" if not raw_category else ""),
                      campaign_name_standard=campaign["campaign_name"] if campaign else "",
                      agency_standard=campaign["agency"] if campaign else "")
        try:
            record["amount"] = float(po["amount"])
        except (ValueError, TypeError):
            raise ValueError(f"Invalid amount for PO {po['po_id']}")
        result.append(record)
    return result


def summarize(rows):
    totals = defaultdict(float)
    for r in rows:
        if r["status"] in ("linked", "approved") and r["category"] != "Unmapped" and not r["code_warning"]:
            totals[(r["agency_standard"], r["category"])] += r["amount"]
    return [{"Agency": agency, "Category": category, "Spend": round(total, 2)}
            for (agency, category), total in sorted(totals.items())]


def csv_bytes(rows):
    if not rows:
        return b""
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode("utf-8-sig")
