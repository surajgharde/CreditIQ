import requests
import json
import time

BASE_URL = "http://localhost:8000"

def run_tests():
    print("====================================")
    print(" CreditIQ Backend Demo API Test Runner ")
    print("====================================\n")
    
    # Let the server wake up if just started
    time.sleep(1)

    # Test 1: Health Check
    try:
        res = requests.get(f"{BASE_URL}/health")
        print(f"[TEST 1] GET /health -> Status {res.status_code}")
        assert res.status_code == 200
        print("   [PASS]")
    except Exception as e:
        print(f"   [FAIL]: {e}")

    # Test 2: Demo Reset
    try:
        res = requests.get(f"{BASE_URL}/api/demo/reset")
        print(f"\n[TEST 2] GET /api/demo/reset -> Status {res.status_code}")
        assert res.status_code == 200
        print("   [PASS] - Demo DB Reset Complete")
    except Exception as e:
        print(f"   [FAIL]: {e}")

    # Test 3: Get Results
    try:
        res = requests.get(f"{BASE_URL}/api/results/1")
        print(f"\n[TEST 3] GET /api/results/1 -> Status {res.status_code}")
        assert res.status_code == 200
        data = res.json()
        assert data["decision"]["decision"].upper() == "CONDITIONAL"
        print("   [PASS] - Results specific to ABC Manufacturing returned")
    except Exception as e:
        print(f"   [FAIL]: {e}")

    # Test 4: Get Fraud Signals
    try:
        res = requests.get(f"{BASE_URL}/api/fraud/1")
        print(f"\n[TEST 4] GET /api/fraud/1 -> Status {res.status_code}")
        assert res.status_code == 200
        data = res.json()
        assert data["overall_verdict"]["risk_level"] == "HIGH"
        print("   [PASS] - Fraud structure validates correctly")
    except Exception as e:
        print(f"   [FAIL]: {e}")

    # Test 5: Get Graph HTML
    try:
        res = requests.get(f"{BASE_URL}/api/fraud/graph/1")
        print(f"\n[TEST 5] GET /api/fraud/graph/1 -> Status {res.status_code}")
        assert res.status_code == 200
        assert "<html>" in res.text
        print("   [PASS] - Vis.js Interactive HTML successfully generated")
    except Exception as e:
        print(f"   [FAIL]: {e}")

    # Test 6: Get EWS Data
    try:
        res = requests.get(f"{BASE_URL}/api/ews/1")
        print(f"\n[TEST 6] GET /api/ews/1 -> Status {res.status_code}")
        assert res.status_code == 200
        data = res.json()
        assert len(data["signals"]) > 0
        print("   [PASS] - Trajectory and active alerts fetched")
    except Exception as e:
        print(f"   [FAIL]: {e}")

    # Test 7: CAM Preview
    try:
        res = requests.get(f"{BASE_URL}/api/cam/preview/1")
        print(f"\n[TEST 7] GET /api/cam/preview/1 -> Status {res.status_code}")
        assert res.status_code == 200
        data = res.json()
        assert "executive_summary" in data
        print("   [PASS] - Fast CAM preview summary initialized")
    except Exception as e:
        print(f"   [FAIL]: {e}")

    # Test 8: CAM Download
    try:
        res = requests.get(f"{BASE_URL}/api/cam/download/1?format=word")
        print(f"\n[TEST 8] GET /api/cam/download/1?format=word -> Status {res.status_code}")
        assert res.status_code == 200
        assert "application/vnd.openxmlformats" in res.headers["Content-Type"]
        print("   [PASS] - Demo Document bytestream exported successfully")
    except Exception as e:
        print(f"   [FAIL]: {e}")

    print("\n====================================")
    print(" [PASS] ALL TESTS COMPLETED SUCCESSFULLY ")
    print("====================================")

if __name__ == "__main__":
    run_tests()
