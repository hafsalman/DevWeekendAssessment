import sys
import re
import argparse
from datetime import datetime
from collections import defaultdict, Counter
from typing import Optional, Dict, List, Tuple
import json
import time


class LogEntry:    
    def __init__(self, timestamp: Optional[float], ip: Optional[str], method: Optional[str],
                 path: Optional[str], status: Optional[int], response_time_ms: Optional[float]):
        self.timestamp = timestamp
        self.ip = ip
        self.method = method
        self.path = path
        self.status = status
        self.response_time_ms = response_time_ms
        self.is_error = status is None or status >= 400 if status else False

    def __repr__(self):
        return f"LogEntry(ts={self.timestamp}, ip={self.ip}, {self.method} {self.path} {self.status} {self.response_time_ms}ms)"


class LogParser:
    STANDARD_PATTERN = r'^([\d/T:\-Z.\s\-a-zA-Z]+?)\s+(\S+)\s+(\w+)\s+(\S+)\s+(-|\d+)\s+([\d.]+(?:ms|s)?)'
    
    def __init__(self):
        self.stats = {
            'total_lines': 0,
            'parsed_lines': 0,
            'malformed_lines': 0,
            'json_lines': 0,
            'format_variants': Counter(),
            'parsing_errors': []
        }

    def _parse_timestamp(self, ts_str: str) -> Optional[float]:
        if not ts_str or ts_str == '-':
            return None

        # Unix epoch (raw number)
        if ts_str.isdigit() or (ts_str.startswith('-') and ts_str[1:].isdigit()):
            try:
                return float(ts_str)
            except ValueError:
                return None

        formats_to_try = [
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S',
            '%Y/%m/%d %H:%M:%S',
            '%m/%d/%Y %H:%M:%S',
            '%d/%m/%Y %H:%M:%S',
            '%d-%b-%Y %H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
        ]

        for fmt in formats_to_try:
            try:
                dt = datetime.strptime(ts_str, fmt)
                return dt.timestamp()
            except ValueError:
                continue

        return None

    def _parse_response_time(self, time_str: str) -> Optional[float]:
        if not time_str or time_str == '-':
            return None

        time_str = time_str.strip()

        if time_str.endswith('ms'):
            try:
                return float(time_str[:-2])
            except ValueError:
                return None

        if time_str.endswith('s'):
            try:
                return float(time_str[:-1]) * 1000  # convert to ms
            except ValueError:
                return None

        try:
            return float(time_str)
        except ValueError:
            return None

    def _try_parse_json_log(self, line: str) -> Optional[LogEntry]:
        try:
            data = json.loads(line)
            timestamp = None
            
            for key in ['timestamp', 'time', 'ts', '@timestamp']:
                if key in data:
                    timestamp = self._parse_timestamp(str(data[key]))
                    break
            
            ip = data.get('ip') or data.get('client_ip') or data.get('remote_addr')
            method = data.get('method') or data.get('http_method')
            path = data.get('path') or data.get('uri') or data.get('url')
            status = None
            if 'status' in data or 'status_code' in data or 'code' in data:
                try:
                    status = int(data.get('status') or data.get('status_code') or data.get('code'))
                except (ValueError, TypeError):
                    status = None
            
            response_time = None
            for key in ['response_time', 'duration', 'latency', 'elapsed']:
                if key in data:
                    response_time = self._parse_response_time(str(data[key]))
                    break
            
            if timestamp and path:
                self.stats['json_lines'] += 1
                self.stats['format_variants']['json'] += 1
                return LogEntry(timestamp, ip, method, path, status, response_time)
        except (json.JSONDecodeError, ValueError):
            pass
        
        return None

    def parse_line(self, line: str) -> Optional[LogEntry]:
        self.stats['total_lines'] += 1
        
        line = line.rstrip('\n')
        
        if not line or not line.strip():
            self.stats['malformed_lines'] += 1
            return None

        json_entry = self._try_parse_json_log(line)
        if json_entry:
            self.stats['parsed_lines'] += 1
            return json_entry

        match = re.match(self.STANDARD_PATTERN, line)
        if match:
            self.stats['parsed_lines'] += 1
            self.stats['format_variants']['standard'] += 1
            
            ts_str, ip, method, path, status_str, time_str = match.groups()
            
            timestamp = self._parse_timestamp(ts_str)
            response_time = self._parse_response_time(time_str)
            status = None
            if status_str != '-':
                try:
                    status = int(status_str)
                except ValueError:
                    pass
            
            return LogEntry(timestamp, ip, method, path, status, response_time)

        self.stats['malformed_lines'] += 1
        self.stats['parsing_errors'].append(line[:100])
        return None


