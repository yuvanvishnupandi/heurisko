import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { 
  Search, Brain, FileText, CheckCircle2, AlertCircle, ExternalLink,
  Plus, Home, User, LogIn, LogOut, ChevronRight, MessageSquare, Menu, BookOpen,
  Library, Bell, Settings, Database, Filter, SlidersHorizontal, History,
  PanelLeftClose, PanelLeftOpen, Eye, EyeOff, Trash2, Paperclip
} from 'lucide-react';
import './index.css';
import { jellyTriangle } from 'ldrs';

jellyTriangle.register();

const MAX_SUMMARY_WORDS = 150;

function truncate(text, words = MAX_SUMMARY_WORDS) {
  if (!text) return "";
  const parts = text.split(" ");
  return parts.length <= words ? text : parts.slice(0, words).join(" ") + " …";
}

function App() {
  // Auth State
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoginMode, setIsLoginMode] = useState(true); // true = Login, false = Register
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  // Search State
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('idle'); // idle, running, completed, error
  const [messages, setMessages] = useState([]); // Stores chat history: [{role: 'user', content: '...'}, {role: 'assistant', content: {summary: '...'}}]
  const [currentHistoryId, setCurrentHistoryId] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);
  const [taskId, setTaskId] = useState(null);
  
  const [showFullSummary, setShowFullSummary] = useState(false);
  const [expandedSections, setExpandedSections] = useState({});
  const [historyList, setHistoryList] = useState([]); // Array of {query, id}
  const [uploadedFile, setUploadedFile] = useState(null);
  const [fileContent, setFileContent] = useState(null);
  const [loadingPhraseIndex, setLoadingPhraseIndex] = useState(0);

  const loadingPhrases = [
    "Scouring the web for sources...",
    "Analyzing research papers...",
    "Extracting key methodologies...",
    "Comparing findings across studies...",
    "Synthesizing final research report..."
  ];

  // Rotates through loading phrases to keep the user entertained!
  useEffect(() => {
    let interval;
    if (status === 'running') {
      interval = setInterval(() => {
        setLoadingPhraseIndex((prev) => (prev + 1) % loadingPhrases.length);
      }, 3500);
    } else {
      setLoadingPhraseIndex(0);
    }
    return () => clearInterval(interval);
  }, [status]);

  const pollingIntervalRef = useRef(null);
  const fileInputRef = useRef(null);

  const handleFileChange = async (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setUploadedFile(file.name);
      
      const formData = new FormData();
      formData.append('file', file);
      
      try {
        const response = await fetch('http://localhost:8000/extract-text', {
          method: 'POST',
          body: formData,
        });
        
        if (response.ok) {
          const data = await response.json();
          setFileContent(data.text);
        } else {
          alert('Failed to extract text from file.');
          setUploadedFile(null);
        }
      } catch (err) {
        console.error('Error uploading file:', err);
        alert('Error uploading file.');
        setUploadedFile(null);
      }
    }
  };

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      setIsAuthenticated(true);
      fetchHistory(token);
    }
  }, []);

  const fetchHistory = async (token) => {
    try {
      const res = await fetch('http://localhost:8000/history', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (res.status === 401) {
        localStorage.removeItem('token');
        localStorage.removeItem('email');
        setIsAuthenticated(false);
        return;
      }
      if (res.ok) {
        const data = await res.json();
        setHistoryList(data);
      }
    } catch (e) {
      console.error('Failed to fetch history', e);
    }
  };

  const loadHistoryItem = async (id) => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`http://localhost:8000/history/${id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.status === 401) {
        localStorage.removeItem('token');
        localStorage.removeItem('email');
        setIsAuthenticated(false);
        return;
      }
      if (res.ok) {
        const data = await res.json();
        setQuery('');
        setCurrentHistoryId(id);
        if (data.messages && data.messages.length > 0) {
          setMessages(data.messages);
          setStatus('completed');
        } else {
          setMessages([]);
          startSearch(null, data.query);
        }
      }
    } catch (e) {
      console.error('Failed to load history item', e);
    }
  };

  const deleteHistoryItem = async (e, id) => {
    e.stopPropagation();
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`http://localhost:8000/history/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        setHistoryList(historyList.filter(item => item.id !== id));
        if (taskId === id || currentHistoryId === id) {
           resetSearch();
        }
      }
    } catch (e) {
      console.error('Failed to delete history item', e);
    }
  };

  const handleAuth = async (e) => {
    e.preventDefault();
    if (!authEmail || !authPassword) return;
    
    try {
      const endpoint = isLoginMode ? '/auth/login' : '/auth/register';
      const response = await fetch(`http://localhost:8000${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: authEmail, password: authPassword })
      });
      
      if (!response.ok) {
        const errData = await response.json();
        alert(errData.detail || 'Authentication failed');
        return;
      }
      
      const data = await response.json();
      localStorage.setItem('token', data.access_token);
      localStorage.setItem('email', data.email);
      setIsAuthenticated(true);
      fetchHistory(data.access_token);
    } catch (err) {
      alert('Network error connecting to server');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('email');
    setIsAuthenticated(false);
    setMessages([]);
    setCurrentHistoryId(null);
    setStatus('idle');
    setQuery('');
    setHistoryList([]);
  };

  const startSearch = async (e, forcedQuery = null) => {
    if (e) e.preventDefault();
    const q = forcedQuery || query;
    if (!q.trim()) return;

    setStatus('running');
    setErrorMsg(null);
    setTaskId(null);
    
    // Add user message immediately
    setMessages(prev => [...prev, {role: 'user', content: q}]);
    setQuery(''); // clear input box
    
    // Create a temporary ID just in case
    const tempId = currentHistoryId || Date.now();

    // Optimistically update history list locally only if it's a new thread
    if (!currentHistoryId) {
      setHistoryList(prev => [{ id: tempId, query: q }, ...prev]);
    }

    try {
      const token = localStorage.getItem('token');
      const headers = { 'Content-Type': 'application/json' };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const finalQuery = fileContent ? `${q}\n\nUploaded Document Context:\n${fileContent}` : q;

      const payload = {
        query: finalQuery,
        language: 'en',
        chat_history: messages,
        history_id: currentHistoryId
      };

      const response = await fetch('http://localhost:8000/research', {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const data = await response.json();
      setTaskId(data.task_id);
      
      // If the backend gave us the real history ID (new thread), update it!
      if (data.history_id && !currentHistoryId) {
        setCurrentHistoryId(data.history_id);
        setHistoryList(prev => prev.map(item => item.id === tempId ? { ...item, id: data.history_id } : item));
      }
    } catch (err) {
      setStatus('error');
      setErrorMsg(err.message || 'Failed to start research.');
    }
  };

  // Automatically poll the backend for research results every 2 seconds
  useEffect(() => {
    if (taskId && status === 'running') {
      pollingIntervalRef.current = setInterval(async () => {
        try {
          const res = await fetch(`http://localhost:8000/results/${taskId}`);
          if (res.ok) {
            const data = await res.json();
            if (data.status === 'completed') {
              setStatus('completed');
              // Append AI response
              if (data.result) {
                setMessages(prev => [...prev, {role: 'assistant', content: data.result}]);
              }
              clearInterval(pollingIntervalRef.current);
            } else if (data.status === 'error') {
              setStatus('error');
              setErrorMsg(data.error?.details || data.error?.error || 'An error occurred during research.');
              clearInterval(pollingIntervalRef.current);
            }
          }
        } catch (err) {
          console.error("Polling error", err);
        }
      }, 2000);
    }

    return () => {
      if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
    };
  }, [taskId, status]);

  const toggleSection = (idx) => {
    setExpandedSections(prev => ({ ...prev, [idx]: !prev[idx] }));
  };

  // --- Auth Screen (Consensus Layout, Elicit Colors) ---
  if (!isAuthenticated) {
    return (
      <div className="flex h-screen bg-background text-text font-sans relative z-0">
        {/* Left Sidebar Info (Consensus Style Layout, Light Theme) */}
        <div className={`${isSidebarOpen ? 'w-[320px]' : 'w-[80px]'} bg-sidebar border-r border-border flex flex-col items-center shrink-0 h-full py-6 px-4 hidden md:flex z-10 relative transition-all duration-300`}>
          
          <div className={`flex items-center ${isSidebarOpen ? 'justify-start w-full px-2' : 'justify-center'} mb-10`}>
            <img src="/logo.png" alt="Heurisko Logo" className="w-6 h-6 rounded" />
            {isSidebarOpen && <span className="font-bold text-lg text-primary tracking-wide ml-2">Heurisko</span>}
          </div>
          
          <button className={`flex items-center ${isSidebarOpen ? 'w-full justify-start px-4' : 'w-12 h-12 justify-center shrink-0'} py-3 bg-primary text-white rounded-full text-sm font-semibold hover:bg-primary/90 transition-colors mb-2 shadow-sm cursor-pointer`}>
            <Plus className="w-5 h-5 shrink-0" /> {isSidebarOpen && <span className="ml-3">New Thread</span>}
          </button>
          
          <button onClick={() => setIsAuthenticated(true)} className={`flex items-center ${isSidebarOpen ? 'w-full justify-start px-4' : 'w-12 h-12 justify-center shrink-0'} py-3 rounded-full text-sm font-medium hover:bg-gray-200 transition-colors mb-12 text-gray-800 bg-gray-100 cursor-pointer`}>
            <Home className="w-5 h-5 text-gray-600 shrink-0" /> {isSidebarOpen && <span className="ml-3">Home</span>}
          </button>

          {isSidebarOpen && (
            <div className="mt-4 text-text fade-in duration-300 w-full px-4">
              <h1 className="text-[32px] font-bold mb-4 tracking-tight leading-tight text-gray-900">Research<br/>starts here</h1>
              <p className="text-gray-600 text-sm mb-8 leading-relaxed">
                Heurisko is the AI-powered academic search engine
              </p>
              
              <div className="space-y-4 pr-4">
                <p className="text-sm font-semibold leading-relaxed bg-primary text-white px-4 py-3 rounded-lg inline-block shadow-sm w-full">
                  Search & analyze millions of research papers instantly
                </p>
                <p className="text-sm font-semibold leading-relaxed bg-primary/10 text-primary px-4 py-3 rounded-lg inline-block w-full">
                  Transparent, reliable, and built to streamline your workflow
                </p>
              </div>
            </div>
          )}

          {isSidebarOpen && (
            <div className="mt-auto flex flex-col gap-3 pb-4 fade-in duration-300 w-full px-4">
               <button onClick={() => setIsLoginMode(true)} className={`w-full rounded-full py-2.5 text-sm font-semibold transition-all active:scale-95 border shadow-sm ${isLoginMode ? 'bg-primary text-white border-primary' : 'bg-transparent text-gray-700 border-gray-300 hover:bg-gray-50'}`}>Sign in</button>
               <button onClick={() => setIsLoginMode(false)} className={`w-full rounded-full py-2.5 text-sm font-semibold transition-all active:scale-95 border shadow-sm ${!isLoginMode ? 'bg-primary text-white border-primary' : 'bg-transparent text-gray-700 border-gray-300 hover:bg-gray-50'}`}>Sign up</button>
            </div>
          )}
        </div>

        {/* Right Auth Panel */}
        <div className="flex-1 flex flex-col items-center justify-center bg-background p-8 relative z-10 overflow-hidden">
          
          {/* Floating Sidebar Toggle (Claude/Consensus Style) */}
          <div className="absolute top-6 left-6 z-20">
            <button onClick={() => setIsSidebarOpen(!isSidebarOpen)} className="w-8 h-8 rounded-md flex items-center justify-center text-gray-500 hover:bg-gray-200 transition-colors">
              {isSidebarOpen ? <PanelLeftClose className="w-5 h-5" /> : <PanelLeftOpen className="w-5 h-5" />}
            </button>
          </div>
          <div className="w-full max-w-[500px] flex flex-col items-center">
            
            <div className="text-center mb-10 flex flex-col items-center">
              <div className="flex justify-center mb-5 items-center gap-3">
                 <img src="/logo.png" alt="Heurisko Logo" className="w-10 h-10 rounded" />
                 <span className="font-bold text-2xl text-primary tracking-wide">Heurisko</span>
              </div>
              <h2 className="text-[32px] font-bold text-gray-900 mb-2">Research starts here</h2>
            </div>

            <form onSubmit={handleAuth} className="w-full space-y-5">
              <div>
                <input
                  type="email"
                  placeholder="Enter your email"
                  value={authEmail}
                  onChange={(e) => setAuthEmail(e.target.value)}
                  className="w-full bg-transparent border-2 border-gray-200 rounded-xl px-5 py-4 text-base focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all text-gray-900 placeholder:text-gray-400"
                  required
                />
              </div>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter your password"
                  value={authPassword}
                  onChange={(e) => setAuthPassword(e.target.value)}
                  className="w-full bg-transparent border-2 border-gray-200 rounded-xl px-5 py-4 text-base focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all text-gray-900 placeholder:text-gray-400 pr-12"
                  required
                />
                <button 
                  type="button" 
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors p-1"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
              
              <div className="flex items-center my-8 py-2">
                <div className="flex-1 border-t-2 border-gray-100"></div>
                <span className="px-6 text-xs text-gray-400 uppercase font-bold tracking-widest">or</span>
                <div className="flex-1 border-t-2 border-gray-100"></div>
              </div>

              <button 
                type="submit"
                className="w-full bg-primary text-white rounded-full py-4 text-base font-bold hover:bg-primary/90 transition-all shadow-md transform hover:scale-[1.01]"
              >
                {isLoginMode ? 'Sign In' : 'Sign Up'}
              </button>
            </form>

            <p className="text-center text-xs text-gray-500 mt-10">
              By continuing, you agree to our <span className="text-gray-700 underline hover:text-primary">Terms of Service</span> and <span className="text-gray-700 underline hover:text-primary">Privacy Policy</span>.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // --- Main App Screen (Consensus Search Layout, Light Theme) ---
  const isResearching = status === 'running';
  const hasSearched = status !== 'idle';
  const handleSearch = startSearch;
  const resetSearch = () => { setStatus('idle'); setMessages([]); setCurrentHistoryId(null); setQuery(''); setUploadedFile(null); setFileContent(null); };

  return (
    <div className="flex h-screen bg-background text-text font-sans relative z-0">
        
        {/* Left Sidebar (Main App) */}
        <div className={`${isSidebarOpen ? 'w-[320px]' : 'w-[80px]'} bg-sidebar border-r border-border flex flex-col items-center shrink-0 h-full py-6 px-4 hidden md:flex z-10 relative transition-all duration-300`}>
          
          <div className={`flex items-center ${isSidebarOpen ? 'justify-start w-full px-2' : 'justify-center'} mb-8`}>
            <img src="/logo.jpg" alt="Heurisko Logo" className="w-6 h-6 rounded" />
            {isSidebarOpen && <span className="font-bold text-lg text-primary tracking-wide ml-2">Heurisko</span>}
          </div>
          
          <button onClick={resetSearch} className={`flex items-center ${isSidebarOpen ? 'w-full justify-start px-4' : 'w-12 h-12 justify-center shrink-0'} py-3 bg-primary text-white rounded-full text-sm font-semibold hover:bg-primary/90 transition-all active:scale-95 mb-6 shadow-sm cursor-pointer`}>
            <Plus className="w-4 h-4 shrink-0" /> {isSidebarOpen && <span className="ml-3">New Thread</span>}
          </button>

          {isSidebarOpen && (
            <div className="w-full mb-6 fade-in flex-1 overflow-y-auto custom-scrollbar">
              <p className="px-4 text-xs font-bold text-gray-400 mb-3 uppercase tracking-wider">Chat History</p>
              <div className="flex flex-col space-y-1 px-2">
                {historyList.length === 0 ? (
                  <p className="px-2 text-sm text-gray-500 italic">No recent chats.</p>
                ) : (
                  historyList.map((item, idx) => (
                    <div key={idx} className="flex items-center w-full justify-between px-3 py-2.5 rounded-lg hover:bg-gray-100 transition-all group cursor-pointer" onClick={() => loadHistoryItem(item.id)}>
                      <button className="flex items-center text-sm font-medium text-gray-600 group-hover:text-gray-900 transition-colors text-left truncate flex-1 min-w-0">
                        <MessageSquare className="w-4 h-4 shrink-0 opacity-50 group-hover:opacity-100 transition-opacity mr-3" /> 
                        <span className="truncate">{item.query}</span>
                      </button>
                      <button onClick={(e) => deleteHistoryItem(e, item.id)} className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-md shrink-0">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          <div className="mt-auto w-full flex flex-col pt-4 border-t border-gray-100">
            <div className={`flex flex-col gap-3 fade-in duration-300 w-full ${isSidebarOpen ? 'px-4' : 'px-0 items-center'}`}>
               
               <div className="flex items-center gap-3 w-full justify-between py-2">
                 <div className="flex items-center gap-3">
                   <div className="w-9 h-9 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold shrink-0 shadow-sm border border-primary/20">
                     {localStorage.getItem('email') ? localStorage.getItem('email').charAt(0).toUpperCase() : 'U'}
                   </div>
                   {isSidebarOpen && <span className="text-sm font-semibold text-gray-800 truncate max-w-[120px]">{localStorage.getItem('email') || 'User'}</span>}
                 </div>
                 {isSidebarOpen && (
                   <button onClick={handleLogout} className="text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors p-2 rounded-md" title="Log Out">
                     <LogOut className="w-4 h-4" />
                   </button>
                 )}
               </div>
               
            </div>
          </div>
        </div>

        {/* Right Main Panel */}
        <div className="flex-1 flex flex-col relative z-10 overflow-hidden bg-background">
          
          {/* Floating Sidebar Toggle (Claude/Consensus Style) */}
          <div className="absolute top-6 left-6 z-20">
            <button onClick={() => setIsSidebarOpen(!isSidebarOpen)} className="w-8 h-8 rounded-md flex items-center justify-center text-gray-500 hover:bg-gray-200 transition-colors">
              {isSidebarOpen ? <PanelLeftClose className="w-5 h-5" /> : <PanelLeftOpen className="w-5 h-5" />}
            </button>
          </div>

          <div className="flex-1 flex flex-col items-center justify-center p-8 w-full overflow-y-auto custom-scrollbar">
            
            {/* Default Search State (Landing Page) */}
            {!hasSearched && !isResearching && (
              <div className="w-full flex flex-col items-center max-w-[760px] mx-auto fade-in">
                {/* Logo and Title */}
                <div className="flex flex-col items-center mb-8">
                  <div className="flex items-center gap-3 mb-3">
                    <img src="/logo.jpg" alt="Logo" className="w-8 h-8 rounded" />
                    <span className="font-bold text-xl text-primary tracking-wide">Heurisko</span>
                  </div>
                  <h2 className="text-[32px] font-bold text-gray-900 tracking-tight">Research starts here</h2>
                </div>

                {/* Huge Search Bar Container */}
                <div className="w-full bg-white border-2 border-gray-200 rounded-2xl shadow-sm transition-all focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20 flex flex-col overflow-hidden">
                  <textarea 
                    className="w-full bg-transparent p-5 text-lg outline-none resize-none text-gray-900 placeholder:text-gray-400"
                    placeholder="Ask the research..."
                    rows={2}
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        startSearch();
                      }
                    }}
                  />
                  
                  {/* Search Bar Action Row */}
                  <div className="flex items-center justify-between p-3 bg-gray-50/80 border-t-2 border-gray-100">
                    <div className="flex items-center gap-3">
                      <input type="file" accept=".pdf,.docx,.md" className="hidden" ref={fileInputRef} onChange={handleFileChange} />
                      <button onClick={() => fileInputRef.current?.click()} className="flex items-center gap-2 px-4 py-1.5 rounded-full border-2 border-gray-200 text-sm font-semibold text-gray-700 hover:bg-white hover:border-gray-300 transition-all shadow-sm cursor-pointer">
                        <Paperclip className="w-4 h-4 opacity-70" /> {uploadedFile ? (uploadedFile.length > 20 ? uploadedFile.slice(0, 20) + '...' : uploadedFile) : 'Add files'}
                      </button>
                    </div>
                    <div className="flex items-center gap-4">
                      <button 
                        onClick={startSearch}
                        disabled={isResearching || !query.trim()}
                        className="w-10 h-10 rounded-full bg-primary flex items-center justify-center text-white hover:bg-primary/90 transition-all shadow-md hover:scale-105 disabled:opacity-50 disabled:hover:scale-100 cursor-pointer"
                      >
                         <ChevronRight className="w-5 h-5" />
                      </button>
                    </div>
                  </div>
                </div>

                {/* Suggestion Pills */}
                <div className="flex flex-wrap items-center justify-center gap-3 mt-8 w-full">
                  <button onClick={() => { setQuery("Identify research gaps"); startSearch(); }} className="flex items-center gap-2 px-4 py-2.5 rounded-full border-2 border-gray-100 bg-white text-xs font-bold text-gray-600 hover:border-gray-200 hover:shadow-sm hover:text-primary transition-all cursor-pointer">
                    <Search className="w-3 h-3 text-primary" /> Identify research gaps
                  </button>
                  <button onClick={() => { setQuery("Find studies by method"); startSearch(); }} className="flex items-center gap-2 px-4 py-2.5 rounded-full border-2 border-gray-100 bg-white text-xs font-bold text-gray-600 hover:border-gray-200 hover:shadow-sm hover:text-primary transition-all cursor-pointer">
                    <CheckCircle2 className="w-3 h-3 text-primary" /> Find studies by method
                  </button>
                  <button onClick={() => { setQuery("Quick TL;DR"); startSearch(); }} className="flex items-center gap-2 px-4 py-2.5 rounded-full border-2 border-gray-100 bg-white text-xs font-bold text-gray-600 hover:border-gray-200 hover:shadow-sm hover:text-primary transition-all cursor-pointer">
                    <FileText className="w-3 h-3 text-primary" /> Quick TL;DR
                  </button>
                </div>
              </div>
            )}

            {/* Messages & Loading State */}
            {hasSearched && (
              <div className="w-full max-w-6xl mx-auto py-8 px-4 flex-1 overflow-y-auto custom-scrollbar flex flex-col gap-6 mb-40">
                {messages.map((msg, idx) => {
                  if (msg.role === 'user') {
                    return (
                      <div key={idx} className="flex justify-end fade-in w-full">
                         <div className="bg-primary text-white p-5 rounded-[24px] rounded-tr-[4px] max-w-[80%] md:max-w-[70%] font-medium shadow-sm text-lg leading-relaxed">
                           {msg.content}
                         </div>
                      </div>
                    );
                  } else {
                    const report = msg.content;
                    return (
                      <div key={idx} className="flex justify-start fade-in w-full">
                         <div className="flex flex-col lg:flex-row gap-8 w-full">
                           {/* Main Content Column */}
                           <div className="flex-1 space-y-8">
                              
                              {/* Synthesis Panel */}
                              <div className="bg-white rounded-3xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-shadow">
                                 <div className="bg-primary/5 px-6 py-5 border-b border-gray-100 flex items-center gap-3">
                                   <Brain className="w-6 h-6 text-primary" />
                                   <h3 className="font-bold text-gray-900 text-xl tracking-tight">AI Synthesis</h3>
                                 </div>
                                 <div className="p-8 text-gray-800 leading-relaxed prose prose-primary prose-lg max-w-none prose-p:mb-5 prose-a:text-primary prose-a:font-semibold prose-a:no-underline hover:prose-a:underline">
                                   <ReactMarkdown remarkPlugins={[remarkGfm]}>{report.summary || ''}</ReactMarkdown>
                                   {report.sections && report.sections.map((sec, i) => (
                                     <div key={i} className="mt-8 border-t border-gray-100 pt-8">
                                       <h4 className="font-bold text-xl text-gray-900 mb-4">{sec.heading}</h4>
                                       <ReactMarkdown remarkPlugins={[remarkGfm]}>{sec.content || ''}</ReactMarkdown>
                                     </div>
                                   ))}
                                 </div>
                              </div>

                              {/* Sources / Papers List */}
                              {report.sources && report.sources.length > 0 && (
                                <div>
                                   <div className="flex items-center justify-between mb-6 px-2">
                                     <h3 className="font-bold text-2xl text-gray-900 flex items-center gap-3">
                                       <Database className="w-6 h-6 text-primary" /> Analysed Papers
                                     </h3>
                                     <span className="bg-primary/10 text-primary font-bold px-3 py-1 rounded-full text-sm">
                                       {report.sources.length} sources
                                     </span>
                                   </div>
                                   
                                   <div className="space-y-5">
                                     {report.sources.map((source, index) => (
                                       <div key={index} className="bg-white p-7 rounded-2xl border border-gray-200 shadow-sm hover:shadow-md transition-all group relative overflow-hidden transform hover:-translate-y-1">
                                         <div className="absolute top-0 left-0 w-1.5 h-full bg-primary/20 group-hover:bg-primary transition-colors"></div>
                                         
                                         <div className="flex justify-between items-start mb-4">
                                           <h4 className="font-bold text-xl text-primary group-hover:text-primary/80 transition-colors cursor-pointer pr-8 leading-tight">
                                             <a href={source.url} target="_blank" rel="noreferrer" className="hover:underline">
                                               {source.title || source.url || 'Untitled Document'}
                                             </a>
                                           </h4>
                                           <span className="bg-gray-100 text-gray-600 text-xs px-3 py-1.5 rounded-full font-bold border border-gray-200 shrink-0 uppercase tracking-wide">
                                             {source.tool_used || 'Web'}
                                           </span>
                                         </div>
                                         
                                         <p className="text-sm text-gray-600 mb-5 line-clamp-2 leading-relaxed font-medium">
                                           {source.authors || 'Unknown Authors'}
                                         </p>
                                         
                                         <div className="bg-gray-50 p-5 rounded-xl border border-gray-100">
                                           <p className="text-sm text-gray-700 italic leading-relaxed">"{source.snippet || 'No snippet available.'}"</p>
                                         </div>
                                       </div>
                                     ))}
                                   </div>
                                </div>
                              )}
                           </div>
                         </div>
                      </div>
                    );
                  }
                })}

                {/* Loading State inline */}
                {isResearching && (
                  <div className="flex justify-start fade-in w-full mt-4">
                     <div className="flex flex-col lg:flex-row gap-8 w-full">
                       <div className="flex-1 space-y-8">
                         <div className="bg-white rounded-3xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-shadow">
                            <div className="bg-primary/5 px-6 py-5 border-b border-gray-100 flex items-center gap-3">
                              <Brain className="w-6 h-6 text-primary" />
                              <h3 className="font-bold text-gray-900 text-xl tracking-tight">AI Synthesis</h3>
                            </div>
                            <div className="p-8">
                              <div className="flex flex-col items-center justify-center gap-5 text-base text-primary font-bold my-8">
                                <l-jelly-triangle size="40" speed="1.75" color="#1B6D7A"></l-jelly-triangle>
                                <span className="animate-pulse tracking-wide transition-opacity duration-500">{loadingPhrases[loadingPhraseIndex]}</span>
                              </div>
                              <div className="h-6 bg-gray-100 rounded-md w-1/3 mb-6 animate-pulse"></div>
                              <div className="space-y-4">
                                <div className="h-4 bg-gray-50 rounded w-full animate-pulse"></div>
                                <div className="h-4 bg-gray-50 rounded w-full animate-pulse"></div>
                                <div className="h-4 bg-gray-50 rounded w-5/6 animate-pulse"></div>
                              </div>
                            </div>
                         </div>
                       </div>
                     </div>
                  </div>
                )}
              </div>
            )}
            
            {/* Sticky Bottom Chat Bar for Follow-ups */}
            {hasSearched && (
              <div className="fixed bottom-0 left-0 right-0 md:left-[320px] bg-gradient-to-t from-background via-background to-transparent pt-12 pb-8 z-20 flex justify-center px-4">
                <div className="w-full max-w-4xl">
                  <div className="flex flex-col bg-white rounded-3xl shadow-xl hover:shadow-2xl transition-all border-2 border-gray-200 focus-within:border-primary focus-within:ring-4 focus-within:ring-primary/20 overflow-hidden transform group">
                    <input 
                      type="text" 
                      placeholder="Ask a follow-up question to dig deeper..." 
                      className="w-full px-8 pt-6 pb-4 bg-transparent text-lg focus:outline-none text-gray-900 placeholder:text-gray-400 font-medium"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      onKeyDown={(e) => { if (e.key === 'Enter') startSearch(); }}
                      disabled={isResearching}
                    />
                    <div className="flex items-center justify-between p-4 bg-gray-50/80 border-t-2 border-gray-100">
                      <div className="flex items-center gap-3">
                        <input type="file" accept=".pdf,.docx,.md" className="hidden" ref={fileInputRef} onChange={handleFileChange} />
                        <button onClick={() => fileInputRef.current?.click()} className="flex items-center gap-2 px-5 py-2 rounded-full border-2 border-gray-200 text-sm font-bold text-gray-700 hover:bg-white hover:border-gray-300 hover:text-primary transition-all shadow-sm cursor-pointer">
                          <Paperclip className="w-4 h-4 opacity-70" /> {uploadedFile ? (uploadedFile.length > 20 ? uploadedFile.slice(0, 20) + '...' : uploadedFile) : 'Attach Document'}
                        </button>
                      </div>
                      <div className="flex items-center gap-4">
                        <button 
                          onClick={startSearch}
                          disabled={isResearching || !query.trim()}
                          className="w-12 h-12 rounded-full bg-primary flex items-center justify-center text-white hover:bg-primary/90 transition-all shadow-md hover:scale-105 active:scale-95 disabled:opacity-50 disabled:hover:scale-100 cursor-pointer"
                        >
                           <ChevronRight className="w-6 h-6" />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Footer (Only on default search state) */}
          {!hasSearched && !isResearching && (
            <div className="w-full pb-8 flex justify-center relative mt-auto">
               <div className="absolute top-[10px] left-1/2 transform -translate-x-1/2 w-[80%] border-t-2 border-gray-100 -z-10"></div>
               <span className="bg-background px-6 text-sm font-bold text-gray-400 tracking-wide uppercase">The new standard for academic research</span>
            </div>
          )}

        </div>
    </div>
  );
}

export default App;
