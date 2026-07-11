from app.forms import issue_types, FORM_SCHEMAS

# field names must be real template slots (or the shared BOL/PRO/customer_request) so intake
# maps straight onto what the drafting engine fills.
KNOWN_SLOTS = {
    "pickup_address", "contact_name", "contact_phone", "requested_window", "receiver_contact",
    "new_address", "damage_desc", "delivery_date", "cancel_reason", "return_reason",
}


def test_issue_types_shape_and_slots():
    its = issue_types()
    slugs = {i["slug"] for i in its}
    assert {"delivery-window", "pickup", "other", "pro-lookup"} <= slugs  # pro-lookup surfaced
    dw = next(i for i in its if i["slug"] == "delivery-window")
    assert any(f["name"] == "requested_window" for f in dw["fields"])
    for it in its:
        for f in it["fields"]:
            assert {"name", "label_zh", "label_en", "type", "required"} <= set(f)
            assert f["name"] in KNOWN_SLOTS, f"unknown slot {f['name']}"


def test_freeform_types_have_no_fields():
    for slug in ("shipment-status", "pro-lookup", "other"):
        assert FORM_SCHEMAS.get(slug) == []
