name: Update BTC price data

on:
  schedule:
    # 01:00 UTC daily -- well after CoinGecko's daily candle closes and caches (00:40 UTC)
    - cron: "0 1 * * *"
  workflow_dispatch: {}   # lets you trigger it manually from the Actions tab

permissions:
  contents: write

jobs:
  update-data:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Fetch and append new BTC closes
        env:
          COINGECKO_API_KEY: ${{ secrets.COINGECKO_API_KEY }}
        run: python scripts/update_btc_data.py

      - name: Commit updated data (if changed)
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/btc-history.json
          git diff --staged --quiet && echo "No changes to commit." && exit 0
          git commit -m "Update BTC price data [automated]"
          git push
