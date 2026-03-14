# 27. Build Final Report Artifacts

- [x] `scripts/build_report_artifacts.py` must build a project report markdown from generated outputs.

```python
from __future__ import annotations

from pathlib import Path
import json


def main() -> None:
    """Build a simple project report markdown."""
    json_dir = Path("outputs/json/canonical")
    report_dir = Path("outputs/reports")
    report_dir.mkdir(parents=True, exist_ok=True)

    sections: list[str] = [
        "# AMI to pAMI Analysis Report",
        "",
        "## Scope",
        "This report reproduces a horizon-specific AMI workflow and extends it with pAMI.",
        "",
        "## Canonical examples",
        "",
    ]

    for path in sorted(json_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        sections.append(f"### {payload['series_name']}")
        sections.append("")
        sections.append(f"- forecastability_class: {payload['interpretation']['forecastability_class']}")
        sections.append(f"- directness_class: {payload['interpretation']['directness_class']}")
        sections.append(f"- primary_lags: {payload['interpretation']['primary_lags']}")
        sections.append(f"- modeling_regime: {payload['interpretation']['modeling_regime']}")
        sections.append("")
        sections.append(payload["interpretation"]["narrative"])
        sections.append("")

    report_path = report_dir / "ami_to_pami_report.md"
    report_path.write_text("\n".join(sections), encoding="utf-8")
    print(f"Saved report: {report_path}")


if __name__ == "__main__":
    main()
```
