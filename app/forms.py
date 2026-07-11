"""Category-dependent intake form engine. Schema-driven: the customer app fetches these
schemas and renders a form per issue type; field `name`s match the template slots the drafting
engine fills, so intake collects exactly what the draft needs. Adding a type is a data change
here (single source of truth), no frontend redeploy.

This is the MVP form config; in the multi-tenant build it becomes a per-agent Knowledge-service
override alongside the templates."""
from __future__ import annotations


def _f(name, zh, en, type="text", required=True):
    return {"name": name, "label_zh": zh, "label_en": en, "type": type, "required": required}


# Per issue slug: the category-specific fields (on top of the always-present BOL + free note,
# which the frontend collects separately). Field names == template slot names.
FORM_SCHEMAS: dict[str, list[dict]] = {
    "pickup": [
        _f("pickup_address", "提货地址", "Pickup address"),
        _f("contact_name", "联系人", "Contact name"),
        _f("contact_phone", "联系电话", "Contact phone", type="tel"),
    ],
    "delivery-window": [
        _f("requested_window", "要求的送达时间窗", "Requested delivery window"),
        _f("receiver_contact", "收货人联系方式", "Receiver contact", required=False),
    ],
    "reconsignment": [
        _f("new_address", "新的送达地址", "New delivery address"),
        _f("contact_name", "新联系人", "New contact name", required=False),
        _f("contact_phone", "新联系电话", "New contact phone", type="tel", required=False),
    ],
    "damage": [
        _f("damage_desc", "损坏描述", "Damage description", type="textarea"),
        _f("delivery_date", "期望送达日期", "Requested delivery date", type="date", required=False),
    ],
    "pod-request": [
        _f("delivery_date", "送达日期(如已知)", "Delivery date (if known)", type="date",
           required=False),
    ],
    "cancellation": [
        _f("cancel_reason", "取消原因", "Cancellation reason", type="textarea", required=False),
    ],
    "shipment-status": [],           # no extra fields — just BOL + note
    "pro-lookup": [],
    "return-reason": [
        _f("return_reason", "退运原因/背景", "Return reason / context", type="textarea",
           required=False),
    ],
    "other": [],                     # freeform only (the note)
}

# Customer-friendly labels for the issue types the customer app offers.
ISSUE_LABELS: dict[str, tuple[str, str]] = {
    "pickup": ("提货", "Pickup"),
    "delivery-window": ("送达时间/预约", "Delivery window"),
    "shipment-status": ("查询状态", "Shipment status"),
    "pod-request": ("索取签收凭证 (POD)", "POD request"),
    "pro-lookup": ("查询 PRO 单号", "PRO lookup"),
    "cancellation": ("取消", "Cancellation"),
    "reconsignment": ("改送新地址", "Reconsignment"),
    "damage": ("货物损坏", "Damage"),
    "return-reason": ("退运原因", "Return reason"),
    "other": ("其他 (自由描述)", "Other (free text)"),
}


def issue_types() -> list[dict]:
    """Customer-facing issue types + their form schemas."""
    out = []
    for slug, (zh, en) in ISSUE_LABELS.items():
        out.append({"slug": slug, "label_zh": zh, "label_en": en,
                    "fields": FORM_SCHEMAS.get(slug, [])})
    return out
