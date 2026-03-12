(function() {
    // Create Chatbot UI Elements
    const chatBubble = document.createElement('div');
    chatBubble.id = 'edu-chat-bubble';
    chatBubble.innerHTML = '<i class="fa-solid fa-comments"></i>';
    
    const chatWindow = document.createElement('div');
    chatWindow.id = 'edu-chat-window';
    chatWindow.innerHTML = `
        <div id="edu-chat-header">
            <span><i class="fa-solid fa-robot me-2"></i>EduSustain AI Helper</span>
            <button id="edu-chat-close"><i class="fa-solid fa-xmark"></i></button>
        </div>
        <div id="edu-chat-messages">
            <div class="bot-msg">Hi! I'm your counseling assistant. How are you feeling today?</div>
        </div>
        <div id="edu-chat-input-area">
            <input type="text" id="edu-chat-input" placeholder="Type a message...">
            <button id="edu-chat-send"><i class="fa-solid fa-paper-plane"></i></button>
        </div>
    `;
    
    document.body.appendChild(chatBubble);
    document.body.appendChild(chatWindow);
    
    // Add Styles
    const style = document.createElement('style');
    style.textContent = `
        #edu-chat-bubble {
            position: fixed;
            bottom: 30px;
            right: 30px;
            width: 60px;
            height: 60px;
            background: linear-gradient(135deg, #8b5cf6, #6366f1);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 24px;
            cursor: pointer;
            box-shadow: 0 5px 20px rgba(139, 92, 246, 0.4);
            z-index: 1000;
            transition: transform 0.3s ease;
        }
        #edu-chat-bubble:hover { transform: scale(1.1); }
        
        #edu-chat-window {
            position: fixed;
            bottom: 100px;
            right: 30px;
            width: 350px;
            height: 450px;
            background: #1e293b;
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            display: none;
            flex-direction: column;
            box-shadow: 0 10px 40px rgba(0,0,0,0.5);
            z-index: 1000;
            overflow: hidden;
            animation: slideUp 0.3s ease;
        }
        @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        
        #edu-chat-header {
            padding: 15px;
            background: rgba(255,255,255,0.05);
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        #edu-chat-messages {
            flex-grow: 1;
            padding: 15px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .bot-msg, .user-msg {
            padding: 10px 15px;
            border-radius: 12px;
            max-width: 80%;
            font-size: 14px;
            line-height: 1.4;
        }
        .bot-msg { background: rgba(255,255,255,0.1); color: #f1f5f9; align-self: flex-start; }
        .user-msg { background: #8b5cf6; color: white; align-self: flex-end; }
        
        #edu-chat-input-area {
            padding: 15px;
            display: flex;
            gap: 10px;
            border-top: 1px solid rgba(255,255,255,0.1);
        }
        #edu-chat-input {
            flex-grow: 1;
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid rgba(255,255,255,0.1);
            color: white;
            border-radius: 8px;
            padding: 8px 12px;
            outline: none;
        }
        #edu-chat-send {
            background: #8b5cf6;
            border: none;
            color: white;
            border-radius: 8px;
            width: 40px;
            cursor: pointer;
        }
        #edu-chat-close { background: none; border: none; color: #94a3b8; cursor: pointer; }
    `;
    document.head.appendChild(style);
    
    // Interactions
    chatBubble.onclick = () => chatWindow.style.display = chatWindow.style.display === 'flex' ? 'none' : 'flex';
    document.getElementById('edu-chat-close').onclick = () => chatWindow.style.display = 'none';
    
    const input = document.getElementById('edu-chat-input');
    const sendBtn = document.getElementById('edu-chat-send');
    const msgContainer = document.getElementById('edu-chat-messages');
    
    const appendMsg = (text, type) => {
        const div = document.createElement('div');
        div.className = `${type}-msg`;
        div.textContent = text;
        msgContainer.appendChild(div);
        msgContainer.scrollTop = msgContainer.scrollHeight;
    };
    
    const handleSend = async () => {
        const msg = input.value.trim();
        if (!msg) return;
        
        appendMsg(msg, 'user');
        input.value = '';
        
        try {
            const response = await fetch('/chatbot', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: msg })
            });
            const data = await response.json();
            appendMsg(data.reply, 'bot');
        } catch (e) {
            appendMsg("Sorry, I'm having trouble connecting right now.", 'bot');
        }
    };
    
    sendBtn.onclick = handleSend;
    input.onkeypress = (e) => { if (e.key === 'Enter') handleSend(); };
})();
