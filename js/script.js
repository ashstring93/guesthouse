document.addEventListener('DOMContentLoaded', () => {
    console.log('Mullebang-a House website loaded.');

    // Smooth scrolling for navigation links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });

    // Hero Slider Logic
    const heroSlider = document.querySelector('.hero-slider');
    const images = ['images/1.avif', 'images/6.avif', 'images/9.avif']; // Landscape oriented images
    let currentSlide = 0;

    // Initialize slides
    images.forEach((img, index) => {
        const slide = document.createElement('div');
        slide.classList.add('slide');
        slide.style.backgroundImage = `url('${img}')`;
        if (index === 0) slide.classList.add('active');
        heroSlider.appendChild(slide);
    });

    setInterval(() => {
        const slides = document.querySelectorAll('.hero-slider .slide');
        slides[currentSlide].classList.remove('active');
        currentSlide = (currentSlide + 1) % slides.length;
        slides[currentSlide].classList.add('active');
    }, 5000); // Change slide every 5 seconds

    // Header Scroll Effect & Hero Parallax
    const heroSection = document.getElementById('hero');
    const heroContent = document.querySelector('.hero-content');
    // heroSlider is already defined above

    window.addEventListener('scroll', () => {
        const scrollY = window.scrollY;

        // Header logic
        if (scrollY > 50) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }

        // Parallax logic (only effective when hero is in view)
        if (scrollY < window.innerHeight) {
            // Move text slower than scroll
            heroContent.style.transform = `translateY(${scrollY * 0.4}px)`;
            heroContent.style.opacity = 1 - (scrollY / 700); // Fade out text

            // Move background slightly to create depth
            heroSlider.style.transform = `translateY(${scrollY * 0.2}px)`;
        }
    });

    // Reviews Data & Rendering
    const reviewsData = [
        {
            name: "김민지",
            date: "2024.01.15",
            rating: 5,
            text: "전주 한옥마을과 가까워서 너무 좋았어요. 숙소도 너무 예쁘고 따뜻했습니다. 마당에서 커피 한잔하는데 정말 힐링되더라고요. 다음에 또 오고 싶어요!"
        },
        {
            name: "Lee So-young",
            date: "2023.12.28",
            rating: 5,
            text: "The perfect place to stay in Jeonju. It was clean, cozy, and the host was very kind. The garden is beautiful even in winter."
        },
        {
            name: "박준형",
            date: "2023.12.10",
            rating: 5,
            text: "가족들과 함께 머물었는데 방도 2개라 넉넉하고 침구도 너무 편안했습니다. 아이들이 마당에서 뛰어노는 걸 보니 좋았네요. 강력 추천합니다."
        },
        {
            name: "Choi Ji-hoon",
            date: "2023.11.05",
            rating: 4,
            text: "도심 속에 이런 조용한 공간이 있다니 놀라웠어요. 인테리어 감성도 너무 좋고 사진 찍기 좋습니다. 주차도 편했어요."
        },
        {
            name: "Sarah Jenkins",
            date: "2023.10.20",
            rating: 5,
            text: "Absolutely loved my stay! The location is fantastic, just a short walk to the main attractions but quiet enough to relax. The house itself is charming."
        }
    ];

    const reviewsSlider = document.querySelector('.reviews-slider');
    
    if (reviewsSlider) {
        reviewsData.forEach(review => {
            const card = document.createElement('div');
            card.classList.add('review-card');
            
            const stars = '★'.repeat(review.rating) + '☆'.repeat(5 - review.rating);
            
            card.innerHTML = `
                <div class="review-header">
                    <span class="reviewer-name">${review.name}</span>
                    <span class="review-date">${review.date}</span>
                </div>
                <div class="review-stars">${stars}</div>
                <div class="review-text">${review.text}</div>
            `;
            
            reviewsSlider.appendChild(card);
        });

        // Simple Auto Scroll for Reviews
        let scrollAmount = 0;
        const scrollSpeed = 0.5;
        let scrollDirection = 1;
        
        function autoScrollReviews() {
            if (reviewsSlider.matches(':hover')) return; // Pause on hover
            
            reviewsSlider.scrollLeft += scrollSpeed * scrollDirection;
            
            // Bounce back at ends (optional, or loop)
            // For simple loop effect, we can just reset if at end, but user scrolling might interfere.
            // Let's just scroll back and forth for now or infinite scroll if cloned.
            // Since cloning logic is complex for this step, let's just do a simple smooth scroll that reverses or resets.
            
            if (reviewsSlider.scrollLeft >= (reviewsSlider.scrollWidth - reviewsSlider.clientWidth)) {
                scrollDirection = -1;
            } else if (reviewsSlider.scrollLeft <= 0) {
                scrollDirection = 1;
            }
        }
        
        // Use AnimationFrame for smoother scroll? Or Interval. Interval 20ms is fine for simple.
        setInterval(autoScrollReviews, 20);
    }
});
