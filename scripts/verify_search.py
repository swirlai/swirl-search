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
        sys.exit(1)

    url = sys.argv[1]
    json_data = json.loads(sys.argv[2])

    bearer_token = sys.argv[3] if len(sys.argv) > 3 else None
    verify_ssl = sys.argv[4] if len(sys.argv) > 4 else False

    make_post_request(url, json_data, bearer_token, verify_ssl)

if __name__ == "__main__":
    main()
