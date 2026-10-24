import requests

API_BASE_URL = "http://localhost:5000"


def get_health_status():
    response = requests.get(f"{API_BASE_URL}/health", timeout=10)
    response.raise_for_status()
    return response.json()


def predict_profile(profile_data, program_type):
    endpoint = f"{API_BASE_URL}/predict/{program_type}"
    response = requests.post(endpoint, json=profile_data, timeout=15)
    response.raise_for_status()
    return response.json()


def match_universities(payload):
    response = requests.post(f"{API_BASE_URL}/match", json=payload, timeout=15)
    response.raise_for_status()
    return response.json()
