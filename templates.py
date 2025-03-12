"""
HTML templates and frontend code for mem0 + Ollama integration
"""

# HTML template for the web interface
INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>mem0 + Ollama Chat</title>
    <style>
        :root {
            --primary: #4a6fa5;
            --secondary: #336b87;
            --background: #f5f5f5;
            --surface: #ffffff;
            --text: #333333;
            --error: #b71c1c;
            --success: #43a047;
            --user-msg: #e3f2fd;
            --assistant-msg: #f1f8e9;
            --memory-bg: #fffde7;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: var(--text);
            background-color: var(--background);
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            min-height: 100vh;
        }
        
        header {
            background-color: var(--primary);
            color: white;
            padding: 1rem;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        main {
            flex: 1;
            display: flex;
            flex-direction: column;
            padding: 1rem;
            max-width: 1200px;
            margin: 0 auto;
            width: 100%;
            box-sizing: border-box;
        }
        
        .chat-container {
            display: flex;
            flex: 1;
            gap: 1rem;
        }
        
        .chat-main {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: var(--surface);
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .sidebar {
            width: 250px;
            background: var(--surface);
            border-radius: 8px;
            padding: 1rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .chat-messages {
            flex: 1;
            padding: 1rem;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }
        
        .message {
            padding: 1rem;
            border-radius: 8px;
            max-width: 80%;
            word-break: break-word;
        }
        
        .user {
            align-self: flex-end;
            background-color: var(--user-msg);
            border-bottom-right-radius: 0;
        }
        
        .assistant {
            align-self: flex-start;
            background-color: var(--assistant-msg);
            border-bottom-left-radius: 0;
        }
        
        .system {
            align-self: center;
            background-color: #f0f0f0;
            color: #666;
            font-style: italic;
            padding: 0.5rem 1rem;
            font-size: 0.9rem;
        }
        
        .chat-form {
            display: flex;
            padding: 1rem;
            gap: 0.5rem;
            background-color: var(--surface);
            border-top: 1px solid #eee;
        }
        
        .chat-input {
            flex: 1;
            padding: 0.75rem;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 1rem;
        }
        
        button {
            background-color: var(--primary);
            color: white;
            border: none;
            border-radius: 4px;
            padding: 0.5rem 1rem;
            font-size: 1rem;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        
        button:hover {
            background-color: var(--secondary);
        }
        
        button:disabled {
            background-color: #cccccc;
            cursor: not-allowed;
        }
        
        .model-selector, .memory-controls, .format-selector {
            margin-bottom: 1.5rem;
        }
        
        select, input {
            width: 100%;
            padding: 0.5rem;
            margin-top: 0.5rem;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 0.9rem;
        }
        
        label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 500;
        }
        
        .sidebar h3 {
            margin-top: 0;
            color: var(--primary);
            border-bottom: 1px solid #eee;
            padding-bottom: 0.5rem;
        }
        
        .memory-item {
            background-color: var(--memory-bg);
            padding: 0.75rem;
            border-radius: 4px;
            margin-bottom: 0.5rem;
            font-size: 0.85rem;
            border-left: 3px solid var(--secondary);
        }
        
        .memories-container {
            max-height: 300px;
            overflow-y: auto;
            margin-top: 1rem;
        }
        
        .loading {
            text-align: center;
            padding: 1rem;
            font-style: italic;
            color: #666;
        }
        
        pre {
            background-color: #f5f5f5;
            padding: 0.5rem;
            border-radius: 4px;
            overflow-x: auto;
            font-size: 0.9rem;
        }
        
        code {
            font-family: 'Courier New', Courier, monospace;
            background-color: #f5f5f5;
            padding: 0.1rem 0.3rem;
            border-radius: 3px;
            font-size: 0.9rem;
        }
        
        .error {
            color: var(--error);
            padding: 1rem;
            background-color: #ffebee;
            border-radius: 4px;
            margin: 1rem 0;
        }
        
        /* Responsive design */
        @media (max-width: 768px) {
            .chat-container {
                flex-direction: column;
            }
            
            .sidebar {
                width: 100%;
                order: 2;
            }
            
            .chat-main {
                order: 1;
            }
            
            .message {
                max-width: 90%;
            }
        }
    </style>
</head>
<body>
    <header>
        <h1>mem0 + Ollama Chat Interface</h1>
    </header>
    
    <main>
        <div class="chat-container">
            <div class="chat-main">
                <div class="chat-messages" id="chatMessages">
                    <div class="message system">
                        Welcome to mem0 + Ollama Chat! This interface connects to the Ollama API with mem0 memory integration.
                    </div>
                </div>
                
                <form class="chat-form" id="chatForm">
                    <input type="text" class="chat-input" id="messageInput" placeholder="Type your message..." required>
                    <button type="submit" id="sendButton">Send</button>
                </form>
            </div>
            
            <div class="sidebar">
                <div class="model-selector">
                    <h3>Model Settings</h3>
                    <label for="modelInput">Model Name:</label>
                    <input type="text" id="modelInput" value="llama3" placeholder="e.g., llama3, llama3:latest">
                    <small style="display: block; margin-top: 5px; color: #666;">Enter the exact model name from your Ollama server</small>
                </div>
                
                <div class="format-selector">
                    <label for="formatSelect">Output Format:</label>
                    <select id="formatSelect">
                        <option value="none">None</option>
                        <option value="json">JSON</option>
                        <option value="sentiment">Sentiment Analysis</option>
                        <option value="summary">Summary</option>
                        <option value="action_items">Action Items</option>
                    </select>
                </div>
                
                <div class="memory-controls">
                    <h3>Memory Settings</h3>
                    <label for="modeSelect">Memory Mode:</label>
                    <select id="modeSelect">
                        <option value="search">Search</option>
                        <option value="user">User</option>
                        <option value="session">Session</option>
                        <option value="none">None</option>
                    </select>
                    
                    <div style="margin-top: 1rem;">
                        <button type="button" id="clearMemoriesBtn" class="secondary-btn">Clear Memories</button>
                    </div>
                </div>
                
                <div>
                    <h3>Recent Memories</h3>
                    <div class="memories-container" id="memoriesContainer">
                        <div class="memory-item">No memories yet.</div>
                    </div>
                </div>
            </div>
        </div>
    </main>
    
    <script>
        // Global state
        let conversationId = null;
        let userId = `web_user_${Date.now().toString(36)}`;
        
        // DOM elements
        const chatMessages = document.getElementById('chatMessages');
        const chatForm = document.getElementById('chatForm');
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        const modelInput = document.getElementById('modelInput');
        const formatSelect = document.getElementById('formatSelect');
        const modeSelect = document.getElementById('modeSelect');
        const clearMemoriesBtn = document.getElementById('clearMemoriesBtn');
        const memoriesContainer = document.getElementById('memoriesContainer');
        
        // Debug window error handler
        window.onerror = function(message, source, lineno, colno, error) {
            console.error('Global error:', message, 'at', source, lineno, colno, error);
            addSystemMessage(`Error: ${message}`);
            return false;
        };
        
        // Try to fetch available models - removed since we use modelInput now
        async function fetchModels() {
            try {
                
                console.log('Fetching models from API...');
                
                // Direct XHR approach to avoid fetch quirks on some browsers
                const xhr = new XMLHttpRequest();
                xhr.open('GET', '/api/models', true);
                xhr.timeout = 5000; // 5 second timeout
                
                xhr.onload = function() {
                    if (xhr.status === 200) {
                        try {
                            const data = JSON.parse(xhr.responseText);
                            console.log('Received models:', data);
                            
                            if (data.models && data.models.length > 0) {
                                // Just log available models for reference
                                const modelNames = data.models.map(model => model.name || model.id || 'unknown').join(', ');
                                console.log(`Available models: ${modelNames}`);
                                
                                // Maybe suggest models to user
                                addSystemMessage(`Available models: ${modelNames}. Enter one in the Model Name field.`);
                            }
                        } catch (e) {
                            console.error('Error parsing models JSON:', e);
                        }
                    }
                };
                
                xhr.onerror = function() {
                    console.error('XHR network error');
                };
                
                xhr.ontimeout = function() {
                    console.error('XHR timeout');
                };
                
                xhr.send();
            } catch (error) {
                console.error('Error fetching models:', error);
                
                addSystemMessage('Failed to load available models. Using default model. Check if Ollama is running at http://localhost:11434');
            }
        }
        
        // Add a message to the chat
        function addMessage(content, role) {
            const messageDiv = document.createElement('div');
            messageDiv.classList.add('message', role);
            
            // Convert markdown-like syntax (simplified)
            let formattedContent = content
                .replace(/```([\s\S]*?)```/g, '<pre>$1</pre>')
                .replace(/`([^`]+)`/g, '<code>$1</code>')
                .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
                .replace(/\*([^*]+)\*/g, '<em>$1</em>')
                .replace(/\\n/g, '<br>');
            
            messageDiv.innerHTML = formattedContent;
            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        // Add a system message
        function addSystemMessage(content) {
            const messageDiv = document.createElement('div');
            messageDiv.classList.add('message', 'system');
            messageDiv.textContent = content;
            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        // Add a loading indicator
        function addLoadingIndicator() {
            const loadingDiv = document.createElement('div');
            loadingDiv.classList.add('loading');
            loadingDiv.id = 'loadingIndicator';
            loadingDiv.textContent = 'Thinking...';
            chatMessages.appendChild(loadingDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        // Remove loading indicator
        function removeLoadingIndicator() {
            const loadingIndicator = document.getElementById('loadingIndicator');
            if (loadingIndicator) {
                loadingIndicator.remove();
            }
        }
        
        // Send a message to the API (with manual try-catch and direct XHR for better debugging)
        function sendMessage(content) {
            addLoadingIndicator();
            sendButton.disabled = true;
            
            try {
                // Get model from text input
                const modelInput = document.getElementById('modelInput');
                const modelName = modelInput.value.trim() || 'llama3'; // Default to llama3 if empty
                addSystemMessage(`Sending message to model: ${modelName}...`);
                
                const payload = {
                    messages: [
                        { role: 'user', content }
                    ],
                    model: modelName,
                    format: formatSelect.value === 'none' ? null : formatSelect.value,
                    conversation_id: conversationId,
                    memory_mode: modeSelect.value  // Add memory mode parameter
                };
                
                console.log("Payload:", JSON.stringify(payload, null, 2));
                
                // Use XMLHttpRequest instead of fetch for better debugging
                const xhr = new XMLHttpRequest();
                xhr.open("POST", "/api/chat", true);
                xhr.setRequestHeader("Content-Type", "application/json");
                xhr.timeout = 60000; // 60 second timeout
                
                xhr.onload = function() {
                    console.log("Response status:", xhr.status);
                    console.log("Response text:", xhr.responseText.substring(0, 200) + "...");
                    
                    if (xhr.status === 200) {
                        try {
                            const data = JSON.parse(xhr.responseText);
                            console.log("Parsed response:", data);
                            
                            // Update conversation ID
                            if (data.conversation_id) {
                                conversationId = data.conversation_id;
                                console.log("Updated conversation ID:", conversationId);
                            }
                            
                            // Check if data is in expected format
                            if (data.choices && data.choices[0] && data.choices[0].message) {
                                const assistantContent = data.choices[0].message.content;
                                removeLoadingIndicator();
                                addMessage(assistantContent, 'assistant');
                                
                                // Update memories if available
                                if (data.memories) {
                                    updateMemoriesDisplay(data.memories);
                                }
                            } else {
                                console.error("Unexpected response format:", data);
                                removeLoadingIndicator();
                                addSystemMessage("Error: Unexpected response format from server");
                            }
                        } catch (parseError) {
                            console.error("JSON parse error:", parseError);
                            removeLoadingIndicator();
                            addSystemMessage(`Error parsing response: ${parseError.message}`);
                        }
                    } else {
                        console.error("XHR error status:", xhr.status);
                        removeLoadingIndicator();
                        addSystemMessage(`API error: ${xhr.status} - ${xhr.statusText}`);
                    }
                    
                    sendButton.disabled = false;
                };
                
                xhr.onerror = function() {
                    console.error("XHR network error");
                    removeLoadingIndicator();
                    addSystemMessage("Network error. Could not connect to API.");
                    sendButton.disabled = false;
                };
                
                xhr.ontimeout = function() {
                    console.error("XHR timeout");
                    removeLoadingIndicator();
                    addSystemMessage("Request timed out. The server may be busy or the model might be taking too long to respond.");
                    sendButton.disabled = false;
                };
                
                // Actually send the request
                xhr.send(JSON.stringify(payload));
                
            } catch (error) {
                console.error('Error in send process:', error);
                removeLoadingIndicator();
                addSystemMessage(`Error: ${error.message}`);
                sendButton.disabled = false;
            }
        }
        
        // Update the memories display
        function updateMemoriesDisplay(memories) {
            memoriesContainer.innerHTML = '';
            
            if (memories.length === 0) {
                const memoryItem = document.createElement('div');
                memoryItem.classList.add('memory-item');
                memoryItem.textContent = 'No memories found.';
                memoriesContainer.appendChild(memoryItem);
                return;
            }
            
            memories.forEach(memory => {
                const memoryItem = document.createElement('div');
                memoryItem.classList.add('memory-item');
                memoryItem.textContent = memory.memory || memory;
                memoriesContainer.appendChild(memoryItem);
            });
        }
        
        // Fetch user memories
        async function fetchMemories() {
            try {
                const response = await fetch(`/api/memories?user_id=${userId}`);
                const data = await response.json();
                
                updateMemoriesDisplay(data.memories || []);
            } catch (error) {
                console.error('Error fetching memories:', error);
            }
        }
        
        // Clear user memories
        async function clearMemories() {
            try {
                const response = await fetch(`/api/memories?user_id=${userId}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    addSystemMessage('All memories have been cleared.');
                    updateMemoriesDisplay([]);
                } else {
                    throw new Error('Failed to clear memories.');
                }
            } catch (error) {
                console.error('Error clearing memories:', error);
                addSystemMessage(`Error: ${error.message}`);
            }
        }
        
        // Event Listeners
        chatForm.addEventListener('submit', function(e) {
            e.preventDefault(); // This stops the form from actually submitting
            console.log("Form submitted");
            
            const message = messageInput.value.trim();
            if (message) {
                console.log("Sending message:", message);
                addMessage(message, 'user');
                sendMessage(message);
                messageInput.value = '';
            } else {
                console.log("Empty message, not sending");
            }
            
            return false; // Just to be extra sure it doesn't refresh
        });
        
        clearMemoriesBtn.addEventListener('click', clearMemories);
        
        // Initialize the app
        function init() {
            // No need to fetch models as we now use manual input
            fetchMemories();
            addSystemMessage(`Memory mode: ${modeSelect.value}`);
            addSystemMessage(`Using model: ${document.getElementById('modelInput').value}`);
        }
        
        // Start the application
        init();
    </script>
</body>
</html>
"""
