import argparse
import os
import requests


def main():
    parser = argparse.ArgumentParser(description="Simulate ESPCAM image upload to dashboard endpoint")
    parser.add_argument("--endpoint", default="http://127.0.0.1:5000/api/input/capture", help="Capture API endpoint")
    parser.add_argument("--image", required=True, help="Path to image file to upload")
    args = parser.parse_args()

    if not os.path.exists(args.image):
        raise SystemExit(f"Image file not found: {args.image}")

    with open(args.image, "rb") as image_file:
        files = {"image": (os.path.basename(args.image), image_file, "application/octet-stream")}
        response = requests.post(args.endpoint, files=files, timeout=10)

    print(f"Status: {response.status_code}")
    try:
        payload = response.json()
    except ValueError:
        print(response.text)
        raise SystemExit(1)

    print(payload)


if __name__ == "__main__":
    main()
