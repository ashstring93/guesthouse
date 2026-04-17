class WatermillChatbot {
    constructor(apiUrl = '') {
        this.apiUrl = apiUrl;
        this.conversationId = this.generateId();
        this.isOpen = false;

        this.init();
    }

    init() {
        this.createChatbotUI();
        this.attachEventListeners();
        this.showWelcomeMessage();
    }

    createChatbotUI() {
        const markup = `
            <button class="chatbot-button" id="chatbotButton" aria-label="챗봇 열기">
                <svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                    <defs>
                        <linearGradient id="chatbotBotHeadGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stop-color="#f6fbff"/>
                            <stop offset="100%" stop-color="#dce7f5"/>
                        </linearGradient>
                        <linearGradient id="chatbotBotBodyGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stop-color="#5ec8ff"/>
                            <stop offset="100%" stop-color="#2e74ff"/>
                        </linearGradient>
                    </defs>
                    <circle cx="32" cy="7" r="4" fill="#ff4d4d"/>
                    <rect x="30" y="11" width="4" height="6" rx="2" fill="#95a8c5"/>
                    <rect x="10" y="18" width="44" height="30" rx="12" fill="url(#chatbotBotHeadGradient)" stroke="#1a3256" stroke-width="2"/>
                    <circle cx="24" cy="32" r="6.5" fill="#08142d"/>
                    <circle cx="40" cy="32" r="6.5" fill="#08142d"/>
                    <circle cx="22" cy="30" r="2" fill="#c6f1ff"/>
                    <circle cx="38" cy="30" r="2" fill="#c6f1ff"/>
                    <path d="M24 41c2.3 2.2 13.7 2.2 16 0" fill="none" stroke="#1a3256" stroke-width="2.4" stroke-linecap="round"/>
                    <rect x="18" y="50" width="28" height="8" rx="4" fill="url(#chatbotBotBodyGradient)" stroke="#1a3256" stroke-width="2"/>
                </svg>
            </button>


            <div class="chatbot-container" id="chatbotContainer">
                <div class="chatbot-header">
                    <h3>🏠 물레방아하우스 안내봇</h3>
                    <button class="chatbot-close" id="chatbotClose" aria-label="챗봇 닫기">×</button>
                </div>

                <div class="chatbot-messages" id="chatbotMessages"></div>

                <div class="typing-indicator" id="typingIndicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>

                <div class="chatbot-input-area">
                    <input
                        type="text"
                        class="chatbot-input"
                        id="chatbotInput"
                        placeholder="무엇을 도와드릴까요?"
                        autocomplete="off"
                    />
                    <button class="chatbot-send" id="chatbotSend" aria-label="메시지 전송">
                        <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                        </svg>
                    </button>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', markup);

        this.button = document.getElementById('chatbotButton');
        this.floatingHint = document.getElementById('chatbotFloatingHint');
        this.container = document.getElementById('chatbotContainer');
        this.closeButton = document.getElementById('chatbotClose');
        this.messagesContainer = document.getElementById('chatbotMessages');
        this.input = document.getElementById('chatbotInput');
        this.sendButton = document.getElementById('chatbotSend');
        this.typingIndicator = document.getElementById('typingIndicator');
    }

    getAppBasePath() {
        const path = window.location.pathname;
        const reservationMarker = '/reservation/';
        const markerIndex = path.indexOf(reservationMarker);

        if (markerIndex >= 0) {
            return path.slice(0, markerIndex);
        }

        if (path === '/' || path === '') {
            return '';
        }

        return path.endsWith('/') ? path.slice(0, -1) : path;
    }

    resolveChatAssetPath(path) {
        if (!path || !path.startsWith('/')) {
            return path;
        }

        const basePath = this.getAppBasePath();
        if (!basePath || path.startsWith(`${basePath}/`)) {
            return path;
        }

        return `${basePath}${path}`;
    }

    hydrateMarkdown(container, markdownText) {
        if (typeof marked === 'undefined') {
            container.textContent = markdownText;
            return;
        }

        container.innerHTML = marked.parse(markdownText);
        container.querySelectorAll('img[src^="/"]').forEach((img) => {
            img.src = this.resolveChatAssetPath(img.getAttribute('src'));
        });
    }

    getChatApiUrl() {
        return this.apiUrl
            ? `${this.apiUrl}/api/chat`
            : `${this.getAppBasePath()}/api/chat`;
    }

    setBusy(isBusy) {
        this.sendButton.disabled = isBusy;
        if (!isBusy) {
            this.input.focus();
        }
    }

    removeWelcomeMessage() {
        const welcomeMessage = this.messagesContainer.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.remove();
        }
    }

    createBotMessage() {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot';
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
        return messageDiv;
    }

    parseStreamEvent(rawEvent) {
        const event = { type: 'message', data: {} };
        const dataLines = [];

        rawEvent.split(/\r?\n/).forEach((line) => {
            if (line.startsWith('event:')) {
                event.type = line.slice(6).trim();
            } else if (line.startsWith('data:')) {
                dataLines.push(line.slice(5).trimStart());
            }
        });

        const rawData = dataLines.join('\n');
        if (!rawData) {
            return event;
        }

        try {
            event.data = JSON.parse(rawData);
        } catch (_) {
            event.data = { text: rawData };
        }

        return event;
    }

    handleStreamEvent(rawEvent, handlers) {
        const event = this.parseStreamEvent(rawEvent);

        if (event.type === 'session' && event.data.session_id) {
            this.conversationId = event.data.session_id;
            return;
        }

        if (event.type === 'chunk') {
            handlers.onChunk(event.data.text || '');
            return;
        }

        if (event.type === 'error') {
            throw new Error(event.data.message || '챗봇 응답 생성 중 오류가 발생했습니다.');
        }
    }

    async readChatStream(response, handlers) {
        if (!response.body) {
            handlers.onChunk(await response.text());
            return;
        }

        const contentType = response.headers.get('content-type') || '';
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });

            if (!contentType.includes('text/event-stream')) {
                handlers.onChunk(chunk);
                continue;
            }

            buffer += chunk;
            const events = buffer.split('\n\n');
            buffer = events.pop() || '';

            events.forEach((rawEvent) => {
                if (rawEvent.trim()) {
                    this.handleStreamEvent(rawEvent, handlers);
                }
            });
        }

        if (contentType.includes('text/event-stream') && buffer.trim()) {
            this.handleStreamEvent(buffer, handlers);
        }
    }

    attachEventListeners() {
        this.button.addEventListener('click', () => this.toggleChatbot());
        this.closeButton.addEventListener('click', () => this.toggleChatbot());

        this.sendButton.addEventListener('click', () => this.sendMessage());
        this.input.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                this.sendMessage();
            }
        });
    }

    toggleChatbot() {
        this.isOpen = !this.isOpen;
        this.container.classList.toggle('open', this.isOpen);
        if (this.floatingHint) {
            this.floatingHint.classList.toggle('is-hidden', this.isOpen);
        }

        if (this.isOpen) {
            this.input.focus();
        }
    }

    showWelcomeMessage() {
        const welcomeHTML = `
            <div class="welcome-message">
                <h4>안녕하세요! 👋</h4>
                <p>물레방아하우스에 관해<br>무엇이든 물어보세요</p>
                <div class="suggested-questions">
                    <button class="suggested-question" data-question="체크인 시간이 언제인가요?">체크인 시간이 언제인가요?</button>
                    <button class="suggested-question" data-question="반려동물을 데리고 갈 수 있나요?">반려동물을 데리고 갈 수 있나요?</button>
                    <button class="suggested-question" data-question="한옥마을까지 얼마나 걸리나요?">한옥마을까지 얼마나 걸리나요?</button>
                </div>
            </div>
        `;

        this.messagesContainer.innerHTML = welcomeHTML;

        this.messagesContainer.querySelectorAll('.suggested-question').forEach((button) => {
            button.addEventListener('click', (event) => {
                const question = event.currentTarget.dataset.question;
                this.input.value = question;
                this.sendMessage();
            });
        });
    }

    async sendMessage() {
        const message = this.input.value.trim();

        if (!message) return;

        this.input.value = '';
        this.setBusy(true);
        this.removeWelcomeMessage();
        this.addMessage(message, 'user');
        this.showTyping();

        try {
            const response = await fetch(this.getChatApiUrl(), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'text/event-stream',
                },
                body: JSON.stringify({
                    question: message,
                    session_id: this.conversationId
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const botMessageDiv = this.createBotMessage();
            let isFirstChunk = true;
            let fullAnswer = '';

            await this.readChatStream(response, {
                onChunk: (chunk) => {
                    if (!chunk) return;

                    if (isFirstChunk) {
                        this.hideTyping();
                        isFirstChunk = false;
                    }

                    fullAnswer += chunk;

                    this.hydrateMarkdown(botMessageDiv, fullAnswer);
                    this.scrollToBottom();
                }
            });

            if (isFirstChunk) this.hideTyping();

        } catch (error) {
            this.hideTyping();
            this.addMessage(
                '죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.',
                'bot'
            );
            console.error('Chatbot API Error:', error);
        } finally {
            this.setBusy(false);
        }
    }

    addMessage(text, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        messageDiv.textContent = text;

        if (type === 'bot') {
            this.hydrateMarkdown(messageDiv, text);
        }

        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    showTyping() {
        this.typingIndicator.classList.add('active');
        this.scrollToBottom();
    }

    hideTyping() {
        this.typingIndicator.classList.remove('active');
    }

    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    generateId() {
        return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.chatbot = new WatermillChatbot();
});

