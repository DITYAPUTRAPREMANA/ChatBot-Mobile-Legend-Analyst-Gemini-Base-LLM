import asyncio
import json
import sys
import re
import pathlib
from typing import List, Dict, Optional
from playwright.async_api import async_playwright

URL = "https://mlbb.io/hero-statistics"

def pct_to_float(text: str) -> Optional[float]:
    if not text:
        return None
    m = re.search(r"(-?\d+(?:[.,]\d+)?)\s*%", text)
    if not m:
        return None
    return float(m.group(1).replace(",", "."))

def safe_filename(s: str) -> str:
    return re.sub(r"[^-\w.]+", "_", s).strip("_")

async def scrape(rank: str = "ALL", timeframe: str = "Past 7 days") -> List[Dict]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(URL, wait_until="domcontentloaded")

        try:
            await page.wait_for_selector("table tbody tr", timeout=10000)
        except:
            pass

        try:
            await page.get_by_text("Rank", exact=False).first.wait_for(timeout=3000)
            await page.get_by_role("button", name=rank, exact=True).click(timeout=2000)
        except:
            pass
        try:
            await page.get_by_text("Timeframe", exact=False).first.wait_for(timeout=3000)
            await page.get_by_role("button", name=timeframe, exact=True).click(timeout=2000)
        except:
            pass

        await page.wait_for_timeout(1200)

        data: List[Dict] = []

        rows = []
        try:
            rows = await page.locator("table tbody tr").all()
        except:
            rows = []

        async def extract_from_row(row_locator):
            cells = await row_locator.locator("th, td, [role=cell]").all()
            texts = [ (await c.inner_text()).strip() for c in cells ]
            name = None
            win = pick = ban = None

            percents = []
            for t in texts:
                if re.search(r"%", t):
                    percents.append(t)

            if len(percents) >= 3:
                win = pct_to_float(percents[0])
                pick = pct_to_float(percents[1])
                ban = pct_to_float(percents[2])
            if len(texts) >= 2:
                cand = texts[1].strip()
                if re.search(r"[A-Za-z]", cand):
                    name = re.sub(r"\s+", " ", cand)
            if not name:
                for t in texts:
                    if re.search(r"[A-Za-z]", t):
                        name = re.sub(r"\s+", " ", t)
                        break

            if name and win is not None and pick is not None and ban is not None:
                return {
                    "hero_name": name,
                    "win_rate": win,
                    "pick_rate": pick,
                    "ban_rate": ban
                }
            return None

        if rows:
            for r in rows:
                d = await extract_from_row(r)
                if d:
                    data.append(d)
        else:
            item_locators = await page.locator("section, div").all()
            for loc in item_locators:
                try:
                    text = (await loc.inner_text()).strip()
                except:
                    continue
                if len(re.findall(r"%", text)) >= 3 and len(text.split()) > 2:
                    row_data = await extract_from_row(loc)
                    if row_data:
                        data.append(row_data)
            seen = set()
            uniq = []
            for d in data:
                key = (d["hero_name"], d["win_rate"], d["pick_rate"], d["ban_rate"])
                if key not in seen:
                    seen.add(key)
                    uniq.append(d)
            data = uniq

        await browser.close()
        return data

def save_to_json(data: List[Dict], filename: str):
    path = pathlib.Path(filename)
    if not path.suffix.lower() == ".json":
        path = path.with_suffix(".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Tersimpan: {path.resolve()}")

def cli():
    rank = "ALL"
    timeframe = "Past 7 days"
    out_file = None
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--rank" and i + 1 < len(args):
            rank = args[i + 1]; i += 2; continue
        if a == "--timeframe" and i + 1 < len(args):
            timeframe = args[i + 1]; i += 2; continue
        if a in ("--out", "-o") and i + 1 < len(args):
            out_file = args[i + 1]; i += 2; continue
        i += 1

    data = asyncio.run(scrape(rank=rank, timeframe=timeframe))

    if not out_file:
        out_file = f"mlbb_hero_stats_{safe_filename(rank)}_{safe_filename(timeframe)}.json"

    save_to_json(data, out_file)

if __name__ == "__main__":
    cli()
