"""Synthetic receipt factory ONLY for structural tests, never a semantic review."""
import reader_value


def structural_review(axes, binding, text, source="", render=""):
    review = reader_value.template(axes, binding)
    for axis, item in review["checks"].items():
        item.update(status="pass", action="keep", location="STRUCTURAL TEST FIXTURE",
                    quote=text[:100], reader_effect="STRUCTURAL FIXTURE, not a reader judgment.",
                    protected_meaning="STRUCTURAL FIXTURE, not source verification.")
        if axis == "selection":
            item["removal_effect"] = "STRUCTURAL FIXTURE: removed text would be absent."
        if axis == "meaning":
            item["source_quote"] = source[:100]
        if axis == "presentation":
            item.update(render_path=str(render), observation="STRUCTURAL FIXTURE, not rendered inspection.")
        if axis == "unit_roles":
            item["roles"] = {key: f"STRUCTURAL FIXTURE {key}" for key in item["roles"]}
    return review
