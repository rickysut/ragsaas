import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useDropzone } from 'react-dropzone';
import { Download, Upload, MessageCircle, FileText, User, LogOut, Search, Database, Trash2, Grid } from 'lucide-react';
import * as XLSX from 'xlsx';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Auth context
const AuthContext = React.createContext();

function App() {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));

  useEffect(() => {
    if (token) {
      // Verify token validity
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      // You could add a token verification endpoint here
    }
  }, [token]);

  const login = (userData, authToken) => {
    setUser(userData);
    setToken(authToken);
    localStorage.setItem('token', authToken);
    axios.defaults.headers.common['Authorization'] = `Bearer ${authToken}`;
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout }}>
      <div className="App">
        {token ? <Dashboard /> : <AuthPage />}
      </div>
    </AuthContext.Provider>
  );
}

function AuthPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { login } = React.useContext(AuthContext);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const endpoint = isLogin ? '/auth/login' : '/auth/register';
      const payload = isLogin ? 
        { email: formData.email, password: formData.password } :
        { email: formData.email, password: formData.password, name: formData.name };

      const response = await axios.post(`${API}${endpoint}`, payload);
      login(response.data.user, response.data.token);
    } catch (err) {
      setError(err.response?.data?.detail || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl p-8">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-indigo-100 rounded-full mb-4">
            <Database className="w-8 h-8 text-indigo-600" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900">RAG SaaS</h1>
          <p className="text-gray-600 mt-2">AI-Powered Document Analysis & Reporting</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {!isLogin && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Nama Lengkap
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                required={!isLogin}
                placeholder="Masukkan nama lengkap Anda"
              />
            </div>
          )}
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Email
            </label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({...formData, email: e.target.value})}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              required
              placeholder="Masukkan email Anda"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Password
            </label>
            <input
              type="password"
              value={formData.password}
              onChange={(e) => setFormData({...formData, password: e.target.value})}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              required
              placeholder="Masukkan password Anda"
            />
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-indigo-600 text-white py-3 px-4 rounded-lg hover:bg-indigo-700 focus:ring-4 focus:ring-indigo-200 font-medium transition-colors disabled:opacity-50"
          >
            {loading ? 'Processing...' : (isLogin ? 'Masuk' : 'Daftar')}
          </button>
        </form>

        <div className="mt-6 text-center">
          <button
            onClick={() => setIsLogin(!isLogin)}
            className="text-indigo-600 hover:text-indigo-700 font-medium"
          >
            {isLogin ? 'Belum punya akun? Daftar di sini' : 'Sudah punya akun? Masuk di sini'}
          </button>
        </div>
      </div>
    </div>
  );
}

