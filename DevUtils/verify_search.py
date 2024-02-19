import os
import sys
import json
import requests

def make_post_request(url, data, bearer_token=None, verify_ssl=True):
    headers = {}

    if bearer_token:
        headers['Authorization'] = f'Bearer {bearer_token}'

    try:
        response = requests.post(url, data=data, headers=headers, verify=verify_ssl)
        response.raise_for_status()

        print(f"POST Request to {url} was successful.")
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Body:\n{response.text}")

    except requests.exceptions.RequestException as e:
        print(f"POST Request to {url} failed with error: {e}")
        sys.exit(1)

def main():
    if len(sys.argv) < 3:
        print("Usage: python verify_search.py <URL> <JSON_DATA> [BEARER_TOKEN] [VERIFY_SSL]")
        print("Usage: Where <URL> is a fully formed search URL")
        print("Usage: Where <JSON_DATA> is post data")
        print("Usage: Where [BEARER_TOKEN] is an optional Bearer token")
        print("Usage: Where [VERIFY_SSL] an optional path to a cert or pem file or a True/False value")
        sys.exit(1)

    url = sys.argv[1]
    json_data = json.loads(sys.argv[2])

    bearer_token = sys.argv[3] if len(sys.argv) > 3 else None
    verify_ssl = sys.argv[4] if len(sys.argv) > 4 else True

    # Check if verify_ssl is a file path
    if verify_ssl and not os.path.exists(verify_ssl):
        verify_ssl = (False if verify_ssl.lower() == 'false' else True)

    make_post_request(url, json_data, bearer_token, verify_ssl)

if __name__ == "__main__":
    main()
