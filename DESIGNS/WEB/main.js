/* ================================================================
   CowCalving.farm — Main JavaScript
   ================================================================ */

'use strict';

document.addEventListener('DOMContentLoaded', () => {
  function getHashFromHref(href) {
    if (!href) return '';
    const hashIndex = href.indexOf('#');
    if (hashIndex === -1) return '';
    const hash = href.slice(hashIndex);
    return hash.length > 1 ? hash : '';
  }

  /* ----------------------------------------------------------------
     1. Reading Progress Bar
  ---------------------------------------------------------------- */
  const progressBar = document.createElement('div');
  progressBar.id = 'progress-bar';
  document.body.prepend(progressBar);

  function updateProgress() {
    const scrollTop = window.scrollY;
    const docHeight = document.documentElement.scrollHeight - window.innerHeight;
    const pct = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
    progressBar.style.width = pct + '%';
  }

  /* ----------------------------------------------------------------
     2. Back-to-Top Button
  ---------------------------------------------------------------- */
  const backToTop = document.createElement('button');
  backToTop.id = 'back-to-top';
  backToTop.setAttribute('aria-label', 'Back to top');
  backToTop.innerHTML = '↑';
  document.body.appendChild(backToTop);

  backToTop.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  /* ----------------------------------------------------------------
     3. Scroll Reveal (IntersectionObserver)
  ---------------------------------------------------------------- */
  const revealTargets = document.querySelectorAll(
    '.sign-card, .stage-card, .daily-card, .colos-card, .trouble-card, ' +
    '.hour-card, .stat-item, .faq-item, .next-card, .testimonial-card, ' +
    '.highlight-stat, .three-qs, .hours-grid, .intro-section, .section-work, .alert-item'
  );

  revealTargets.forEach(el => el.classList.add('reveal'));

  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        revealObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12 });

  revealTargets.forEach(el => revealObserver.observe(el));

  /* ----------------------------------------------------------------
     3b. Platform Features Progressive Reveal
  ---------------------------------------------------------------- */
  const platformSection = document.querySelector('.platform-features-section');
  const platformCards = platformSection
    ? Array.from(platformSection.querySelectorAll('.feature-card'))
    : [];
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const isDesktopPlatformScroll = window.matchMedia('(min-width: 1101px)').matches;
  const shouldScrollJackPlatform = !prefersReducedMotion && isDesktopPlatformScroll;
  const extraPlatformCards = (shouldScrollJackPlatform && platformCards.length > 1)
    ? platformCards.slice(1)
    : [];
  let revealedPlatformCount = 0;
  let targetPlatformCount = 0;
  let platformStepRaf = 0;

  if (extraPlatformCards.length > 0) {
    platformSection.classList.add('pf-scrolljack');
    platformSection.style.setProperty('--pf-extra-steps', String(extraPlatformCards.length));
    extraPlatformCards.forEach(card => card.classList.add('pf-queued'));
  }

  function revealPlatformCard(card) {
    card.classList.remove('pf-queued');
    card.classList.add('pf-enter');
    window.setTimeout(() => card.classList.remove('pf-enter'), 500);
  }

  function hidePlatformCard(card) {
    card.classList.remove('pf-enter');
    card.classList.add('pf-queued');
  }

  function stepPlatformCards() {
    if (revealedPlatformCount < targetPlatformCount) {
      revealPlatformCard(extraPlatformCards[revealedPlatformCount]);
      revealedPlatformCount += 1;
      platformStepRaf = window.requestAnimationFrame(stepPlatformCards);
      return;
    }

    if (revealedPlatformCount > targetPlatformCount) {
      revealedPlatformCount -= 1;
      hidePlatformCard(extraPlatformCards[revealedPlatformCount]);
      platformStepRaf = window.requestAnimationFrame(stepPlatformCards);
      return;
    }

    platformStepRaf = 0;
  }

  function updatePlatformCards() {
    if (!platformSection || extraPlatformCards.length === 0) return;

    const rect = platformSection.getBoundingClientRect();
    const viewportH = window.innerHeight || document.documentElement.clientHeight;
    const revealAnchor = viewportH * 0.28;
    const distanceIntoSection = Math.max(0, revealAnchor - rect.top);
    const stepDistance = Math.max(140, viewportH * 0.24);
    const computedTargetCount = Math.min(
      extraPlatformCards.length,
      Math.floor(distanceIntoSection / stepDistance)
    );
    targetPlatformCount = computedTargetCount;

    if (!platformStepRaf) {
      platformStepRaf = window.requestAnimationFrame(stepPlatformCards);
    }
  }

  /* ----------------------------------------------------------------
     4. Combined Scroll Handler
  ---------------------------------------------------------------- */
  function handleScroll() {
    updateProgress();

    // Back to top visibility
    if (window.scrollY > 400) {
      backToTop.classList.add('visible');
    } else {
      backToTop.classList.remove('visible');
    }

    // Active nav link highlighting
    const sections = document.querySelectorAll('section[id], div[id]');
    let current = '';
    sections.forEach(sec => {
      const rect = sec.getBoundingClientRect();
      if (rect.top <= 120 && rect.bottom >= 120) {
        current = sec.id;
      }
    });

    document.querySelectorAll('.nav-links a').forEach(link => {
      link.classList.remove('nav-active');
      const hash = getHashFromHref(link.getAttribute('href') || '');
      if (hash === '#' + current) {
        link.classList.add('nav-active');
      }
    });

    const guideToggle = document.querySelector('.nav-dropdown-toggle');
    if (guideToggle) {
      guideToggle.classList.remove('nav-active');
      const path = window.location.pathname;
      const onGuidePage = path.endsWith('guide.html') || path.endsWith('/guide.html');
      if (onGuidePage) guideToggle.classList.add('nav-active');
    }

    updatePlatformCards();
  }

  window.addEventListener('scroll', handleScroll, { passive: true });
  updatePlatformCards();

  /* ----------------------------------------------------------------
     5. FAQ Accordion
  ---------------------------------------------------------------- */
  document.querySelectorAll('.faq-q').forEach(btn => {
    btn.addEventListener('click', () => {
      const item = btn.closest('.faq-item');
      const isOpen = item.classList.contains('open');

      // Close all
      document.querySelectorAll('.faq-item.open').forEach(openItem => {
        openItem.classList.remove('open');
      });

      // Open clicked if it was closed
      if (!isOpen) {
        item.classList.add('open');
      }
    });
  });

  /* ----------------------------------------------------------------
     6. Interactive Checklist
  ---------------------------------------------------------------- */
  document.querySelectorAll('.check-box').forEach(box => {
    box.addEventListener('click', () => {
      box.classList.toggle('checked');
      const item = box.closest('.check-item');
      if (item) item.classList.toggle('done', box.classList.contains('checked'));
    });
  });

  // Also allow clicking the whole check-item row
  document.querySelectorAll('.check-item').forEach(item => {
    item.addEventListener('click', (e) => {
      if (e.target.classList.contains('check-box')) return; // already handled
      const box = item.querySelector('.check-box');
      if (box) {
        box.classList.toggle('checked');
        item.classList.toggle('done', box.classList.contains('checked'));
      }
    });
  });

  /* ----------------------------------------------------------------
     7. Smooth Scroll for Internal Links
  ---------------------------------------------------------------- */
  document.querySelectorAll('a[href*="#"]').forEach(anchor => {
    anchor.addEventListener('click', e => {
      const rawHref = anchor.getAttribute('href') || '';
      const hash = getHashFromHref(rawHref);
      if (!hash) return;

      let targetUrl;
      try {
        targetUrl = new URL(rawHref, window.location.href);
      } catch {
        return;
      }

      if (targetUrl.pathname !== window.location.pathname) return;

      const targetId = decodeURIComponent(hash.slice(1));
      const target = document.getElementById(targetId);
      if (!target) return;

      e.preventDefault();
      const navH = document.querySelector('nav') ? document.querySelector('nav').offsetHeight : 74;
      const top = target.getBoundingClientRect().top + window.scrollY - navH - 16;
      window.scrollTo({ top, behavior: 'smooth' });
    });
  });

  /* ----------------------------------------------------------------
     8. Animated Counters for Stats Strip
  ---------------------------------------------------------------- */
  function animateValue(el, endVal, suffix, duration) {
    const startTime = performance.now();
    const startVal = 0;
    const isFloat = suffix.includes('.');

    function update(currentTime) {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 3); // ease-out cubic
      const current = startVal + (endVal - startVal) * ease;
      el.textContent = (isFloat ? current.toFixed(1) : Math.round(current)) + suffix;
      if (progress < 1) requestAnimationFrame(update);
    }

    requestAnimationFrame(update);
  }

  const statsObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const statValue = entry.target.querySelector('.stat-value');
      if (!statValue || statValue.dataset.animated) return;
      statValue.dataset.animated = true;

      const raw = statValue.textContent.trim(); // e.g. "280 days", "3", "2 – 6 hrs"
      // Extract leading number
      const match = raw.match(/^([\d.]+)/);
      if (match) {
        const num = parseFloat(match[1]);
        const suffix = raw.slice(match[1].length);
        animateValue(statValue, num, suffix, 1200);
      }

      statsObserver.unobserve(entry.target);
    });
  }, { threshold: 0.4 });

  document.querySelectorAll('.stat-item').forEach(item => statsObserver.observe(item));

  /* ----------------------------------------------------------------
     9. Active nav link style (injected CSS)
  ---------------------------------------------------------------- */
  const style = document.createElement('style');
  style.textContent = `
    .nav-links a.nav-active,
    .nav-dropdown-toggle.nav-active {
      color: var(--amber-light) !important;
      background: rgba(255,255,255,.09) !important;
    }
  `;
  document.head.appendChild(style);

  /* ----------------------------------------------------------------
     10. Scroll-Linked Interactive Features
  ---------------------------------------------------------------- */
  const featureSteps = document.querySelectorAll('.feature-step');
  if (featureSteps.length > 0) {
    const featureObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          // Remove active from all
          featureSteps.forEach(step => step.classList.remove('active'));
          // Add to intersecting
          entry.target.classList.add('active');
        }
      });
    }, {
      rootMargin: '-40% 0px -40% 0px', // Trigger when item is in middle 20% of screen
      threshold: 0
    });

    featureSteps.forEach(step => featureObserver.observe(step));
  }

  /* ----------------------------------------------------------------
     11. Nav Dropdown
  ---------------------------------------------------------------- */
  const dropdownToggles = document.querySelectorAll('.nav-dropdown-toggle');

  function closeDropdowns() {
    dropdownToggles.forEach(toggle => {
      const item = toggle.closest('.nav-item.dropdown');
      if (item) item.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
    });
  }

  dropdownToggles.forEach(toggle => {
    toggle.addEventListener('click', (e) => {
      e.stopPropagation();
      const item = toggle.closest('.nav-item.dropdown');
      if (!item) return;
      const isOpen = item.classList.contains('open');
      closeDropdowns();
      if (!isOpen) {
        item.classList.add('open');
        toggle.setAttribute('aria-expanded', 'true');
      }
    });
  });

  document.addEventListener('click', (e) => {
    if (e.target.closest('.nav-item.dropdown')) return;
    closeDropdowns();
  });

  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    closeDropdowns();
  });

  document.querySelectorAll('.nav-dropdown a').forEach(link => {
    link.addEventListener('click', () => closeDropdowns());
  });

});
