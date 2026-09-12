import argparse
import random
import time
import requests


def send_weight(endpoint, weight):
    response = requests.post(endpoint, json={"weight": weight}, timeout=10)
    print(f"Weight {weight}g -> status {response.status_code}")
    try:
        print(response.json())
    except ValueError:
        print(response.text)


def main():
    parser = argparse.ArgumentParser(description="Simulate ESP32 weight sensor payloads")
    parser.add_argument("--endpoint", default="http://127.0.0.1:5000/api/input/weight", help="Weight API endpoint")
    parser.add_argument("--weight", type=float, help="Single weight value in grams")
    parser.add_argument("--min-weight", type=float, default=100.0, help="Minimum random weight in grams")
    parser.add_argument("--max-weight", type=float, default=500.0, help="Maximum random weight in grams")
    parser.add_argument("--count", type=int, default=1, help="Number of weight samples to send")
    parser.add_argument("--interval", type=float, default=1.5, help="Seconds between samples")
    args = parser.parse_args()

    if args.weight is not None:
        send_weight(args.endpoint, args.weight)
        return

    if args.count < 1:
        raise SystemExit("count must be >= 1")

    for i in range(args.count):
        weight = round(random.uniform(args.min_weight, args.max_weight), 2)
        send_weight(args.endpoint, weight)
        if i < args.count - 1:
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
