import requests
import json
import os
import sys
from datetime import datetime
import pandas as pd
import io
import time

class RAGSaaSAPITester:
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

    def test_health_check(self):
        """Test the health check endpoint"""
        success, response = self.run_test(
            "Health Check",
            "GET",
            "health",
            200
        )
        return success

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

    def create_sample_excel(self):
        """Create a sample Excel file for testing"""
        # Create a sample DataFrame
        data = {
            'Name': ['John Doe', 'Jane Smith', 'Bob Johnson', 'Alice Brown'],
            'Age': [30, 25, 45, 35],
            'City': ['New York', 'Los Angeles', 'Chicago', 'Houston'],
            'Sales': [5000, 6000, 4500, 7500]
        }
        df = pd.DataFrame(data)
        
        # Save to a BytesIO object
        excel_file = io.BytesIO()
        df.to_excel(excel_file, index=False)
        excel_file.seek(0)
        
        return excel_file

    def test_upload_document(self):
        """Test document upload"""
        excel_file = self.create_sample_excel()
        
        files = {
            'file': ('test_data.xlsx', excel_file, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        }
        
        success, response = self.run_test(
            "Document Upload",
            "POST",
            "documents/upload",
            200,
            files=files
        )
        
        if success and 'document_id' in response:
            self.document_id = response['document_id']
            print(f"Uploaded document ID: {self.document_id}")
            return True
        return False

    def test_list_documents(self):
        """Test document listing"""
        success, response = self.run_test(
            "List Documents",
            "GET",
            "documents",
            200
        )
        
        if success and isinstance(response, list):
            print(f"Found {len(response)} documents")
            return True
        return False

    def test_query(self, query_text="What is the total sales?", language="en"):
        """Test RAG query"""
        success, response = self.run_test(
            f"RAG Query ({language})",
            "POST",
            "query",
            200,
            data={
                "query": query_text,
                "language": language
            }
        )
        
        if success and 'answer' in response:
            print(f"Query answer: {response['answer'][:100]}...")
            return True
        return False

    def test_report_generation(self, query_text="What is the total sales?", language="en"):
        """Test report generation"""
        success, response = self.run_test(
            f"Report Generation ({language})",
            "POST",
            "reports/generate",
            200,
            data={
                "query": query_text,
                "language": language
            }
        )
        
        if success and 'excel_data' in response:
            print(f"Excel report generated successfully")
            return True
        return False
        
    def test_delete_document(self):
        """Test document deletion"""
        if not self.document_id:
            print("❌ No document ID available for deletion test")
            return False
            
        success, delete_response = self.run_test(
            "Document Deletion",
            "DELETE",
            f"documents/{self.document_id}",
            200
        )
        
        if success:
            print(f"Document deleted successfully: {self.document_id}")
            # Verify document is gone by listing documents
            list_success, list_response = self.run_test(
                "Verify Document Deletion",
                "GET",
                "documents",
                200
            )
            
            if list_success:
                # Check if the deleted document is no longer in the list
                deleted = True
                for doc in list_response:
                    if doc.get('id') == self.document_id:
                        deleted = False
                        break
                
                if deleted:
                    print("✅ Document deletion verified")
                    return True
                else:
                    print("❌ Document still exists after deletion")
                    return False
        
        return False

def main():
    # Get the backend URL from environment variable
    backend_url = os.environ.get('REACT_APP_BACKEND_URL', 'https://d0b63582-cba0-4fa1-8fc8-c08eedc81deb.preview.emergentagent.com')
    
    print(f"Testing RAG SaaS API at: {backend_url}")
    tester = RAGSaaSAPITester(backend_url)
    
    # Run tests
    health_check_success = tester.test_health_check()
    if not health_check_success:
        print("❌ Health check failed, stopping tests")
        return 1
    
    register_success = tester.test_register()
    if not register_success:
        print("❌ Registration failed, trying login instead")
        login_success = tester.test_login()
        if not login_success:
            print("❌ Login also failed, stopping tests")
            return 1
    
    # Test document upload
    upload_success = tester.test_upload_document()
    if not upload_success:
        print("❌ Document upload failed, stopping tests")
        return 1
    
    # Test document listing
    list_success = tester.test_list_documents()
    if not list_success:
        print("❌ Document listing failed")
    
    # Wait a bit for embeddings to be processed
    print("Waiting 5 seconds for document processing...")
    time.sleep(5)
    
    # Test RAG query in English
    query_en_success = tester.test_query("What is the total sales?", "en")
    if not query_en_success:
        print("❌ English query failed")
    
    # Test RAG query in Indonesian
    query_id_success = tester.test_query("Berapa total penjualan?", "id")
    if not query_id_success:
        print("❌ Indonesian query failed")
    
    # Test report generation
    report_success = tester.test_report_generation("What is the total sales?", "en")
    if not report_success:
        print("❌ Report generation failed")
    
    # Test document deletion
    delete_success = tester.test_delete_document()
    if not delete_success:
        print("❌ Document deletion failed")
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())