"""Capture a genuine, reproducible Asset impact screenshot from local Streamlit.

The mock EAM service and Streamlit must be running on localhost. Only synthetic
data is used; no OpenAI credentials are needed.
"""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "Images" / "asset-impact.png"


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        try:
            page = browser.new_page(
                viewport={"width": 1600, "height": 1000},
                device_scale_factor=1,
                color_scheme="dark",
            )
            page.goto("http://127.0.0.1:8501", wait_until="domcontentloaded", timeout=90000)
            page.get_by_role("tab", name="Asset impact").wait_for(timeout=90000)
            page.get_by_role("tab", name="Asset impact").click()

            # The clean demo defaults to Balanced, £250m, EAM on, A133: 8.
            page.get_by_text("current condition", exact=False).first.wait_for(timeout=90000)
            page.get_by_role("button", name="Compare funding decisions").click()
            page.get_by_text("Funding decisions that changed", exact=True).wait_for(timeout=90000)

            # Guard against a misleading screenshot of an incomplete comparison.
            if "£249.9m" not in page.locator("body").inner_text():
                raise RuntimeError("Expected baseline capital allocation is not visible")
            if "£243.2m" not in page.locator("body").inner_text():
                raise RuntimeError("Expected simulated capital allocation is not visible")

            page.screenshot(path=str(OUTPUT), full_page=True, animations="disabled")
            print(f"Captured {OUTPUT} ({OUTPUT.stat().st_size:,} bytes)")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
