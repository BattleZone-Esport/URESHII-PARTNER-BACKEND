"""
Simple test script to verify API endpoints
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("Testing /health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    print("✓ Health check passed\n")

def test_chat():
    """Test chat endpoint"""
    print("Testing /chat endpoint...")
    payload = {
        "message": "How do I create a REST API in Python?",
        "skill_level": "intermediate",
        "preferences": {
            "languages": ["Python"],
            "frameworks": ["FastAPI"]
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/chat",
        json=payload,
        params={"user_id": "test_user"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200
    print("✓ Chat endpoint passed\n")

def test_history():
    """Test history endpoint"""
    print("Testing /history endpoint...")
    response = requests.get(f"{BASE_URL}/history/test_user")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200
    print("✓ History endpoint passed\n")

def test_suggestions():
    """Test suggestions endpoint"""
    print("Testing /suggest endpoint...")
    response = requests.get(f"{BASE_URL}/suggest/test_user")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200
    print("✓ Suggestions endpoint passed\n")

def run_tests():
    """Run all tests"""
    print("=" * 50)
    print("Starting API Tests")
    print("=" * 50 + "\n")
    
    try:
        test_health()
        test_chat()
        time.sleep(1)  # Avoid rate limiting
        test_history()
        test_suggestions()
        
        print("=" * 50)
        print("All tests passed! ✓")
        print("=" * 50)
    except AssertionError as e:
        print(f"Test failed: {e}")
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to API. Make sure the server is running.")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    run_tests()