# How a FRED series is pulled

FRED (Federal Reserve Economic Data) is a database published by the Federal Reserve Bank of St. Louis. It stores economic measurements as time series. A time series is a list of dates, each with a number. The unemployment rate is one series. Gross domestic product is another.

This page follows one series from an ID on a web page to a list of dates and numbers in Python. The code is `golem_sources/fred.py`. Golem, the research terminal, loads a FRED chart with this same request: one series ID in, observations out.

## A series ID

Every FRED series has an ID. The US civilian unemployment rate is `UNRATE`. Its page is:

https://fred.stlouisfed.org/series/UNRATE

The ID is the last piece of that URL. The page states the units and how often a new number is published. For `UNRATE` the units are percent and the frequency is monthly. A value of 4.1 means 4.1 percent of the labor force is unemployed.

Some series are seasonally adjusted: the agency that produces the series has already removed a regular calendar pattern, such as holiday hiring. The FRED page says when that has been done. The client returns the values FRED sent.

## The request

Observations come from the FRED API. The observations endpoint is:

https://api.stlouisfed.org/fred/series/observations

The call sends the series ID and `file_type=json`, which asks for a JSON document. It also sends `api_key`, a free key from:

https://fred.stlouisfed.org/docs/api/api_key.html

Set the key as the environment variable `FRED_API_KEY`, or put it in a `.env` file in the repository root (see `.env.example`). The client reads that variable when it starts. The key is not written in this page or in the example script.

FRED requires the key on the request URL, so the request that leaves the machine includes it. Log lines and error messages are written with the key removed. The client adds the key on a copy of the request, after the URL that httpx logs has already been formed. If the call fails, the error text is rewritten so the key is gone before the error is raised. The tests check both of those with a stand-in key and a stand-in HTTP response, and they do not call FRED.

A second call, `series`, returns the title, units, and frequency. The example prints those beside the numbers.

## The response

A successful observations response is a JSON object. The field used here is `observations`: a list of objects with `date` and `value`. The date looks like `2024-01-01`. The value is text. A period, `.`, means FRED has no number for that date, because the period is still open or the figure was never published. The client turns dates into `datetime.date` values and values into floats. A period becomes `None`. The example prints that as `NA`.

FRED revises older numbers. The value for a given date can change after you download it. When you publish a figure, write the series ID and the download date next to it. In this project that looks like `FRED: UNRATE`, plus the date.

## Run the example

From the repository root, with the package installed and `FRED_API_KEY` set:

```bash
python examples/pull_fred_series.py
```

That prints the title and the last twelve observations of `UNRATE`. Pass another ID to pull a different series:

```bash
python examples/pull_fred_series.py GDP
```

The script prints to the terminal and does not add a data file to the repository.

The shape of the output, with made-up figures:

```
UNRATE: Unemployment Rate
Units: Percent
Frequency: Monthly

2024-01-01  3.7
2024-02-01  NA
```

## Terms

FRED's own terms cover the data. Some series are supplied by other organizations, and those series stay under their terms. Charts and a citation are the ordinary use. Copying a third-party series into this repository is outside those terms. See [DATA_SOURCES.md](../DATA_SOURCES.md).

Text of this page is CC BY 4.0. The code it describes is MIT. Both are linked from the repository README.
