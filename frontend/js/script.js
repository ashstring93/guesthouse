document.addEventListener('DOMContentLoaded', () => {
    console.log('Watermill House website loaded.');

    const GUESTHOUSE_ADDRESS = '전북특별자치도 전주시 완산구 물레방아3길 19-3';
    const GUESTHOUSE_PARCEL = '태평동 180-3';
    const GUESTHOUSE_POSTCODE = '54998';

    function initializeNaverMap() {
        const mapElement = document.getElementById('map');
        const fallback = document.getElementById('map-fallback');

        if (!mapElement) return true;
        if (!window.naver || !window.naver.maps) return false;
        if (window.__naverMapAuthFailed) {
            mapElement.classList.remove('map-ready');
            return true;
        }

        const guesthousePosition = new naver.maps.LatLng(35.82438, 127.13421);
        const map = new naver.maps.Map(mapElement, {
            center: guesthousePosition,
            zoom: 16,
            zoomControl: true,
            zoomControlOptions: {
                position: naver.maps.Position.TOP_RIGHT
            }
        });

        const marker = new naver.maps.Marker({
            position: guesthousePosition,
            map,
            title: 'Watermill House'
        });

        const infoWindow = new naver.maps.InfoWindow({
            content: `
                <div style="padding:10px 12px;font-size:13px;line-height:1.5;">
                    <strong>Watermill House</strong><br>
                    ${GUESTHOUSE_ADDRESS}<br>
                    지번: ${GUESTHOUSE_PARCEL}<br>
                    우편번호: ${GUESTHOUSE_POSTCODE}
                </div>
            `
        });
        infoWindow.open(map, marker);

        mapElement.classList.add('map-ready');
        if (fallback) fallback.style.display = 'none';

        return true;
    }

    if (!initializeNaverMap()) {
        let retries = 0;
        const maxRetries = 20;
        const retryTimer = setInterval(() => {
            retries += 1;

            if (initializeNaverMap()) {
                clearInterval(retryTimer);
                return;
            }

            if (retries >= maxRetries) {
                clearInterval(retryTimer);
                const fallback = document.getElementById('map-fallback');
                if (fallback) {
                    const title = fallback.querySelector('span');
                    const description = fallback.querySelector('p');
                    if (title) title.textContent = '지도를 불러오지 못했습니다.';
                    if (description) {
                        description.textContent = 'Client ID 또는 NCP Web 서비스 URL 설정을 확인해주세요.';
                    }
                }
            }
        }, 250);
    }

    document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
        anchor.addEventListener('click', function onClick(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;

            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });

    const revealTargets = document.querySelectorAll('[data-reveal]');
    if (revealTargets.length > 0) {
        const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

        if (!prefersReducedMotion && 'IntersectionObserver' in window) {
            const revealObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach((entry) => {
                    if (!entry.isIntersecting) return;
                    entry.target.classList.add('in-view');
                    observer.unobserve(entry.target);
                });
            }, {
                threshold: 0.15,
                rootMargin: '0px 0px -10% 0px'
            });

            revealTargets.forEach((el) => {
                el.classList.add('reveal-init');
                revealObserver.observe(el);
            });
        } else {
            revealTargets.forEach((el) => el.classList.add('in-view'));
        }
    }

    const heroSlider = document.querySelector('.hero-slider');
    const images = ['images/1.avif', 'images/6.avif', 'images/9.avif'];
    let currentSlide = 0;

    if (heroSlider) {
        images.forEach((img, index) => {
            const slide = document.createElement('div');
            slide.classList.add('slide');
            slide.style.backgroundImage = `url('${img}')`;
            if (index === 0) slide.classList.add('active');
            heroSlider.appendChild(slide);
        });

        setInterval(() => {
            const slides = document.querySelectorAll('.hero-slider .slide');
            if (slides.length === 0) return;
            slides[currentSlide].classList.remove('active');
            currentSlide = (currentSlide + 1) % slides.length;
            slides[currentSlide].classList.add('active');
        }, 5000);
    }

    function initializeRoomCarousel() {
        const roomGrid = document.querySelector('.room-grid');
        if (!roomGrid) return;

        const roomItems = Array.from(roomGrid.querySelectorAll('.room-item'));
        if (roomItems.length < 2) return;

        const gardenItem = roomItems[0];
        const interiorItems = roomItems.slice(1);

        gardenItem.className = 'room-item garden-card';

        const carousel = document.createElement('section');
        carousel.className = 'interior-carousel';
        carousel.setAttribute('aria-label', '실내 공간 둘러보기');

        const viewport = document.createElement('div');
        viewport.className = 'interior-carousel-viewport';
        viewport.tabIndex = 0;

        const track = document.createElement('div');
        track.className = 'interior-carousel-track';
        viewport.appendChild(track);

        const prevButton = document.createElement('button');
        prevButton.type = 'button';
        prevButton.className = 'carousel-arrow carousel-arrow-prev';
        prevButton.setAttribute('aria-label', '이전 사진');
        prevButton.textContent = '‹';

        const nextButton = document.createElement('button');
        nextButton.type = 'button';
        nextButton.className = 'carousel-arrow carousel-arrow-next';
        nextButton.setAttribute('aria-label', '다음 사진');
        nextButton.textContent = '›';

        carousel.append(viewport, prevButton, nextButton);

        roomGrid.replaceChildren(gardenItem, carousel);
        roomGrid.classList.add('is-carousel-ready');

        interiorItems.forEach((item, index) => {
            item.className = index === 0 ? 'interior-slide is-active' : 'interior-slide';
            const image = item.querySelector('img');
            if (image) image.draggable = false;
            track.appendChild(item);
        });

        let activeIndex = 0;
        let pointerStartX = null;
        let pointerOffsetX = 0;
        let activePointerId = null;
        let isDragging = false;

        function renderTrack(offsetX = 0, animate = true) {
            track.style.transition = animate
                ? 'transform 0.55s cubic-bezier(0.22, 0.61, 0.36, 1)'
                : 'none';
            track.style.transform = `translateX(calc(${-activeIndex * 100}% + ${offsetX}px))`;
        }

        function goToSlide(nextIndex) {
            activeIndex = (nextIndex + interiorItems.length) % interiorItems.length;
            renderTrack(0, true);

            interiorItems.forEach((slide, index) => {
                slide.classList.toggle('is-active', index === activeIndex);
            });
        }

        prevButton.addEventListener('click', () => goToSlide(activeIndex - 1));
        nextButton.addEventListener('click', () => goToSlide(activeIndex + 1));

        viewport.addEventListener('keydown', (event) => {
            if (event.key === 'ArrowLeft') {
                event.preventDefault();
                goToSlide(activeIndex - 1);
            }

            if (event.key === 'ArrowRight') {
                event.preventDefault();
                goToSlide(activeIndex + 1);
            }
        });

        viewport.addEventListener('pointerdown', (event) => {
            if (event.pointerType === 'mouse' && event.button !== 0) return;
            pointerStartX = event.clientX;
            pointerOffsetX = 0;
            activePointerId = event.pointerId;
            isDragging = true;
            viewport.classList.add('is-dragging');
            track.style.transition = 'none';
            viewport.setPointerCapture(event.pointerId);
        });

        viewport.addEventListener('pointermove', (event) => {
            if (!isDragging || activePointerId !== event.pointerId || pointerStartX === null) return;
            pointerOffsetX = event.clientX - pointerStartX;
            renderTrack(pointerOffsetX, false);
        });

        function endDrag(event) {
            if (!isDragging || activePointerId !== event.pointerId) return;

            const threshold = Math.min(140, viewport.clientWidth * 0.18);
            const deltaX = pointerOffsetX;

            isDragging = false;
            pointerStartX = null;
            pointerOffsetX = 0;
            activePointerId = null;
            viewport.classList.remove('is-dragging');

            if (viewport.hasPointerCapture(event.pointerId)) {
                viewport.releasePointerCapture(event.pointerId);
            }

            if (Math.abs(deltaX) < threshold) {
                renderTrack(0, true);
                return;
            }

            if (deltaX > 0) goToSlide(activeIndex - 1);
            if (deltaX < 0) goToSlide(activeIndex + 1);
        }

        viewport.addEventListener('pointerup', endDrag);
        viewport.addEventListener('pointercancel', endDrag);
        viewport.addEventListener('dragstart', (event) => event.preventDefault());

        goToSlide(0);
    }

    initializeRoomCarousel();

    const header = document.getElementById('main-header');
    const heroContent = document.querySelector('.hero-content');

    window.addEventListener('scroll', () => {
        const scrollY = window.scrollY;

        if (header) {
            if (scrollY > 50) {
                header.classList.add('scrolled');
            } else {
                header.classList.remove('scrolled');
            }
        }

        if (scrollY < window.innerHeight) {
            if (heroContent) {
                heroContent.style.transform = `translateY(${scrollY * 0.4}px)`;
                heroContent.style.opacity = String(1 - (scrollY / 700));
            }
            if (heroSlider) {
                heroSlider.style.transform = `translateY(${scrollY * 0.2}px)`;
            }
        }
    });

    const reviewsData = [
        {
            name: '김민지',
            date: '2024.01.15',
            rating: 5,
            text: '한옥 감성이 정말 좋았고 마당이 넓어서 아이와 함께 머물기 좋았어요. 청소 상태도 매우 깔끔했습니다.'
        },
        {
            name: 'Lee So-young',
            date: '2023.12.28',
            rating: 5,
            text: 'The perfect place to stay in Jeonju. It was clean, cozy, and the host was very kind. The garden is beautiful even in winter.'
        },
        {
            name: '박지은',
            date: '2023.12.10',
            rating: 5,
            text: '반려견과 함께 머물기에 좋았고, 주변이 조용해서 쉬기에 딱이었습니다. 다시 방문하고 싶어요.'
        },
        {
            name: 'Choi Ji-hoon',
            date: '2023.11.05',
            rating: 4,
            text: '객리단길과 가깝고 접근성이 좋았습니다. 실내가 아늑하고 편해서 하룻밤 잘 쉬었어요.'
        },
        {
            name: 'Sarah Jenkins',
            date: '2023.10.20',
            rating: 5,
            text: 'Absolutely loved my stay! The location is fantastic, just a short walk to the main attractions but quiet enough to relax. The house itself is charming.'
        }
    ];

    const reviewsSlider = document.querySelector('.reviews-slider');

    if (reviewsSlider) {
        reviewsData.forEach((review) => {
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

        const scrollSpeed = 0.5;
        let scrollDirection = 1;

        function autoScrollReviews() {
            if (reviewsSlider.matches(':hover')) return;

            reviewsSlider.scrollLeft += scrollSpeed * scrollDirection;

            if (reviewsSlider.scrollLeft >= (reviewsSlider.scrollWidth - reviewsSlider.clientWidth)) {
                scrollDirection = -1;
            } else if (reviewsSlider.scrollLeft <= 0) {
                scrollDirection = 1;
            }
        }

        setInterval(autoScrollReviews, 20);
    }
});
