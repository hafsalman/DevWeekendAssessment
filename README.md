# Log Analyzer

A robust CLI tool for analyzing server logs with mixed formats and malformed entries.

## Features

- **Multi-format parsing**: Handles ISO 8601, Unix epoch, slash-format, named-month timestamps
- **Flexible response times**: Supports ms, seconds, or raw numbers
- **Graceful error handling**: Skips malformed lines without crashing; reports count and examples
- **Comprehensive analytics**: 
  - Status code distribution and error rates
  - Response time percentiles (p50, p95, p99)
  - Top endpoints by frequency and slowness
  - Top IPs by request count
  - Format variant detection

## Quick Start

### Prerequisites
- Python 3.7+
- No external dependencies

## How to Run on Fresh Machine

1. Clone/download the repository
2. Ensure Python 3.7+ is installed
3. Run: `python log_analyzer.py <path-to-your-logfile>`

No installation or dependencies needed.

## Handling of Edge Cases

The analyzer gracefully handles:

- **Blank lines**: Skipped silently
- **Missing status codes or response times**: Fields treated as optional; entries still processed
- **Multiple timestamp formats**: Detects and parses ISO 8601, Unix epoch, slash-format, named-month variants
- **Multiple response time units**: Converts s to ms automatically
- **Extra fields** (user agents, referrers): Regex extracts core fields, ignores extras
- **JSON entries mixed with standard format**: Detects and parses separately
- **Malformed lines**: Counted, reported, not fatal — processing continues
- **Large files**: Streams line-by-line, memory-efficient

## Testing

```bash
python scripts/generate_logs.py --lines 100000 --output mytest.log

# Analyze it
python log_analyzer.py mytest.log
```

The generator creates realistic variations:
- Blank lines
- Partial writes
- Stack traces
- Missing fields
- Extra fields
- JSON logs mixed in