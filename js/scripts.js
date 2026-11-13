/*!
* Start Bootstrap - Resume v7.0.6 (https://startbootstrap.com/theme/resume)
* Copyright 2013-2023 Start Bootstrap
* Licensed under MIT (https://github.com/StartBootstrap/startbootstrap-resume/blob/master/LICENSE)
*/
//
// Scripts
// 

window.addEventListener('DOMContentLoaded', event => {

    // Activate Bootstrap scrollspy on the main nav element
    const sideNav = document.body.querySelector('#sideNav');
    if (sideNav) {
        new bootstrap.ScrollSpy(document.body, {
            target: '#sideNav',
            rootMargin: '0px 0px -40%',
        });
    };

    // Collapse responsive navbar when toggler is visible
    const navbarToggler = document.body.querySelector('.navbar-toggler');
    const responsiveNavItems = [].slice.call(
        document.querySelectorAll('#navbarResponsive .nav-link')
    );
    responsiveNavItems.map(function (responsiveNavItem) {
        responsiveNavItem.addEventListener('click', () => {
            if (window.getComputedStyle(navbarToggler).display !== 'none') {
                navbarToggler.click();
            }
        });
    });

    // Dark-mode toggle (initial theme is set by the inline script in <head>)
    document.querySelectorAll('.theme-toggle').forEach(btn => btn.addEventListener('click', () => {
        const theme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
        document.documentElement.dataset.theme = theme;
        try { localStorage.setItem('theme', theme); } catch (e) { /* storage blocked: still toggles for this visit */ }
    }));

    // Timelines: place bars and year ticks from data-start / data-end ("YYYY-MM" or "present").
    const month = s => {
        if (s === 'present') { const d = new Date(); return d.getFullYear() * 12 + d.getMonth(); }
        const [y, m] = s.split('-').map(Number);
        return y * 12 + m - 1;
    };
    document.querySelectorAll('.timeline').forEach(tl => {
        const bars = [...tl.querySelectorAll('.tl-bar')];
        const lo = Math.min(...bars.map(b => month(b.dataset.start)));
        const hi = Math.max(...bars.map(b => month(b.dataset.end)));
        const x = v => (v - lo) / (hi - lo);
        bars.forEach(b => {
            b.style.setProperty('--s', x(month(b.dataset.start)));
            b.style.setProperty('--e', x(month(b.dataset.end)));
        });
        const axis = tl.querySelector('.tl-axis');
        for (let y = Math.ceil(lo / 12); y * 12 <= hi; y++) {
            axis.insertAdjacentHTML('beforeend', `<span style="--x:${x(y * 12)}">${y}</span>`);
        }
    });

    // Publications: clicking a type in the legend shows only that type; clicking it again (or "All") shows everything.
    const legend = document.querySelector('.pub-legend');
    if (legend) {
        legend.addEventListener('click', e => {
            const btn = e.target.closest('button');
            if (!btn) return;
            const type = btn.dataset.type;
            const filter = type !== 'all' && btn.getAttribute('aria-pressed') !== 'true';
            legend.querySelectorAll('button').forEach(b =>
                b.setAttribute('aria-pressed', filter ? b === btn : b.dataset.type === 'all'));
            document.querySelectorAll('.pubs .pub').forEach(p => { p.hidden = filter && p.dataset.type !== type; });
        });
    }

});