function Dashboard() {
  const [activeTab, setActiveTab] = useState('upload');
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const { user, logout } = React.useContext(AuthContext);

  const fetchDocuments = async () => {
    try {
      const response = await axios.get(`${API}/documents`);
      setDocuments(response.data);
    } catch (error) {
      console.error('Error fetching documents:', error);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-3">
              <Database className="w-8 h-8 text-indigo-600" />
              <h1 className="text-xl font-bold text-gray-900">RAG SaaS</h1>
            </div>
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <User className="w-5 h-5 text-gray-500" />
                <span className="text-gray-700">{user?.name}</span>
              </div>
              <button
                onClick={logout}
                className="flex items-center space-x-2 text-gray-500 hover:text-red-600 transition-colors"
              >
                <LogOut className="w-5 h-5" />
                <span>Keluar</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex space-x-8">
            <button
              onClick={() => setActiveTab('upload')}
              className={`py-4 px-2 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'upload'
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <Upload className="w-4 h-4 inline mr-2" />
              Upload Data
            </button>
            <button
              onClick={() => setActiveTab('query')}
              className={`py-4 px-2 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'query'
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <MessageCircle className="w-4 h-4 inline mr-2" />
              Query & Analysis
            </button>
            <button
              onClick={() => setActiveTab('documents')}
              className={`py-4 px-2 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'documents'
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <FileText className="w-4 h-4 inline mr-2" />
              Dokumen Saya
            </button>
          </nav>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'upload' && <UploadTab onUploadSuccess={fetchDocuments} />}
        {activeTab === 'query' && <QueryTab />}
        {activeTab === 'documents' && <DocumentsTab documents={documents} />}
      </div>
    </div>
  );
}

function UploadTab({ onUploadSuccess }) {
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);

  const onDrop = async (acceptedFiles) => {
    const file = acceptedFiles[0];
    if (!file) return;

    setUploading(true);
    setUploadResult(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API}/documents/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      setUploadResult({
        success: true,
        message: response.data.message,
        filename: response.data.filename,
        chunks_count: response.data.chunks_count,
        file_type: response.data.file_type
      });
      
      onUploadSuccess();
    } catch (error) {
      setUploadResult({
        success: false,
        message: error.response?.data?.detail || 'Upload failed'
      });
    } finally {
      setUploading(false);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'application/json': ['.json']
    },
    maxFiles: 1
  });

  return (
    <div className="max-w-2xl mx-auto">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors ${
          isDragActive
            ? 'border-indigo-400 bg-indigo-50'
            : 'border-gray-300 hover:border-indigo-400 hover:bg-gray-50'
        }`}
      >
        <input {...getInputProps()} />
        <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        {uploading ? (
          <div>
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Mengupload dan memproses file...</p>
          </div>
        ) : (
          <div>
            <p className="text-lg font-medium text-gray-900 mb-2">
              Drop file di sini atau klik untuk upload
            </p>
            <p className="text-gray-500">
              Mendukung Excel (.xlsx, .xls) dan JSON (.json)
            </p>
          </div>
        )}
      </div>

      {uploadResult && (
        <div className={`mt-6 p-6 rounded-lg ${
          uploadResult.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
        }`}>
          <div className={`font-medium ${uploadResult.success ? 'text-green-800' : 'text-red-800'}`}>
            {uploadResult.message}
          </div>
          {uploadResult.success && (
            <div className="mt-2 text-sm text-green-700">
              <p>File: {uploadResult.filename}</p>
              <p>Tipe: {uploadResult.file_type}</p>
              <p>Chunks diproses: {uploadResult.chunks_count}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function QueryTab() {
  const [query, setQuery] = useState('');
  const [language, setLanguage] = useState('id');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    try {
      const response = await axios.post(`${API}/query`, {
        query: query.trim(),
        language
      });
      setResult(response.data);
    } catch (error) {
      setResult({
        error: true,
        message: error.response?.data?.detail || 'Query failed'
      });
    } finally {
      setLoading(false);
    }
  };

  const generateReport = async () => {
    if (!query.trim()) return;

    try {
      const response = await axios.post(`${API}/reports/generate`, {
        query: query.trim(),
        language
      });
      
      // Convert base64 to blob and download
      const base64Data = response.data.excel_data;
      const binaryData = atob(base64Data);
      const bytes = new Uint8Array(binaryData.length);
      for (let i = 0; i < binaryData.length; i++) {
        bytes[i] = binaryData.charCodeAt(i);
      }
      
      const blob = new Blob([bytes], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      });
      
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = response.data.filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error generating report:', error);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow-sm border p-6 mb-6">
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Bahasa / Language
          </label>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          >
            <option value="id">Bahasa Indonesia</option>
            <option value="en">English</option>
          </select>
        </div>

        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            {language === 'id' ? 'Pertanyaan Anda' : 'Your Question'}
          </label>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            rows={4}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            placeholder={language === 'id' 
              ? 'Contoh: Berapa total penjualan bulan ini? Atau analisis data pelanggan yang sudah diupload...' 
              : 'Example: What is the total sales this month? Or analyze the customer data uploaded...'}
          />
        </div>

        <div className="flex space-x-3">
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="flex items-center space-x-2 bg-indigo-600 text-white px-6 py-3 rounded-lg hover:bg-indigo-700 focus:ring-4 focus:ring-indigo-200 font-medium transition-colors disabled:opacity-50"
          >
            <Search className="w-4 h-4" />
            <span>{loading ? 'Processing...' : (language === 'id' ? 'Analisis' : 'Analyze')}</span>
          </button>
          
          {result && !result.error && (
            <button
              type="button"
              onClick={generateReport}
              className="flex items-center space-x-2 bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 focus:ring-4 focus:ring-green-200 font-medium transition-colors"
            >
              <Download className="w-4 h-4" />
              <span>{language === 'id' ? 'Download Laporan' : 'Download Report'}</span>
            </button>
          )}
        </div>
      </form>

      {result && (
        <div className="bg-white rounded-lg shadow-sm border p-6">
          {result.error ? (
            <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg">
              {result.message}
            </div>
          ) : (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                {language === 'id' ? 'Hasil Analisis' : 'Analysis Result'}
              </h3>
              
              <div className="prose max-w-none mb-6">
                <div className="bg-gray-50 p-4 rounded-lg">
                  <p className="text-gray-800 leading-relaxed whitespace-pre-wrap">{result.answer}</p>
                </div>
              </div>
              
              {result.sources && result.sources.length > 0 && (
                <div className="mb-4">
                  <h4 className="text-md font-medium text-gray-900 mb-2">
                    {language === 'id' ? 'Sumber Data' : 'Data Sources'}
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {result.sources.map((source, index) => (
                      <span
                        key={index}
                        className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-indigo-100 text-indigo-700"
                      >
                        <FileText className="w-3 h-3 mr-1" />
                        {source}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function DocumentsTab({ documents }) {
  return (
    <div>
      <div className="bg-white rounded-lg shadow-sm border">
        <div className="px-6 py-4 border-b">
          <h3 className="text-lg font-semibold text-gray-900">Dokumen Saya</h3>
          <p className="text-gray-600">Total: {documents.length} dokumen</p>
        </div>
        
        <div className="divide-y">
          {documents.length === 0 ? (
            <div className="px-6 py-12 text-center">
              <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500">Belum ada dokumen yang diupload</p>
            </div>
          ) : (
            documents.map((doc) => (
              <div key={doc.id} className="px-6 py-4 hover:bg-gray-50">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium text-gray-900">{doc.filename}</h4>
                    <div className="flex items-center space-x-4 text-sm text-gray-500 mt-1">
                      <span className="capitalize">{doc.file_type}</span>
                      <span>{doc.chunks_count} chunks</span>
                      <span>{new Date(doc.uploaded_at).toLocaleDateString('id-ID')}</span>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      doc.processed 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {doc.processed ? 'Processed' : 'Processing'}
                    </span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

export default App;