# Data sources and their terms

Summaries only. Confirm each source's current terms before publishing numbers from it.

| Source | Key needed? | Terms (summary) | Can we republish derived data? | Status |
|---|---|---|---|---|
| FRED (St. Louis Fed) | yes (free) | FRED API terms of use. Some series are owned by third parties (for example ICE BofA, S&P, Moody's) and carry copyright notices. | Charts and citations, usually yes. Bulk redistribution of third-party series, no. Flag those series. | to confirm |
| Census ACS / PUMS | yes (free) | U.S. government work, public domain. Do not imply Census endorsement. | Yes. | to confirm |
| Census TIGERweb | no | Public domain. | Yes. | to confirm |
| IPUMS USA crosswalks | no | Cite IPUMS. Do not redistribute their files. | Cite, and download at runtime. Never commit the files. | to confirm |
| World Bank WDI | no | CC BY 4.0. | Yes, with attribution. | to confirm |
| BLS | optional | Public domain. | Yes. | to confirm |
| EIA | optional | Public domain, attribution requested. | Yes. | to confirm |

Implemented here: FRED (`golem_sources.fred`). The other rows are notes for later clients.

Not included: EODHD (paid feed, no redistribution) and the CC-BY-NC `usa-states.svg` map. IPUMS files are not committed.
