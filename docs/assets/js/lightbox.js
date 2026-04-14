// Minimal lightbox: click any <a data-lightbox> to open a fullscreen overlay.
// Arrow keys cycle through all lightbox links on the page. Esc closes.
(function () {
    "use strict";

    const links = Array.from(document.querySelectorAll("a[data-lightbox]"));
    if (!links.length) return;

    let currentIndex = -1;
    let backdrop = null;

    function open(index) {
        currentIndex = index;
        const link = links[currentIndex];
        const href = link.getAttribute("href");
        const caption = link.getAttribute("data-caption") || "";

        if (!backdrop) {
            backdrop = document.createElement("div");
            backdrop.className = "lb-backdrop";
            backdrop.innerHTML = `
                <button class="lb-close" aria-label="Close (Esc)">&times;</button>
                <button class="lb-prev" aria-label="Previous (&larr;)">&larr;</button>
                <button class="lb-next" aria-label="Next (&rarr;)">&rarr;</button>
                <img alt="">
                <div class="lb-caption"></div>
            `;
            document.body.appendChild(backdrop);

            backdrop.addEventListener("click", (e) => {
                if (e.target === backdrop) close();
            });
            backdrop.querySelector(".lb-close").addEventListener("click", close);
            backdrop.querySelector(".lb-prev").addEventListener("click", (e) => {
                e.stopPropagation();
                prev();
            });
            backdrop.querySelector(".lb-next").addEventListener("click", (e) => {
                e.stopPropagation();
                next();
            });
        }

        backdrop.querySelector("img").src = href;
        backdrop.querySelector("img").alt = caption;
        backdrop.querySelector(".lb-caption").textContent = caption;
        backdrop.style.display = "flex";

        const single = links.length <= 1;
        backdrop.querySelector(".lb-prev").style.display = single ? "none" : "";
        backdrop.querySelector(".lb-next").style.display = single ? "none" : "";
    }

    function close() {
        if (backdrop) backdrop.style.display = "none";
        currentIndex = -1;
    }

    function next() { open((currentIndex + 1) % links.length); }
    function prev() { open((currentIndex - 1 + links.length) % links.length); }

    links.forEach((link, i) => {
        link.addEventListener("click", (e) => {
            e.preventDefault();
            open(i);
        });
    });

    document.addEventListener("keydown", (e) => {
        if (currentIndex < 0) return;
        if (e.key === "Escape") close();
        else if (e.key === "ArrowRight") next();
        else if (e.key === "ArrowLeft") prev();
    });
})();
