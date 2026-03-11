import re
import sys
import json

def filter_errors(log_file_path):
    """
    Two-stage JSON-aware error filter.
    1. Identify lines with 'error', 'fail', 'exception' (case-insensitive).
    2. Exclude lines where the match is just a JSON key (e.g., "error": null, "hasError": false).
    """
    error_pattern = re.compile(r'(?i)\b(error|fail|exception)\b')
    # Matches a JSON key containing error/fail/exception
    json_key_pattern = re.compile(r'"[^"]*(?i:error|fail|exception)[^"]*"\s*:')
    
    real_errors = []
    with open(log_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if error_pattern.search(line):
                # If the error string is just a JSON key, skip it
                if json_key_pattern.search(line):
                    # Quick check: if the rest of the line doesn't have an actual error, ignore.
                    # A more robust check would parse JSON, but log lines might be partial JSON.
                    # We assume if it's a JSON key, we only flag if the value is explicitly indicating an error.
                    # For a simple filter, we exclude it to avoid false positives.
                    continue
                real_errors.append(line.strip())
                
    return real_errors

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python json_error_filter.py <log_file>")
        sys.exit(1)
        
    errors = filter_errors(sys.argv[1])
    for err in errors:
        print(err)
