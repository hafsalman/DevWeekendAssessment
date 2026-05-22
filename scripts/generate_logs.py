import random
import time
import json
from datetime import datetime, timedelta
import argparse


def generate_test_logs(num_lines=1000, seed=42):
    random.seed(seed)
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=1)
    start_epoch = start_time.timestamp()
    end_epoch = end_time.timestamp()
    
    methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD']
    paths = [
        '/api/users',
        '/api/users/12',
        '/api/login',
        '/api/logout',
        '/api/products',
        '/api/products/42',
        '/api/orders',
        '/health',
        '/metrics',
        '/static/style.css',
        '/static/app.js',
        '/admin/dashboard',
        '/api/search',
        '/api/notifications',
    ]
    
    ips = [
        '192.168.1.42',
        '10.0.0.7',
        '172.16.0.1',
        '203.0.113.45',
        '198.51.100.12',
        '203.0.113.99',
    ]
    
    status_weights = {
        200: 0.70,
        201: 0.05,
        204: 0.05,
        400: 0.05,
        401: 0.03,
        403: 0.02,
        404: 0.03,
        500: 0.02,
        503: 0.05,
    }
    
    lines = []
    malformed_count = 0
    target_malformed = int(num_lines * random.uniform(0.05, 0.10))
    
    for i in range(num_lines):
        should_malform = random.random() < (target_malformed - malformed_count) / (num_lines - i)
        
        if should_malform and malformed_count < target_malformed:
            malformed_count += 1
            
            malform_type = random.choice([
                'blank',
                'partial',
                'stack_trace',
                'missing_fields',
                'extra_fields',
                'wrong_format',
                'truncated',
            ])
            
            if malform_type == 'blank':
                lines.append('')
            
            elif malform_type == 'partial':
                lines.append('2024-03-15T14:23:01Z 192.168.1.42')
            
            elif malform_type == 'stack_trace':
                lines.append('  at java.lang.Thread.run(Thread.java:745)')
            
            elif malform_type == 'missing_fields':
                lines.append('2024-03-15T14:23:01Z 192.168.1.42 GET')
            
            elif malform_type == 'extra_fields':
                lines.append(f'2024-03-15T14:23:01Z 192.168.1.42 GET /api/users 200 142ms "Mozilla/5.0" "https://example.com" extra_field1 extra_field2')
            
            elif malform_type == 'wrong_format':
                lines.append(f'corrupted data at offset {random.randint(100, 1000)}')
            
            elif malform_type == 'truncated':
                lines.append('2024-03-15T14:23:01Z 192.168.1.42 GET /api/users 200')
            
        else:
            format_choice = random.choice(['standard', 'standard', 'standard', 'unix_epoch', 'slash_date', 'named_month', 'json'])
            
            epoch = random.uniform(start_epoch, end_epoch)
            dt = datetime.fromtimestamp(epoch)
            
            ip = random.choice(ips)
            method = random.choice(methods)
            path = random.choice(paths)
            status = random.choices(
                list(status_weights.keys()),
                weights=list(status_weights.values())
            )[0]
            response_time = random.choice([
                f'{random.randint(10, 500)}ms',
                f'{random.uniform(0.01, 0.5):.3f}s',
                str(random.randint(10, 500)),
            ])
            
            if format_choice == 'standard':
                line = f"{dt.strftime('%Y-%m-%dT%H:%M:%SZ')} {ip} {method} {path} {status} {response_time}"
            
            elif format_choice == 'unix_epoch':
                line = f"{int(epoch)} {ip} {method} {path} {status} {response_time}"
            
            elif format_choice == 'slash_date':
                line = f"{dt.strftime('%Y/%m/%d %H:%M:%S')} {ip} {method} {path} {status} {response_time}"
            
            elif format_choice == 'named_month':
                line = f"{dt.strftime('%d-%b-%Y %H:%M:%S')} {ip} {method} {path} {status} {response_time}"
            
            elif format_choice == 'json':
                entry = {
                    'timestamp': int(epoch),
                    'ip': ip,
                    'method': method,
                    'path': path,
                    'status': status,
                    'response_time': f'{response_time}',
                }
                line = json.dumps(entry)
            
            lines.append(line)
    
    return lines


def main():
    parser = argparse.ArgumentParser(description='Generate test log files.')
    parser.add_argument('--lines', type=int, default=1000, help='Number of log lines to generate (default: 1000)')
    parser.add_argument('--output', default='test_logs.txt', help='Output file path (default: test_logs.txt)')
    parser.add_argument('--seed', type=int, default=42, help='Random seed for reproducibility (default: 42)')
    
    args = parser.parse_args()
    
    print(f"Generating {args.lines:,} log lines...")
    lines = generate_test_logs(args.lines, seed=args.seed)
    
    with open(args.output, 'w') as f:
        f.write('\n'.join(lines))
    
    print(f"Wrote {args.lines:,} lines to {args.output}")
    print(f"5-10% of lines are intentionally malformed for testing resilience")


if __name__ == '__main__':
    main()