'use strict';

document.addEventListener('DOMContentLoaded', () => {
  const progressBar = document.getElementById('progress-bar');
  const backToTop = document.getElementById('back-to-top');
  const mobileMenu = document.querySelector('[data-mobile-menu]');
  const mobileMenuToggle = document.querySelector('[data-mobile-menu-toggle]');
  const dropdownToggles = Array.from(document.querySelectorAll('[data-nav-dropdown-toggle]'));
  const revealTargets = Array.from(document.querySelectorAll('.reveal-up'));
  const platformCards = Array.from(document.querySelectorAll('[data-platform-card]'));
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function updateProgress() {
    if (!progressBar) return;
    const docHeight = document.documentElement.scrollHeight - window.innerHeight;
    const progress = docHeight > 0 ? (window.scrollY / docHeight) * 100 : 0;
    progressBar.style.width = `${progress}%`;
  }

  function updateBackToTop() {
    if (!backToTop) return;
    backToTop.classList.toggle('visible', window.scrollY > 400);
  }

  function closeDropdowns() {
    dropdownToggles.forEach((toggle) => {
      toggle.setAttribute('aria-expanded', 'false');
      toggle.closest('.site-dropdown-item')?.classList.remove('open');
    });
  }

  dropdownToggles.forEach((toggle) => {
    toggle.addEventListener('click', (event) => {
      event.stopPropagation();
      const item = toggle.closest('.site-dropdown-item');
      const shouldOpen = !item?.classList.contains('open');
      closeDropdowns();
      if (shouldOpen && item) {
        item.classList.add('open');
        toggle.setAttribute('aria-expanded', 'true');
      }
    });
  });

  document.addEventListener('click', (event) => {
    if (!event.target.closest('.site-dropdown-item')) {
      closeDropdowns();
    }
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      closeDropdowns();
      if (mobileMenu && mobileMenuToggle) {
        mobileMenu.classList.add('hidden');
        mobileMenuToggle.setAttribute('aria-expanded', 'false');
      }
    }
  });

  if (mobileMenu && mobileMenuToggle) {
    mobileMenuToggle.addEventListener('click', () => {
      const isOpen = !mobileMenu.classList.contains('hidden');
      mobileMenu.classList.toggle('hidden', isOpen);
      mobileMenuToggle.setAttribute('aria-expanded', String(!isOpen));
    });
  }

  if (backToTop) {
    backToTop.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  document.querySelectorAll('a[href*="#"]').forEach((anchor) => {
    anchor.addEventListener('click', (event) => {
      const href = anchor.getAttribute('href') || '';
      const hashIndex = href.indexOf('#');
      if (hashIndex === -1) return;

      let targetUrl;
      try {
        targetUrl = new URL(href, window.location.href);
      } catch {
        return;
      }

      if (targetUrl.pathname !== window.location.pathname) return;

      const targetId = decodeURIComponent(href.slice(hashIndex + 1));
      const target = document.getElementById(targetId);
      if (!target) return;

      event.preventDefault();
      closeDropdowns();
      mobileMenu?.classList.add('hidden');
      mobileMenuToggle?.setAttribute('aria-expanded', 'false');

      const navHeight = document.querySelector('nav')?.offsetHeight || 74;
      const top = target.getBoundingClientRect().top + window.scrollY - navHeight - 16;
      window.scrollTo({ top, behavior: 'smooth' });
    });
  });

  if (!prefersReducedMotion && revealTargets.length > 0) {
    const revealObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.12 });

    revealTargets.forEach((target) => revealObserver.observe(target));
  } else {
    revealTargets.forEach((target) => target.classList.add('visible'));
  }

  if (platformCards.length > 0) {
    platformCards.forEach((card, index) => {
      if (index > 0) {
        card.classList.add('is-hidden');
      }
    });

    const updatePlatformCards = () => {
      if (prefersReducedMotion || window.innerWidth <= 1100) {
        platformCards.forEach((card) => card.classList.remove('is-hidden'));
        return;
      }

      const section = document.querySelector('.platform-features-section');
      if (!section) return;

      const rect = section.getBoundingClientRect();
      const revealAnchor = window.innerHeight * 0.28;
      const distanceIntoSection = Math.max(0, revealAnchor - rect.top);
      const stepDistance = Math.max(140, window.innerHeight * 0.24);
      const visibleCount = 1 + Math.min(
        platformCards.length - 1,
        Math.floor(distanceIntoSection / stepDistance),
      );

      platformCards.forEach((card, index) => {
        card.classList.toggle('is-hidden', index >= visibleCount);
      });
    };

    updatePlatformCards();
    window.addEventListener('scroll', updatePlatformCards, { passive: true });
    window.addEventListener('resize', updatePlatformCards);
  }

  function handleScroll() {
    updateProgress();
    updateBackToTop();
  }

  window.addEventListener('scroll', handleScroll, { passive: true });
  handleScroll();
});
