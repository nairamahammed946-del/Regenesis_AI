# REGENESIS industrial data acquisition

## Facility directories and plant-level records

- **Egypt:** Made in Egypt Gate is an industry directory and B2B platform managed by the Egypt Industrial Development Association. It describes factory profiles, product data and RFQ functionality. It is not an unrestricted bulk-download license; obtain permission or partner access before copying its records. https://madeinegyptgate.com/about/?lang=en
- **Egypt official industrial digital platform:** the Ministry's unified platform is intended for officially registered factories. Use an approved integration/partnership or have factories register directly; do not scrape restricted data. https://mind.gov.eg:8041/
- **Global facility data:** IndustryAtlas describes 29,681 facilities across 165 countries and identifies Climate TRACE v6 as the facility backbone. Its site states CC BY 4.0 for its published open datasets. Check the specific Zenodo record and fields before commercial use. https://inzonex.co.uk/industryatlas/about
- **US manufacturing facilities:** M-FIND contains 340,229 US facility records and is published on Zenodo. It is US-only, not an Egyptian factory directory. https://zenodo.org/records/21827821

- **Climate TRACE public API:** queryable source/asset records by sector, owner and geography; the API is beta and should be used at low volume. It provides emissions source records, not a verified supplier/buyer directory or contact database. Data are published under CC BY 4.0 with attribution. https://climatetrace.org/data and https://api.climatetrace.org/v7/docs/index.html

## Industrial process/material datasets

- **Industrial Ecology Data Commons (IEDC):** 460+ datasets / 3.7 million data points, including material stocks and flows, process inventories, yields and material composition. Each downloaded dataset must be checked against its own source publication and license. https://www.database.industrialecology.uni-freiburg.de/
- **UNEP circular economy data:** https://wedocs.unep.org/items/119697bc-0a4e-48d3-937d-5b6843b6cee1
- **OECD waste by sector:** https://data-explorer.oecd.org/vis?df%5Bag%5D=OECD.ENV.EPI&df%5Bds%5D=DisseminateFinalDMZ&df%5Bid%5D=DSD_WSECTOR%40DF_WSECTOR

## Import

1. Copy `factories_template.csv` and fill it from a source whose terms permit your intended use.
2. Preserve the source name, exact source URL and date for each row.
3. Run `python scripts/import_factories.py path/to/factories.csv --dry-run`.
4. If validation is clean, run without `--dry-run`.
5. Imported facilities are always unverified. A directory record does not prove that a plant generates a particular by-product, buys a material, has available capacity, or wants contact. Only publish a supply/demand listing after confirmation.

The importer intentionally does not invent contact details, waste volumes, material requirements, or verification status.
