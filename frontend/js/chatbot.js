/**
 * 臾쇰젅諛⑹븘?섏슦??AI 梨쀫큸 ?꾩젽
 * 諛깆뿏??API? ?듭떊?섏뿬 ??뷀삎 ?명꽣?섏씠???쒓났
 */

class MullebangChatbot {
    constructor(apiUrl = '') {
        this.apiUrl = apiUrl;
        this.conversationId = this.generateId();
        this.isOpen = false;
        this.messageHistory = [];

        this.init();
    }

    init() {
        // DOM ?붿냼 ?앹꽦
        this.createChatbotUI();

        // ?대깽??由ъ뒪???깅줉
        this.attachEventListeners();

        // ?섏쁺 硫붿떆吏 ?쒖떆
        this.showWelcomeMessage();
    }

    createChatbotUI() {
        // 梨쀫큸 HTML ?앹꽦
        const chatbotHTML = `
            <!-- 플로팅 버튼 -->
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


            <!-- 대화창 -->
            <div class="chatbot-container" id="chatbotContainer">
                <div class="chatbot-header">
                    <h3>🏠 물레방아하우스 안내봇</h3>
                    <button class="chatbot-close" id="chatbotClose" aria-label="챗봇 닫기">×</button>
                </div>

                <div class="chatbot-messages" id="chatbotMessages">
                    <!-- 메시지가 여기에 추가됩니다 -->
                </div>

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

        // body??異붽?
        document.body.insertAdjacentHTML('beforeend', chatbotHTML);

        // DOM 李몄“ ???
        this.button = document.getElementById('chatbotButton');
        this.floatingHint = document.getElementById('chatbotFloatingHint');
        this.container = document.getElementById('chatbotContainer');
        this.closeButton = document.getElementById('chatbotClose');
        this.messagesContainer = document.getElementById('chatbotMessages');
        this.input = document.getElementById('chatbotInput');
        this.sendButton = document.getElementById('chatbotSend');
        this.typingIndicator = document.getElementById('typingIndicator');
    }

    attachEventListeners() {
        // 梨쀫큸 ?닿린/?リ린
        this.button.addEventListener('click', () => this.toggleChatbot());
        this.closeButton.addEventListener('click', () => this.toggleChatbot());

        // 硫붿떆吏 ?꾩넚
        this.sendButton.addEventListener('click', () => this.sendMessage());
        this.input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
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

        // 異붿쿇 吏덈Ц ?대┃ ?대깽??
        document.querySelectorAll('.suggested-question').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const question = e.target.dataset.question;
                this.input.value = question;
                this.sendMessage();
            });
        });
    }

    async sendMessage() {
        const message = this.input.value.trim();

        if (!message) return;

        // ?낅젰李?珥덇린??諛?踰꾪듉 鍮꾪솢?깊솕
        this.input.value = '';
        this.sendButton.disabled = true;

        // ?섏쁺 硫붿떆吏 ?쒓굅 (泥?硫붿떆吏??寃쎌슦)
        const welcomeMsg = this.messagesContainer.querySelector('.welcome-message');
        if (welcomeMsg) {
            welcomeMsg.remove();
        }

        // ?ъ슜??硫붿떆吏 ?쒖떆
        this.addMessage(message, 'user');

        // ??댄븨 ?몃뵒耳?댄꽣 ?쒖떆
        this.showTyping();

        try {
            // API ?몄텧 (?ㅽ듃由щ컢)
            const defaultApiPath = window.location.pathname.includes('/reservation/')
                ? '../api/chat'
                : 'api/chat';
            const url = this.apiUrl
                ? `${this.apiUrl}/api/chat`
                : new URL(defaultApiPath, window.location.href).toString();
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    question: message,
                    session_id: this.conversationId
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            // 遊?硫붿떆吏 而⑦뀒?대꼫 ?앹꽦 (鍮??곹깭濡?
            const botMessageDiv = document.createElement('div');
            botMessageDiv.className = 'message bot';
            this.messagesContainer.appendChild(botMessageDiv);
            this.scrollToBottom();

            // ?ㅽ듃由??쎄린
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let isFirstChunk = true;
            let fullAnswer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                fullAnswer += chunk;

                if (isFirstChunk) {
                    this.hideTyping();
                    isFirstChunk = false;
                }

                // 留덊겕?ㅼ슫 ?뚯떛???곸슜?섏뿬 HTML濡??뚮뜑留?
                if (typeof marked !== 'undefined') {
                    botMessageDiv.innerHTML = marked.parse(fullAnswer);
                } else {
                    botMessageDiv.textContent = fullAnswer;
                }
                this.scrollToBottom();
            }

            // 硫붿떆吏 ?덉뒪?좊━ ???
            this.messageHistory.push(
                { role: 'user', content: message },
                { role: 'assistant', content: fullAnswer }
            );

        } catch (error) {
            this.hideTyping(); // ?먮윭 諛쒖깮 ???몃뵒耳?댄꽣 ?④?
            this.addMessage(
                '죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.',
                'bot'
            );
            console.error('Chatbot API Error:', error);
        } finally {
            // 踰꾪듉 ?ㅼ떆 ?쒖꽦??
            this.sendButton.disabled = false;
            this.input.focus();
        }
    }

    // callAPI 硫붿꽌?쒕뒗 ?댁젣 sendMessage ?대????듯빀?섏뿀?쇰?濡??쒓굅?섍굅??洹몃?濡??щ룄 臾대갑?섏?留?
    // sendMessage媛 吏곸젒 fetch瑜??섑뻾?섎?濡??ъ슜?섏? ?딆쓬.
    async callAPI(question) {
        // ... (Legacy code, kept for reference if needed, or remove)
        return null;
    }

    addMessage(text, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        messageDiv.textContent = text;

        // 留덊겕?ㅼ슫 異붽? (遊?硫붿떆吏??寃쎌슦)
        if (type === 'bot') {
            if (typeof marked !== 'undefined') {
                messageDiv.innerHTML = marked.parse(text);
            }
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

// ?섏씠吏 濡쒕뱶 ??梨쀫큸 珥덇린??
document.addEventListener('DOMContentLoaded', () => {
    // ?곷? 寃쎈줈 ?ъ슜???꾪빐 apiUrl ?놁씠 珥덇린??
    window.chatbot = new MullebangChatbot();
    console.log('물레방아하우스 챗봇이 준비되었습니다!');
});

