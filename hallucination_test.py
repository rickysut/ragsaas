import requests
import json
import os
import sys
from datetime import datetime
import pandas as pd
import io
import time

class RAGHallucinationTester:
    def __init__(self, base_url):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.user_email = f"test{int(time.time())}@example.com"
        self.user_password = "testpass123"
        self.user_name = "Test User"
        self.document_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                if files:
                    # For file uploads, don't use JSON content type
                    headers.pop('Content-Type', None)
                    response = requests.post(url, headers=headers, files=files)
                else:
                    response = requests.post(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)
            
            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json()
                except:
                    return success, {}
            else:
                print(f"❌ Failed - Status: {response.status_code}")
                try:
                    error_detail = response.json().get('detail', 'No detail provided')
                    print(f"Error: {error_detail}")
                except:
                    print(f"Response: {response.text}")
                return False, {}
                
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_register(self):
        """Test user registration"""
        success, response = self.run_test(
            "User Registration",
            "POST",
            "auth/register",
            200,
            data={
                "email": self.user_email,
                "password": self.user_password,
                "name": self.user_name
            }
        )
        
        if success and 'token' in response:
            self.token = response['token']
            print(f"Registered user: {self.user_email}")
            return True
        return False

    def test_login(self):
        """Test user login"""
        success, response = self.run_test(
            "User Login",
            "POST",
            "auth/login",
            200,
            data={
                "email": self.user_email,
                "password": self.user_password
            }
        )
        
        if success and 'token' in response:
            self.token = response['token']
            print(f"Logged in as: {self.user_email}")
            return True
        return False

    def create_test_excel_for_hallucination(self):
        """Create a test Excel file with specific data for hallucination testing"""
        # Create test data with specific types including 05R
        data = {
            'Item_Name': ['Item A', 'Item B', 'Item C', 'Item D', 'Item E'],
            'Type': ['05R', '06S', '05R', '07T', '05R'],
            'Quantity': [10, 15, 8, 12, 20],
            'Price': [1000, 1500, 800, 1200, 2000]
        }
        
        df = pd.DataFrame(data)
        
        # Save to a BytesIO object
        excel_file = io.BytesIO()
        df.to_excel(excel_file, index=False)
        excel_file.seek(0)
        
        return excel_file

    def test_upload_hallucination_test_document(self):
        """Upload the hallucination test document"""
        excel_file = self.create_test_excel_for_hallucination()
        
        files = {
            'file': ('hallucination_test.xlsx', excel_file, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        }
        
        success, response = self.run_test(
            "Hallucination Test Document Upload",
            "POST",
            "documents/upload",
            200,
            files=files
        )
        
        if success and 'document_id' in response:
            self.document_id = response['document_id']
            print(f"Uploaded hallucination test document ID: {self.document_id}")
            return True
        return False

    def test_hallucination_query(self, query_text, language="en"):
        """Test RAG query for hallucination"""
        success, response = self.run_test(
            f"Hallucination Test Query: '{query_text}'",
            "POST",
            "query",
            200,
            data={
                "query": query_text,
                "language": language
            }
        )
        
        if success and 'answer' in response:
            print(f"Query answer: {response['answer']}")
            print(f"Context used: {json.dumps(response['context_used'], indent=2)}")
            
            # Check if the context only contains 05R items
            hallucination_detected = False
            non_05r_items = []
            
            for context in response['context_used']:
                # Parse the context to check for type
                if '|' in context:
                    pairs = context.split(' | ')
                    item_type = None
                    item_name = None
                    
                    for pair in pairs:
                        if ':' in pair:
                            key, value = pair.split(':', 1)
                            key = key.strip()
                            value = value.strip()
                            
                            if key == 'Type':
                                item_type = value
                            elif key == 'Item_Name':
                                item_name = value
                    
                    if item_type and item_type != '05R':
                        hallucination_detected = True
                        non_05r_items.append(f"{item_name} (Type: {item_type})")
            
            if hallucination_detected:
                print(f"❌ HALLUCINATION DETECTED: Query for '05R' returned non-05R items: {', '.join(non_05r_items)}")
                return False
            else:
                print(f"✅ No hallucination detected: Only 05R items were returned")
                return True
        
        return False

def main():
    # Get the backend URL from environment variable
    backend_url = os.environ.get('REACT_APP_BACKEND_URL', 'https://d0b63582-cba0-4fa1-8fc8-c08eedc81deb.preview.emergentagent.com')
    
    print(f"Testing RAG System for Hallucination at: {backend_url}")
    tester = RAGHallucinationTester(backend_url)
    
    # Run authentication tests
    register_success = tester.test_register()
    if not register_success:
        print("❌ Registration failed, trying login instead")
        login_success = tester.test_login()
        if not login_success:
            print("❌ Login also failed, stopping tests")
            return 1
    
    # Upload test document
    upload_success = tester.test_upload_hallucination_test_document()
    if not upload_success:
        print("❌ Document upload failed, stopping tests")
        return 1
    
    # Wait for document processing
    print("Waiting 5 seconds for document processing...")
    time.sleep(5)
    
    # Test queries for hallucination
    hallucination_tests = [
        {"query": "Show me all items with type 05R", "language": "en"},
        {"query": "Tampilkan barang dengan tipe 05R", "language": "id"},
        {"query": "What items have type 05R?", "language": "en"},
        {"query": "Berapa jumlah barang tipe 05R?", "language": "id"}
    ]
    
    hallucination_results = []
    
    for test in hallucination_tests:
        print(f"\n===== TESTING: {test['query']} =====")
        result = tester.test_hallucination_query(test['query'], test['language'])
        hallucination_results.append({
            "query": test['query'],
            "language": test['language'],
            "passed": result
        })
    
    # Print summary
    print("\n===== HALLUCINATION TEST SUMMARY =====")
    for result in hallucination_results:
        status = "✅ PASSED" if result['passed'] else "❌ FAILED (Hallucination Detected)"
        print(f"{status} - Query: '{result['query']}' ({result['language']})")
    
    # Overall results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    
    # Check if any hallucination was detected
    hallucination_detected = any(not result['passed'] for result in hallucination_results)
    if hallucination_detected:
        print("❌ HALLUCINATION DETECTED: The RAG system is returning non-05R items when queried for 05R items.")
    else:
        print("✅ NO HALLUCINATION DETECTED: The RAG system correctly returns only 05R items when queried.")
    
    return 0 if not hallucination_detected else 1

if __name__ == "__main__":
    sys.exit(main())