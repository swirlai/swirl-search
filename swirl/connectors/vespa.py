import requests

class VespaClient:
    def __init__(self, vespa_endpoint):
        self.vespa_endpoint = vespa_endpoint

    def search(self, query):
        url = f"{self.vespa_endpoint}/search/"
        params = {"query": query}
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code}")
            return None

if __name__ == "__main__":
    vespa_endpoint = "https://<your-vespa-endpoint>"
    vespa_client = VespaClient(vespa_endpoint)

    query = input("Enter your search query: ")
    results = vespa_client.search(query)

    if results:
        print("Search results:")
        for result in results["results"]:
            print(result)
    else:
        print("No results found.")