class LogAnalyzer:
    def __init__(self):
        self.entries: List[LogEntry] = []
        self.parser = LogParser()

    def load_file(self, filepath: str) -> None:
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    entry = self.parser.parse_line(line)
                    if entry:
                        self.entries.append(entry)
        except FileNotFoundError:
            print(f"Error: File not found: {filepath}", file=sys.stderr)
            sys.exit(1)
        except IOError as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)

    def print_summary(self) -> None:
        if not self.entries:
            print("No valid log entries parsed.")
            return

        stats = self.parser.stats
        
        print("\n" + "="*70)
        print("LOG ANALYZER REPORT")
        print("="*70)
        
        print(f"\nPARSING STATISTICS")
        print(f"  Total lines:           {stats['total_lines']:,}")
        print(f"  Successfully parsed:   {stats['parsed_lines']:,} ({stats['parsed_lines']*100//stats['total_lines']:.1f}%)")
        print(f"  Malformed/skipped:     {stats['malformed_lines']:,}")
        print(f"  Format variants found: {dict(stats['format_variants'])}")
        
        if stats['parsing_errors'] and stats['malformed_lines'] <= 10:
            print(f"\nExample malformed lines:")
            for err in stats['parsing_errors'][:5]:
                print(f"    └─ {err}...")

        status_codes = Counter()
        for entry in self.entries:
            if entry.status:
                status_codes[entry.status] += 1
        
        success = sum(c for s, c in status_codes.items() if s < 400)
        client_errors = sum(c for s, c in status_codes.items() if 400 <= s < 500)
        server_errors = sum(c for s, c in status_codes.items() if s >= 500)
        unknown = len(self.entries) - sum(status_codes.values())

        print(f"\nRESPONSE STATUS DISTRIBUTION")
        print(f"  Success (2xx):         {success:,} ({success*100//len(self.entries):.1f}%)")
        print(f"  Client Errors (4xx):   {client_errors:,} ({client_errors*100//len(self.entries):.1f}%)")
        print(f"  Server Errors (5xx):   {server_errors:,} ({server_errors*100//len(self.entries):.1f}%)")
        if unknown:
            print(f"  Unknown:               {unknown:,}")
        
        print(f"\n  Top status codes:")
        for status, count in status_codes.most_common(5):
            print(f"    {status}: {count:,} requests")

        response_times = [e.response_time_ms for e in self.entries if e.response_time_ms is not None]
        if response_times:
            response_times.sort()
            avg = sum(response_times) / len(response_times)
            p50 = response_times[len(response_times)//2]
            p95 = response_times[int(len(response_times)*0.95)]
            p99 = response_times[int(len(response_times)*0.99)]
            
            print(f"\nRESPONSE TIME ANALYSIS (ms)")
            print(f"  Mean:                  {avg:.1f}ms")
            print(f"  Median (p50):          {p50:.1f}ms")
            print(f"  95th percentile (p95): {p95:.1f}ms")
            print(f"  99th percentile (p99): {p99:.1f}ms")
            print(f"  Min:                   {min(response_times):.1f}ms")
            print(f"  Max:                   {max(response_times):.1f}ms")

        endpoint_stats = defaultdict(lambda: {'count': 0, 'errors': 0, 'total_time': 0})
        for entry in self.entries:
            if entry.method and entry.path:
                key = f"{entry.method} {entry.path}"
                endpoint_stats[key]['count'] += 1
                if entry.is_error:
                    endpoint_stats[key]['errors'] += 1
                if entry.response_time_ms:
                    endpoint_stats[key]['total_time'] += entry.response_time_ms

        print(f"\nTOP 10 ENDPOINTS BY FREQUENCY")
        for i, (endpoint, stats_dict) in enumerate(
            sorted(endpoint_stats.items(), key=lambda x: x[1]['count'], reverse=True)[:10], 1
        ):
            error_rate = (stats_dict['errors']*100//stats_dict['count']) if stats_dict['count'] > 0 else 0
            print(f"  {i:2d}. {endpoint:<40} {stats_dict['count']:>6,} requests ({error_rate:>2d}% errors)")

        print(f"\nSLOWEST ENDPOINTS (by mean response time)")
        slowest = [
            (ep, stats_dict['total_time'] / stats_dict['count'])
            for ep, stats_dict in endpoint_stats.items()
            if stats_dict['total_time'] > 0 and stats_dict['count'] > 0
        ]
        slowest.sort(key=lambda x: x[1], reverse=True)
        
        for i, (endpoint, avg_time) in enumerate(slowest[:10], 1):
            print(f"  {i:2d}. {endpoint:<40} {avg_time:>8.1f}ms avg")

        print(f"\nTOP IPs BY REQUEST COUNT")
        ip_counts = Counter()
        for entry in self.entries:
            if entry.ip:
                ip_counts[entry.ip] += 1
        
        for i, (ip, count) in enumerate(ip_counts.most_common(10), 1):
            print(f"  {i:2d}. {ip:<20} {count:>8,} requests")

        print("\n" + "="*70 + "\n")

    def print_slowest(self, limit: int = 20) -> None:
        requests_with_time = [
            (e.timestamp, f"{e.method} {e.path}", e.response_time_ms, e.status)
            for e in self.entries
            if e.response_time_ms is not None
        ]
        requests_with_time.sort(key=lambda x: x[2], reverse=True)
        
        print(f"\nSLOWEST {limit} REQUESTS")
        print(f"{'Time (ms)':<12} {'Status':<8} {'Method':<6} {'Path'}")
        print("-" * 70)
        
        for ts, endpoint, duration, status in requests_with_time[:limit]:
            status_str = str(status) if status else '-'
            print(f"{duration:>10.1f}ms {status_str:<8} {endpoint}")
        
        print()


def main():
    parser = argparse.ArgumentParser(
        description='Analyze server logs with multiple formats and graceful error handling.'
    )
    parser.add_argument('logfile', help='Path to the log file to analyze')
    parser.add_argument('--slowest', type=int, metavar='N', help='Show the N slowest individual requests')
    
    args = parser.parse_args()
    
    analyzer = LogAnalyzer()
    analyzer.load_file(args.logfile)
    analyzer.print_summary()
    
    if args.slowest:
        analyzer.print_slowest(args.slowest)


if __name__ == '__main__':
    main()