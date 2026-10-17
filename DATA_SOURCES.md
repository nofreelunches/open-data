# Data sources and their terms

Checked against each source's published terms on 2026-10-17.

| Source | Key needed? | Terms | Can we republish derived data? | Required notice or citation |
|---|---|---|---|---|
| FRED (St. Louis Fed) | yes (free) | [FRED API terms](https://fred.stlouisfed.org/docs/api/terms_of_use.html). Third-party series carry the word "Copyright" in their notes and need the owner's permission for anything beyond personal use. | St. Louis Fed series, yes. Third-party copyrighted series, not without the owner's permission. | "This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis." |
| Census API (ACS, PUMS) | yes (free) | [Census API terms](https://www.census.gov/data/developers/about/terms-of-service.html). No re-identification of people, households, or businesses. | Yes. | "This product uses the Census Bureau Data API but is not endorsed or certified by the Census Bureau." |
| Census TIGERweb | no | U.S. government work, public domain. TIGER and TIGER/Line are Census trademarks. | Yes. | Credit the U.S. Census Bureau. |
| IPUMS USA | no | [IPUMS USA terms](https://usa.ipums.org/usa/terms.shtml). No redistribution without permission. | No. Download at runtime and never commit the files. | Cite IPUMS USA per its citation guidance. |
| World Bank WDI | no | [Dataset terms](https://www.worldbank.org/en/about/legal/terms-of-use-for-datasets): CC BY 4.0 unless an indicator is labeled otherwise. | Yes, with attribution. Check each indicator's license field. | "The World Bank: World Development Indicators: [data source]". Pass the same attribution requirement on, for example by linking the dataset terms. |
| BLS | optional | [BLS copyright](https://www.bls.gov/opub/copyright-information.htm): public domain. | Yes. | Cite the Bureau of Labor Statistics. |
| EIA | optional | [EIA reuse](https://www.eia.gov/about/copyrights_reuse.php): public domain. | Yes. | "Source: U.S. Energy Information Administration ([publication date])". |

Implemented here: FRED (`golem_sources.fred`). The other rows are notes for later clients.

Not included: EODHD (paid feed, no redistribution) and the CC-BY-NC `usa-states.svg` map. IPUMS files are not committed.
