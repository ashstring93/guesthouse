/**
 * 물레방아하우스 AI 챗봇 위젯
 * 백엔드 API와 통신하여 대화형 인터페이스 제공
 */

class MullebangChatbot {
    constructor(apiUrl = 'http://localhost:8000') {
        this.apiUrl = apiUrl;
        this.conversationId = this.generateId();
        this.isOpen = false;
        this.messageHistory = [];
        
        this.init();
    }
    
    init() {
        // DOM 요소 생성
        this.createChatbotUI();
        
        // 이벤트 리스너 등록
        this.attachEventListeners();
        
        // 환영 메시지 표시
        this.showWelcomeMessage();
    }
    
    createChatbotUI() {
        // 챗봇 HTML 생성
        const chatbotHTML = `
            <!-- 플로팅 버튼 -->
            <button class="chatbot-button" id="chatbotButton" aria-label="챗봇 열기">
                <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/>
                    <path d="M7 9h2v2H7zm4 0h2v2h-2zm4 0h2v2h-2z"/>
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
        
        // body에 추가
        document.body.insertAdjacentHTML('beforeend', chatbotHTML);
        
        // DOM 참조 저장
        this.button = document.getElementById('chatbotButton');
        this.container = document.getElementById('chatbotContainer');
        this.closeButton = document.getElementById('chatbotClose');
        this.messagesContainer = document.getElementById('chatbotMessages');
        this.input = document.getElementById('chatbotInput');
        this.sendButton = document.getElementById('chatbotSend');
        this.typingIndicator = document.getElementById('typingIndicator');
    }
    
    attachEventListeners() {
        // 챗봇 열기/닫기
        this.button.addEventListener('click', () => this.toggleChatbot());
        this.closeButton.addEventListener('click', () => this.toggleChatbot());
        
        // 메시지 전송
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
        
        // 추천 질문 클릭 이벤트
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
        
        // 입력창 초기화 및 버튼 비활성화
        this.input.value = '';
        this.sendButton.disabled = true;
        
        // 환영 메시지 제거 (첫 메시지인 경우)
        const welcomeMsg = this.messagesContainer.querySelector('.welcome-message');
        if (welcomeMsg) {
            welcomeMsg.remove();
        }
        
        // 사용자 메시지 표시
        this.addMessage(message, 'user');
        
        // 타이핑 인디케이터 표시
        this.showTyping();
        
        try {
            // API 호출
            const response = await this.callAPI(message);
            
            // 타이핑 인디케이터 숨기기
            this.hideTyping();
            
            // AI 응답 표시
            this.addMessage(response.answer, 'bot', response.sources);
            
            // 메시지 히스토리 저장
            this.messageHistory.push(
                { role: 'user', content: message },
                { role: 'assistant', content: response.answer }
            );
            
        } catch (error) {
            this.addMessage(
                '죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 타임아웃 되거나 연결이 거부되었을 수 있습니다.',
                'bot'
            );
            console.error('Chatbot API Error:', error);
        } finally {
            // 버튼 다시 활성화
            this.sendButton.disabled = false;
            this.input.focus();
        }
    }
    
    async callAPI(question) {
        const response = await fetch(`${this.apiUrl}/api/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ question })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }
    
    addMessage(text, type, sources = []) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        messageDiv.textContent = text;
        
        // 소스 정보 추가 (봇 메시지인 경우)
        if (type === 'bot' && sources && sources.length > 0) {
            const sourcesDiv = document.createElement('div');
            sourcesDiv.className = 'message-sources';
            sourcesDiv.textContent = `📚 ${sources.join(', ')}`;
            messageDiv.appendChild(sourcesDiv);
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

// 페이지 로드 시 챗봇 초기화
document.addEventListener('DOMContentLoaded', () => {
    // 호스트명 기반으로 API URL 동적 설정
    const hostname = window.location.hostname;
    const isLocal = hostname === 'localhost' || 
                   hostname === '127.0.0.1' || 
                   hostname.startsWith('192.168.') || 
                   hostname.startsWith('172.') || 
                   hostname.startsWith('10.');

    const API_URL = isLocal
        ? `http://${hostname}:8000` 
        : 'https://your-backend-url.com';
    
    
    window.chatbot = new MullebangChatbot(API_URL);
    console.log('물레방아하우스 챗봇이 준비되었습니다! 🎉');
});
